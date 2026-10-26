"""
Prépare les données DPE tertiaire (ADEME) pour le dashboard.

Le gros CSV est lu par morceaux, seules les colonnes utiles sont gardées, les données
sont nettoyées, puis des tables AGRÉGÉES et DÉJÀ CALCULÉES sont écrites dans data/ :
    communes.csv, departements.csv, regions.csv, france.csv, meta.json
Le dashboard n'a plus qu'à lire ces fichiers : plus aucun calcul à l'affichage.

Usage :
    python prepare_data.py chemin/vers/dpe_tertiaire.csv
    python prepare_data.py dpe.csv --sortie data --sep ";" --garder-expires
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from ref_geo import DEPT_TO_REGION

CLASSES = list("ABCDEFG")
SURF_COLS = [f"S_{c}" for c in CLASSES]
RENOVER = ["E", "F", "G"]                 # classes comptées dans la surface à rénover
SURFACE_MAX_M2 = 1_000_000                # au-delà : surface jugée aberrante (saisie erronée)

# Colonnes du CSV source réellement utilisées (les ~60 autres sont ignorées)
COLONNES_UTILES = [
    "numero_dpe",              # identifiant (dédoublonnage)
    "date_fin_validite_dpe",   # exclure les DPE expirés
    "etiquette_dpe",           # classe énergie A à G
    "surface_utile",           # surface du bâtiment (m²)
    "surface_shon",            # surface de secours si surface_utile est vide
    "code_insee_ban",          # commune (code INSEE)
    "nom_commune_ban",         # nom de la commune
]
COL_REMPLACE = "numero_dpe_remplace"      # DPE remplacé par ce DPE (donc obsolète)


# --------------------------------------------------------------------------
# Nettoyage
# --------------------------------------------------------------------------
def code_commune(insee: pd.Series) -> pd.Series:
    """
    Normalise le code INSEE de la commune.
    Les fonds de carte ont UNE commune pour Paris, Lyon et Marseille alors que la BAN
    renvoie des arrondissements : on les ramène à la commune (75056, 69123, 13055).
    """
    s = insee.str.strip()
    s = s.mask(s.str.fullmatch(r"\d{4}").fillna(False), s.str.zfill(5))
    s = s.mask(s.str.fullmatch(r"751(0[1-9]|1\d|20)").fillna(False), "75056")
    s = s.mask(s.str.fullmatch(r"6938[1-9]").fillna(False), "69123")
    s = s.mask(s.str.fullmatch(r"132(0[1-9]|1[0-6])").fillna(False), "13055")
    return s


def surface_m2(chunk: pd.DataFrame) -> tuple[pd.Series, int]:
    """surface_utile, sinon surface_shon ; 0 si absente ou aberrante (le bâtiment reste compté)."""
    utile = pd.to_numeric(chunk["surface_utile"], errors="coerce")
    shon = pd.to_numeric(chunk["surface_shon"], errors="coerce")
    surf = utile.where(utile > 0, shon)
    invalide = ~((surf > 0) & (surf <= SURFACE_MAX_M2))
    return surf.where(~invalide, 0.0), int(invalide.sum())


def traiter_chunk(chunk, remplaces, vus, stats, aujourdhui, garder_expires):
    """Applique les filtres, puis renvoie (agrégat commune x étiquette, noms de communes)."""
    stats["lignes_lues"] += len(chunk)

    chunk = chunk.copy()
    chunk["etiquette"] = chunk["etiquette_dpe"].str.strip().str.upper()
    ok = chunk["etiquette"].isin(CLASSES)
    stats["etiquette_invalide"] += int((~ok).sum())
    chunk = chunk[ok]

    ok = ~chunk["numero_dpe"].isin(remplaces)
    stats["remplaces_par_un_dpe_plus_recent"] += int((~ok).sum())
    chunk = chunk[ok]

    if not garder_expires:
        fin = pd.to_datetime(chunk["date_fin_validite_dpe"], errors="coerce")
        ok = ~(fin < aujourdhui)                       # date vide : on garde
        stats["expires"] += int((~ok).sum())
        chunk = chunk[ok]

    doublon = chunk["numero_dpe"].duplicated() | chunk["numero_dpe"].isin(vus)
    stats["doublons"] += int(doublon.sum())
    chunk = chunk[~doublon]
    vus.update(chunk["numero_dpe"])

    insee = chunk["code_insee_ban"].str.strip()
    ok = insee.notna() & (insee != "")
    stats["sans_commune"] += int((~ok).sum())
    chunk = chunk[ok].copy()

    chunk["code"] = code_commune(chunk["code_insee_ban"])
    ok = chunk["code"].str[:2].isin(DEPT_TO_REGION)    # France métropolitaine uniquement
    stats["hors_metropole"] += int((~ok).sum())
    chunk = chunk[ok].copy()

    chunk["surface"], invalides = surface_m2(chunk)
    stats["surface_invalide_ou_absente"] += invalides
    stats["retenues"] += len(chunk)

    agg = (chunk.groupby(["code", "etiquette"], as_index=False)
                .agg(n=("numero_dpe", "size"), surf=("surface", "sum")))
    noms = chunk.drop_duplicates("code")[["code", "nom_commune_ban"]]
    return agg, noms


# --------------------------------------------------------------------------
# Calcul des KPI (une seule fois, ici)
# --------------------------------------------------------------------------
def add_kpis(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["total"] = df[CLASSES].sum(axis=1)
    df["nb_passoires"] = df[["F", "G"]].sum(axis=1)
    df["part_passoires"] = (df["nb_passoires"] / df["total"].where(df["total"] > 0)).round(4)
    df["surface_totale"] = df[SURF_COLS].sum(axis=1)
    df["surface_renover"] = df[[f"S_{c}" for c in RENOVER]].sum(axis=1)
    return df


def agreger(communes: pd.DataFrame, cle: str) -> pd.DataFrame:
    """Somme des comptages par département / région, puis recalcul des KPI."""
    somme = communes.groupby(cle)[CLASSES + SURF_COLS].sum().reset_index()
    somme = somme.rename(columns={cle: "code"})
    if cle == "code_dept":
        somme.insert(1, "code_region", somme["code"].map(DEPT_TO_REGION))
    return add_kpis(somme)


# --------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="CSV DPE tertiaire de l'ADEME")
    ap.add_argument("--sortie", default="data", help="dossier de sortie (défaut : data)")
    ap.add_argument("--sep", default=",", help="séparateur du CSV (défaut : ,)")
    ap.add_argument("--encoding", default="utf-8", help="encodage du CSV (défaut : utf-8)")
    ap.add_argument("--chunk", type=int, default=200_000, help="lignes lues à la fois")
    ap.add_argument("--garder-expires", action="store_true", help="ne pas exclure les DPE expirés")
    args = ap.parse_args()

    source, sortie = Path(args.source), Path(args.sortie)
    lecture = dict(sep=args.sep, encoding=args.encoding, dtype=str,
                   keep_default_na=False, na_values=[""], chunksize=args.chunk)

    entete = pd.read_csv(source, sep=args.sep, encoding=args.encoding, nrows=0).columns
    manquantes = [c for c in COLONNES_UTILES + [COL_REMPLACE] if c not in entete]
    if manquantes:
        sys.exit(f"Colonnes absentes du fichier : {manquantes}\n"
                 f"(séparateur utilisé : {args.sep!r} - essayer --sep \";\")")

    # Passe 1 : DPE remplacés par un DPE plus récent (donc à ignorer)
    print("Passe 1/2 : recherche des DPE remplacés...")
    remplaces = set()
    for chunk in pd.read_csv(source, usecols=[COL_REMPLACE], **lecture):
        remplaces.update(chunk[COL_REMPLACE].dropna())
    print(f"  {len(remplaces):,} DPE remplacés".replace(",", " "))

    # Passe 2 : nettoyage et agrégation par commune
    print("Passe 2/2 : nettoyage et agrégation...")
    stats = dict.fromkeys(["lignes_lues", "etiquette_invalide", "remplaces_par_un_dpe_plus_recent",
                           "expires", "doublons", "sans_commune", "hors_metropole",
                           "surface_invalide_ou_absente", "retenues"], 0)
    aujourdhui = pd.Timestamp.today().normalize()
    vus, partiels, noms_partiels = set(), [], []
    for chunk in pd.read_csv(source, usecols=COLONNES_UTILES, **lecture):
        agg, noms = traiter_chunk(chunk, remplaces, vus, stats, aujourdhui, args.garder_expires)
        partiels.append(agg)
        noms_partiels.append(noms)
        print(f"  {stats['lignes_lues']:>10,} lignes lues | {stats['retenues']:>10,} retenues".replace(",", " "))
    if not partiels or stats["retenues"] == 0:
        sys.exit("Aucune ligne exploitable : vérifier le fichier, le séparateur et les filtres.")

    # Tables large : une ligne par commune, comptages et surfaces par classe
    agg = pd.concat(partiels).groupby(["code", "etiquette"], as_index=False).sum()
    nb = agg.pivot(index="code", columns="etiquette", values="n").reindex(columns=CLASSES).fillna(0).astype(int)
    surf = agg.pivot(index="code", columns="etiquette", values="surf").reindex(columns=CLASSES).fillna(0).round(0).astype(int)
    surf.columns = SURF_COLS
    communes = nb.join(surf).reset_index()

    noms = pd.concat(noms_partiels).drop_duplicates("code").set_index("code")["nom_commune_ban"]
    noms.loc["75056"] = "Paris"; noms.loc["69123"] = "Lyon"; noms.loc["13055"] = "Marseille"
    communes["nom"] = communes["code"].map(noms)
    communes["code_dept"] = communes["code"].str[:2]
    communes["code_region"] = communes["code_dept"].map(DEPT_TO_REGION)
    communes = add_kpis(communes)

    ordre = ["code", "nom", "code_dept", "code_region"]
    departements = agreger(communes, "code_dept")
    regions = agreger(communes, "code_region")
    france = add_kpis(communes[CLASSES + SURF_COLS].sum().to_frame().T.astype(int))
    france.insert(0, "code", "FR")

    sortie.mkdir(parents=True, exist_ok=True)
    communes[ordre + [c for c in communes.columns if c not in ordre]].sort_values("code") \
        .to_csv(sortie / "communes.csv", index=False)
    departements.sort_values("code").to_csv(sortie / "departements.csv", index=False)
    regions.sort_values("code").to_csv(sortie / "regions.csv", index=False)
    france.to_csv(sortie / "france.csv", index=False)

    meta = {
        "source": source.name,
        "genere_le": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dpe_expires_exclus": not args.garder_expires,
        "surface": "surface_utile, sinon surface_shon ; 0 si absente ou > "
                   f"{SURFACE_MAX_M2} m2 (le bâtiment reste compté)",
        "surface_a_renover": "classes " + ", ".join(RENOVER),
        "nb_batiments": int(france["total"].iloc[0]),
        "nb_communes_avec_donnees": int(len(communes)),
        "nettoyage": stats,
    }
    (sortie / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nRésumé du nettoyage :")
    for k, v in stats.items():
        print(f"  {k:<36}{v:>12,}".replace(",", " "))
    print(f"\nFichiers écrits dans {sortie.resolve()} :")
    for f in ("communes.csv", "departements.csv", "regions.csv", "france.csv", "meta.json"):
        print(f"  {f:<18}{(sortie / f).stat().st_size / 1024:>10.0f} Ko")


if __name__ == "__main__":
    main()
