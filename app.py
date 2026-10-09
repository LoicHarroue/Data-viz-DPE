"""
Dashboard Dash - Parc tertiaire par classe DPE (données de TEST)

Navigation : France > régions > départements > communes
KPI 1 : répartition du parc par classe énergie (A à G)
KPI 2 : part de "passoires" (classes F + G)
KPI 3 : surface à rénover (m² des bâtiments en classes E, F et G)

Lancement :  python app.py   puis   http://127.0.0.1:8050
"""
import json
import math
import re
import unicodedata
import urllib.request
import zlib
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------
CLASSES = list("ABCDEFG")
SURF_COLS = [f"S_{c}" for c in CLASSES]          # surface (m²) par classe
RENOVER = ["E", "F", "G"]                        # classes comptées dans "à rénover"
# Deux palettes : "default" (couleurs officielles du DPE) et "okabe" (Okabe-Ito,
# lisible pour les daltoniens). Logique conservée : vert = bon, vermillon/noir = mauvais.
PALETTES = {
    "default": dict(
        colorscale="RdYlGn_r",
        classes={"A": "#319834", "B": "#33cc31", "C": "#cbfc34", "D": "#fbfe06",
                 "E": "#fccc2f", "F": "#fc9935", "G": "#fc0205"},
        outline="#111111", good="#2e7d32", bad="#c62828",
    ),
    "okabe": dict(
        colorscale=[[0.0, "#009E73"], [0.35, "#F0E442"], [0.70, "#D55E00"], [1.0, "#000000"]],
        classes=dict(zip(CLASSES, ["#009E73", "#56B4E9", "#F0E442", "#E69F00",
                                   "#D55E00", "#CC79A7", "#000000"])),
        outline="#0072B2", good="#009E73", bad="#D55E00",
    ),
}
# Échelle de couleur commune à tous les niveaux (au-delà, la couleur sature)
Z_MIN, Z_MAX = 0.10, 0.35
TOP_N = 5                                        # nb de barres dans le graphique de surface

BASE_URL = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/"
GEO_DIR = Path(__file__).parent / "geojson"

# Région (code INSEE) -> départements (France métropolitaine)
REGIONS_DEPTS = {
    "11": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "24": ["18", "28", "36", "37", "41", "45"],
    "27": ["21", "25", "39", "58", "70", "71", "89", "90"],
    "28": ["14", "27", "50", "61", "76"],
    "32": ["02", "59", "60", "62", "80"],
    "44": ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"],
    "52": ["44", "49", "53", "72", "85"],
    "53": ["22", "29", "35", "56"],
    "75": ["16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"],
    "76": ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
    "84": ["01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"],
    "93": ["04", "05", "06", "13", "83", "84"],
    "94": ["2A", "2B"],
}
DEPT_TO_REGION = {d: r for r, ds in REGIONS_DEPTS.items() for d in ds}

# Part moyenne fictive de passoires (F+G) par région, pour avoir des écarts visibles
BASE_PASSOIRES = {
    "11": 0.14, "24": 0.22, "27": 0.25, "28": 0.21, "32": 0.27, "44": 0.26,
    "52": 0.16, "53": 0.15, "75": 0.19, "76": 0.18, "84": 0.20, "93": 0.17,
    "94": 0.28,
}

EMPTY_NAV = {"region": None, "dept": None, "communes": False, "commune": None}


# --------------------------------------------------------------------------
# Fonds de carte (GeoJSON) : régions/départements en local,
# communes téléchargées à la demande (un fichier par département)
# --------------------------------------------------------------------------
@lru_cache(maxsize=24)
def load_geojson(rel_path: str) -> dict:
    path = GEO_DIR / rel_path
    if not path.exists():
        url = BASE_URL + rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            urllib.request.urlretrieve(url, tmp)
        except Exception as exc:
            raise RuntimeError(f"Téléchargement impossible : {url} ({exc})") from exc
        tmp.replace(path)
    return json.loads(path.read_text(encoding="utf-8"))


GEO_REGIONS = load_geojson("regions-version-simplifiee.geojson")
GEO_DEPTS = load_geojson("departements-version-simplifiee.geojson")
NOM_REGION = {f["properties"]["code"]: f["properties"]["nom"] for f in GEO_REGIONS["features"]}
NOM_DEPT = {f["properties"]["code"]: f["properties"]["nom"] for f in GEO_DEPTS["features"]}


def communes_path(code_dept: str) -> str:
    """Ex. '29' -> departements/29-finistere/communes-29-finistere.geojson"""
    nom = unicodedata.normalize("NFKD", NOM_DEPT[code_dept]).encode("ascii", "ignore").decode().lower()
    folder = f"{code_dept}-{re.sub(r'[^a-z0-9]+', '-', nom).strip('-')}"
    return f"departements/{folder}/communes-{folder}.geojson"


def _bounds(features):
    xs, ys = [], []

    def walk(coords):
        if isinstance(coords[0], (int, float)):
            xs.append(coords[0])
            ys.append(coords[1])
        else:
            for c in coords:
                walk(c)

    for f in features:
        walk(f["geometry"]["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def fit_view(features, width=650, height=620):
    """Centre et zoom (approximatifs) pour cadrer les polygones affichés."""
    x0, y0, x1, y1 = _bounds(features)
    mid_lat = (y0 + y1) / 2
    z_lon = math.log2(width * 360 / (512 * max(x1 - x0, 1e-3)))
    lat_span_merc = max(y1 - y0, 1e-3) / math.cos(math.radians(mid_lat))
    z_lat = math.log2(height * 360 / (512 * lat_span_merc))
    zoom = min(max(min(z_lon, z_lat) - 0.3, 3.0), 13.0)
    return {"lat": mid_lat, "lon": (x0 + x1) / 2}, zoom


@lru_cache(maxsize=32)
def get_geo(level: str, region, dept):
    """(geojson, centre, zoom) de la carte affichée."""
    if level == "france":
        gj = GEO_REGIONS
    elif level == "region":
        gj = {"type": "FeatureCollection",
              "features": [f for f in GEO_DEPTS["features"]
                           if f["properties"]["code"] in REGIONS_DEPTS[region]]}
    else:
        gj = load_geojson(communes_path(dept))
    center, zoom = fit_view(gj["features"])
    return gj, center, zoom


# --------------------------------------------------------------------------
# Données de TEST (cohérentes entre niveaux : communes -> départements -> régions)
#
# Pour utiliser de vraies données : remplacer dept_data() et commune_data() par un
# chargement des agrégats ADEME (mêmes colonnes : code, nom, A..G, S_A..S_G).
# --------------------------------------------------------------------------
def add_kpis(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["total"] = df[CLASSES].sum(axis=1)
    df["nb_passoires"] = df[["F", "G"]].sum(axis=1)
    df["part_passoires"] = df["nb_passoires"] / df["total"].where(df["total"] > 0)
    df["surface_totale"] = df[SURF_COLS].sum(axis=1)
    df["surface_renover"] = df[[f"S_{c}" for c in RENOVER]].sum(axis=1)
    return df


@lru_cache(maxsize=8)
def dept_data(seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for code_dept, code_region in DEPT_TO_REGION.items():
        total = int(rng.lognormal(mean=10.0, sigma=0.6))
        fg = float(np.clip(rng.normal(BASE_PASSOIRES[code_region], 0.035), 0.06, 0.45))
        poids_ae = rng.dirichlet(np.array([0.04, 0.12, 0.28, 0.32, 0.24]) * 60)
        probs = np.concatenate([poids_ae * (1 - fg), [fg * 0.6, fg * 0.4]])
        counts = rng.multinomial(total, probs)
        surf_moy = rng.lognormal(np.log(900), 0.2, size=7)   # m² moyen / bâtiment
        rows.append({"code": code_dept, "code_region": code_region,
                     **dict(zip(CLASSES, counts)),
                     **dict(zip(SURF_COLS, counts * surf_moy))})
    df = add_kpis(pd.DataFrame(rows))
    df["nom"] = df["code"].map(NOM_DEPT)
    return df


@lru_cache(maxsize=8)
def region_data(seed: int) -> pd.DataFrame:
    df = dept_data(seed).groupby("code_region", as_index=False)[CLASSES + SURF_COLS].sum()
    df = add_kpis(df)
    df["code"] = df["code_region"]
    df["nom"] = df["code"].map(NOM_REGION)
    return df


@lru_cache(maxsize=8)
def france_data(seed: int) -> pd.Series:
    return add_kpis(dept_data(seed)[CLASSES + SURF_COLS].sum().to_frame().T).iloc[0]


@lru_cache(maxsize=32)
def commune_data(seed: int, code_dept: str) -> pd.DataFrame:
    """Répartit les totaux du département entre ses communes (somme exacte)."""
    feats = load_geojson(communes_path(code_dept))["features"]
    n = len(feats)
    parent = dept_data(seed).set_index("code").loc[code_dept]
    rng = np.random.default_rng([seed, zlib.crc32(code_dept.encode())])
    taille = rng.lognormal(0, 1.2, n)                        # communes très inégales
    out = {"code": [f["properties"]["code"] for f in feats],
           "nom": [f["properties"]["nom"] for f in feats]}
    for c in CLASSES:
        w = taille * rng.lognormal(0, 0.5, n)
        counts = rng.multinomial(int(parent[c]), w / w.sum())
        out[c] = counts
        surf_moy = parent[f"S_{c}"] / parent[c] if parent[c] else 0.0
        out[f"S_{c}"] = counts * surf_moy
    return add_kpis(pd.DataFrame(out))


# --------------------------------------------------------------------------
# Logique de navigation / vue
# --------------------------------------------------------------------------
def apply_event(nav: dict, trigger: str, click) -> dict:
    """Nouvel état de navigation après un clic carte ou bouton."""
    nav = dict(nav)
    if trigger == "btn-france":
        return dict(EMPTY_NAV)
    if trigger == "btn-region":
        nav.update(communes=False, commune=None)
    elif trigger == "btn-communes":
        nav.update(communes=True, commune=None)
    elif trigger == "btn-clear":
        nav["commune" if nav["communes"] else "dept"] = None
    elif trigger == "map" and click and click.get("points"):
        code = str(click["points"][0]["location"])
        if nav["region"] is None:
            if code in NOM_REGION:
                nav.update(region=code, dept=None, communes=False, commune=None)
        elif not nav["communes"]:
            if code in REGIONS_DEPTS[nav["region"]]:
                nav["dept"] = code
        else:
            nav["commune"] = code
    return nav


def build_view(nav: dict, seed: int) -> dict:
    """Détermine ce qui est affiché : niveau, tableau de données, sélection, panneau."""
    region, dept, communes, commune = (nav[k] for k in ("region", "dept", "communes", "commune"))
    level = "france" if region is None else ("dept" if communes else "region")

    if level == "france":
        df, selected, unit = region_data(seed), None, "régions"
    elif level == "region":
        d = dept_data(seed)
        df, selected, unit = d[d["code_region"] == region], dept, "départements"
    else:
        df, selected, unit = commune_data(seed, dept), commune, "communes"

    # Entité décrite dans le panneau + référence de comparaison
    if commune:
        row, ref = df[df["code"] == commune].iloc[0], dept_data(seed).set_index("code").loc[dept]
        titre, ref_label = f"{row['nom']} ({commune})", "vs département"
        niveau_txt = "Commune"
    elif dept:
        row = dept_data(seed).set_index("code").loc[dept].copy()
        row["code"] = dept
        ref = region_data(seed).set_index("code").loc[DEPT_TO_REGION[dept]]
        titre, ref_label, niveau_txt = f"{NOM_DEPT[dept]} ({dept})", "vs région", "Département"
    elif region:
        row, ref = region_data(seed).set_index("code").loc[region], france_data(seed)
        titre, ref_label, niveau_txt = NOM_REGION[region], "vs France", "Région"
    else:
        row, ref, titre, ref_label, niveau_txt = france_data(seed), None, "France métropolitaine", "", "Pays"

    crumb = ["France"]
    if region:
        crumb.append(NOM_REGION[region])
    if dept:
        crumb.append(NOM_DEPT[dept])
    if commune:
        crumb.append(row["nom"])

    return dict(level=level, df=df, selected=selected, unit=unit, row=row, ref=ref,
                titre=titre, ref_label=ref_label, niveau_txt=niveau_txt,
                crumb=" › ".join(crumb))


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------
def make_map(view: dict, nav: dict, min_batiments: int, pal: dict) -> go.Figure:
    df, level = view["df"], view["level"]
    gj, center, zoom = get_geo(level, nav["region"], nav["dept"])
    seuil = min_batiments if level == "dept" else 0           # seuil : communes seulement
    ok, low = df[df["total"] >= max(seuil, 1)], df[df["total"] < max(seuil, 1)]

    fig = go.Figure()
    fig.add_trace(go.Choroplethmap(
        geojson=gj, featureidkey="properties.code",
        locations=ok["code"].tolist(), z=ok["part_passoires"].tolist(),
        colorscale=pal["colorscale"], zmin=Z_MIN, zmax=Z_MAX,
        marker=dict(opacity=0.75, line=dict(color="white", width=0.8)),
        text=ok["nom"].tolist(), customdata=ok[["total", "surface_renover"]].to_numpy(),
        hovertemplate=("<b>%{text}</b><br>Bâtiments : %{customdata[0]:,.0f}"
                       "<br>Passoires (F+G) : %{z:.1%}"
                       "<br>Surface à rénover : %{customdata[1]:,.0f} m²<extra></extra>"),
        colorbar=dict(title="% F+G", tickformat=".0%", len=0.7),
    ))
    if len(low):                                              # données insuffisantes -> gris
        fig.add_trace(go.Choroplethmap(
            geojson=gj, featureidkey="properties.code",
            locations=low["code"].tolist(), z=[0] * len(low),
            colorscale=[[0, "#bdbdbd"], [1, "#bdbdbd"]], showscale=False,
            marker=dict(opacity=0.6, line=dict(color="white", width=0.5)),
            text=low["nom"].tolist(), customdata=low["total"].to_numpy(),
            hovertemplate="<b>%{text}</b><br>%{customdata:,.0f} bâtiment(s)"
                          "<br>Données insuffisantes<extra></extra>",
        ))
    if view["selected"]:                                      # contour de la zone sélectionnée
        fig.add_trace(go.Choroplethmap(
            geojson=gj, featureidkey="properties.code",
            locations=[view["selected"]], z=[0], showscale=False, hoverinfo="skip",
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            marker=dict(line=dict(color=pal["outline"], width=3)),
        ))
    fig.update_layout(
        map=dict(style="carto-positron", center=center, zoom=zoom),
        height=620, margin=dict(l=0, r=0, t=0, b=0),
        uirevision=f"{level}-{nav['region']}-{nav['dept']}",   # recadre à chaque navigation
    )
    return fig


def make_distribution(row, pal: dict) -> go.Figure:
    valeurs = [int(row[c]) for c in CLASSES]
    total = max(sum(valeurs), 1)
    fig = go.Figure(go.Bar(
        x=CLASSES, y=valeurs, marker_color=[pal["classes"][c] for c in CLASSES],
        text=[f"{v / total:.0%}" for v in valeurs], textposition="outside",
        hovertemplate="Classe %{x}<br>%{y:,} bâtiments<extra></extra>",
    ))
    fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0),
                      xaxis_title="Classe énergie", yaxis_title="Nb de bâtiments",
                      yaxis=dict(range=[0, max(valeurs + [1]) * 1.18]),
                      plot_bgcolor="white")
    return fig


def make_surface_chart(view: dict, pal: dict) -> go.Figure:
    d = view["df"].sort_values("surface_renover", ascending=False)
    sel = view["selected"]
    if len(d) > TOP_N:
        top = d.head(TOP_N)
        if sel and sel not in top["code"].values:             # garde la commune sélectionnée visible
            top = pd.concat([top.iloc[:-1], d[d["code"] == sel]])
        d = top
    labels = d["nom"].where(~d["nom"].duplicated(keep=False), d["nom"] + " (" + d["code"] + ")")
    opacity = [1.0 if (not sel or c == sel) else 0.45 for c in d["code"]]

    fig = go.Figure()
    for c in RENOVER:
        fig.add_trace(go.Bar(
            y=labels, x=d[f"S_{c}"], name=f"Classe {c}", orientation="h",
            marker=dict(color=pal["classes"][c], opacity=opacity),
            hovertemplate=f"%{{y}}<br>Classe {c} : %{{x:,.0f}} m²<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", height=max(320, 24 * len(d) + 120),
        margin=dict(l=0, r=10, t=30, b=0), plot_bgcolor="white",
        yaxis=dict(autorange="reversed", automargin=True),
        xaxis=dict(title="Surface à rénover (m²)", tickformat=".2s", gridcolor="#eeeeee"),
        legend=dict(orientation="h", y=1.06, x=0),
    )
    return fig


# --------------------------------------------------------------------------
# Mise en forme
# --------------------------------------------------------------------------
def fr(n, nd=0) -> str:
    return f"{n:,.{nd}f}".replace(",", "\u202f").replace(".", ",")


def fmt_surface(m2: float) -> str:
    return f"{fr(m2 / 1e6, 2)} M m²" if m2 >= 1e6 else f"{fr(m2)} m²"


def fmt_pct(x) -> str:
    return "n.d." if pd.isna(x) else f"{fr(x * 100, 1)} %"


CARD = {"flex": "1", "background": "#f6f7f9", "borderRadius": "8px", "padding": "10px 14px"}
BTN = {"padding": "6px 12px", "marginRight": "8px", "border": "1px solid #c5c9d1",
       "borderRadius": "6px", "background": "white", "cursor": "pointer"}
HIDDEN = {**BTN, "display": "none"}


def card(label, value, extra=None):
    return html.Div(style=CARD, children=[
        html.Div(label, style={"fontSize": "12px", "color": "#555"}),
        html.Div(value, style={"fontSize": "22px", "fontWeight": "600"}),
        extra if extra is not None else html.Div("\u00a0", style={"fontSize": "12px"}),
    ])


def delta_span(part, ref_part, label, pal):
    if label == "" or pd.isna(part) or pd.isna(ref_part):
        return None
    pts = (part - ref_part) * 100
    txt = f"{pts:+.1f}".replace(".", ",").replace("-", "−") + f" pts {label}"
    return html.Div(txt, style={"fontSize": "12px", "color": pal["bad"] if pts > 0 else pal["good"]})


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
app = Dash(__name__, title="Parc tertiaire - DPE")
server = app.server

app.layout = html.Div(style={"fontFamily": "system-ui, sans-serif", "maxWidth": "1400px",
                             "margin": "0 auto", "padding": "16px"}, children=[
    dcc.Store(id="nav", data=EMPTY_NAV),
    dcc.Download(id="download"),

    html.Div(style={"marginBottom": "12px"}, children=[
        html.H1("Comment se répartit le DPE du parc tertiaire ?", style={"margin": "0 0 4px"}),
        html.Div("Répartition de la surface DPE selon les territoires.", style={"color": "#666"}),
    ]),

    html.Div(style={"display": "flex", "alignItems": "center", "marginBottom": "8px",
                    "flexWrap": "wrap", "gap": "4px"}, children=[
        html.Button("← France", id="btn-france", style=HIDDEN),
        html.Button("← Retour aux départements", id="btn-region", style=HIDDEN),
        html.Button("Voir les communes", id="btn-communes", style=HIDDEN),
        html.Button("Désélectionner", id="btn-clear", style=HIDDEN),
        html.Span(id="crumb", style={"fontWeight": "600", "marginLeft": "8px"}),
    ]),

    html.Div(style={"display": "grid", "gridTemplateColumns": "3fr 2fr", "gap": "24px"}, children=[
        html.Div([
            dcc.Loading(dcc.Graph(id="map", config={"scrollZoom": True, "displaylogo": False})),
            html.Div(style={"display": "flex", "gap": "24px", "alignItems": "center",
                            "flexWrap": "wrap", "marginTop": "8px"}, children=[
                html.Div([html.Label("Graine aléatoire "),
                          dcc.Input(id="seed", type="number", value=42, min=0, step=1,
                                    debounce=True, style={"width": "80px"})]),
                html.Div(style={"width": "380px"}, children=[
                    html.Label("Seuil min. de bâtiments par commune (sous le seuil : gris)"),
                    dcc.Slider(id="seuil", min=0, max=100, step=5, value=20,
                               marks={0: "0", 20: "20", 50: "50", 100: "100"},
                               tooltip={"placement": "bottom"}),
                ]),
                html.Button("Télécharger les données (CSV)", id="btn-csv", style=BTN),
                html.Button("Filtre Daltonie : désactivée", id="btn-palette", style=BTN),
            ]),
        ]),
        html.Div([
            html.H2(id="panel-title", style={"marginTop": "0"}),
            html.Div(id="metrics", style={"display": "flex", "gap": "10px"}),
            html.Div(id="note", style={"color": "#b26a00", "fontSize": "13px", "margin": "6px 0"}),
            html.H4("Répartition du parc par classe énergie", style={"marginBottom": "0"}),
            dcc.Graph(id="dist", config={"displayModeBar": False}),
            html.H4(id="surface-title", style={"marginBottom": "0"}),
            dcc.Graph(id="surface-chart", config={"displayModeBar": False}),
        ]),
    ]),
])


@app.callback(
    Output("nav", "data"), Output("map", "clickData"),
    Input("map", "clickData"), Input("btn-france", "n_clicks"), Input("btn-region", "n_clicks"),
    Input("btn-communes", "n_clicks"), Input("btn-clear", "n_clicks"),
    State("nav", "data"), prevent_initial_call=True,
)
def navigate(click, *_):
    nav = _[-1]
    trigger = ctx.triggered_id
    if trigger == "map" and not click:
        return no_update, no_update
    return apply_event(nav, trigger, click), None             # None : permet de recliquer la même zone


@app.callback(
    Output("map", "figure"), Output("crumb", "children"), Output("panel-title", "children"),
    Output("metrics", "children"), Output("note", "children"), Output("dist", "figure"),
    Output("surface-title", "children"), Output("surface-chart", "figure"),
    Output("btn-france", "style"), Output("btn-region", "style"),
    Output("btn-communes", "style"), Output("btn-communes", "children"),
    Output("btn-clear", "style"), Output("btn-palette", "children"),
    Input("nav", "data"), Input("seuil", "value"), Input("seed", "value"),
    Input("btn-palette", "n_clicks"),
)
def render(nav, seuil, seed, n_palette):
    seed, seuil = int(seed or 0), int(seuil or 0)
    okabe = (n_palette or 0) % 2 == 1                         # un clic sur deux
    pal = PALETTES["okabe" if okabe else "default"]
    v = build_view(nav, seed)
    row, ref = v["row"], v["ref"]

    metrics = [
        card("Bâtiments", fr(row["total"])),
        card("Part de passoires (F+G)", fmt_pct(row["part_passoires"]),
             delta_span(row["part_passoires"], None if ref is None else ref["part_passoires"],
                        v["ref_label"], pal)),
        card("Surface à rénover (E+F+G)", fmt_surface(row["surface_renover"])),
    ]
    note = ""
    if nav["commune"] and row["total"] < seuil:
        note = f"Moins de {seuil} bâtiments : indicateur peu fiable."

    df = v["df"]

    scope = {"france": "France", "region": NOM_REGION.get(nav["region"], ""),
             "dept": NOM_DEPT.get(nav["dept"], "")}[v["level"]]
    surf_title = f"Surface à rénover (classes E, F, G) - {v['unit']} · {scope}"
    if len(df) > TOP_N:
        surf_title += f" (top {TOP_N} sur {len(df)})"

    show = lambda cond: BTN if cond else HIDDEN               # noqa: E731
    btn_communes_label = f"Voir les communes - {NOM_DEPT[nav['dept']]}" if nav["dept"] else ""
    clear_visible = bool(nav["commune"]) if nav["communes"] else bool(nav["dept"])

    return (make_map(v, nav, seuil, pal), v["crumb"], f"{v['niveau_txt']} : {v['titre']}",
            metrics, note, make_distribution(row, pal),
            surf_title, make_surface_chart(v, pal),
            show(nav["region"] is not None), show(nav["communes"]),
            show(bool(nav["dept"]) and not nav["communes"]), btn_communes_label,
            show(clear_visible),
            "Filtre Daltonie : activée" if okabe else "Filtre Daltonie : désactivée")


@app.callback(Output("download", "data"), Input("btn-csv", "n_clicks"),
              State("seed", "value"), prevent_initial_call=True)
def download(_, seed):
    cols = ["code", "nom", "code_region"] + CLASSES + SURF_COLS
    return dcc.send_data_frame(dept_data(int(seed or 0))[cols].to_csv,
                               "dpe_test_departements.csv", index=False)


if __name__ == "__main__":
    app.run(debug=True)