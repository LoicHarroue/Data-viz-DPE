Question métier
Quelle est la question que l’analyse doit éclairer ?

Comment se répartit le parc étudié selon les classes énergétiques du DPE ?
Quelle part du parc doit être prioritairement rénovée ?
Pourquoi cette question est importante ?

Elle permet d’évaluer l’état énergétique du parc étudié.
Elle permet d’identifier les logements les moins performants.
Elle permet d’estimer l’importance des besoins de rénovation énergétique.
Pour qui ?
Les collectivités territoriales.
Les décideurs publics.
Les acteurs de la rénovation énergétique.
Les professionnels du bâtiment et de l’énergie.
Qu’est-ce que le lecteur doit pouvoir faire ou décider ?
Identifier les classes DPE les plus représentées.
Mesurer la part des passoires énergétiques F et G.
Estimer la surface correspondant aux classes E, F et G.
Repérer les catégories les plus prioritaires.
Prioriser les actions de rénovation énergétique.
Périmètre des données analysées
Nombre total de DPE étudiés :

10 000 DPE
Répartition des types de bâtiments :

6 346 appartements
3 335 maisons
319 immeubles
Qualité de la classe DPE :

10 000 DPE sur 10 000 disposent d’une classe A à G exploitable
Doublons sur numero_dpe :

0 doublon détecté
KPI 1 — Répartition des DPE par classe énergétique
Objectif :

Mesurer la proportion de DPE appartenant à chaque classe énergétique de A à G.
Question à laquelle ce KPI répond :

Quelles classes énergétiques sont les plus représentées dans le parc étudié ?
Calcul :

Nombre de DPE de la classe / Nombre total de DPE × 100.
Colonne utilisée :

etiquette_dpe
Résultats :

Classe A :
184 DPE
1,84 %
Classe B :
631 DPE
6,31 %
Classe C :
3 692 DPE
36,92 %
Classe D :
3 053 DPE
30,53 %
Classe E :
1 572 DPE
15,72 %
Classe F :
569 DPE
5,69 %
Classe G :
299 DPE
2,99 %
Interprétation :

Les classes C et D dominent largement le parc étudié.
Elles représentent ensemble 67,45 % des DPE.
Les classes les plus performantes A et B restent minoritaires avec 8,15 % du total.
Visualisation :

Diagramme en barres ordonné de A à G.
Utilité :

Comprendre rapidement la performance énergétique globale du parc étudié.
Identifier les classes les plus représentées.
KPI 2 — Part des passoires énergétiques
Objectif :

Mesurer la part des DPE classés F et G.
Question à laquelle ce KPI répond :

Quelle part du parc étudié correspond aux logements les plus énergivores ?
Classes concernées :

F
G
Calcul :

(Nombre de DPE F + Nombre de DPE G) / Nombre total de DPE × 100.
Colonne utilisée :

etiquette_dpe
Résultat :

Nombre de DPE F :
569
Nombre de DPE G :
299
Nombre total de passoires F/G :
868
Part des passoires énergétiques :
8,68 %
Interprétation :

Environ 1 DPE sur 12 du jeu étudié est classé F ou G.
Ces 868 observations constituent le cœur de la cible prioritaire pour les actions de rénovation énergétique.
Visualisation :

Carte KPI avec :
8,68 % de passoires énergétiques
Afficher également :
868 DPE classés F ou G
Utilité :

Mesurer l’importance des logements ayant les plus mauvaises performances énergétiques.
Identifier la part du parc à traiter en priorité.
KPI 3 — Surface prioritaire à rénover
Objectif :

Estimer la surface totale correspondant aux classes énergétiques les moins performantes.
Question à laquelle ce KPI répond :

Quelle surface totale appartient aux classes prioritaires pour la rénovation ?
Classes concernées :

E
F
G
Calcul :

Somme des surfaces des DPE classés E, F et G.
Unité :

m²
Colonnes utilisées :

etiquette_dpe
type_batiment
surface_habitable_logement
surface_habitable_immeuble
Règle de calcul :

Pour une maison ou un appartement :
utiliser surface_habitable_logement.
Pour un immeuble :
utiliser surface_habitable_immeuble.
Résultats :

Nombre de DPE classés E, F ou G :
2 440 DPE
Surface totale E/F/G calculée avec la règle ci-dessus :
208 532,3 m²
Dont maisons + appartements :
156 849,5 m²
Dont immeubles :
51 682,8 m²
Interprétation :

Les classes E, F et G représentent 24,40 % des DPE étudiés.
Elles correspondent à 208 532,3 m² de surface potentiellement prioritaire selon la règle de calcul retenue.
Cette valeur donne une estimation de l’ampleur physique des besoins de rénovation.
Visualisation :

Carte KPI avec :
208 532,3 m² de surface E/F/G
Utilité :

Mesurer l’ampleur physique des travaux potentiels.
Aider à dimensionner les besoins de rénovation.
Nettoyage des données
Vérifier la présence d’une classe DPE exploitable.

Résultat :
10 000 / 10 000 observations exploitables
Garder uniquement les classes A à G.

Résultat :
10 000 observations conservées
Convertir les colonnes de surface en valeurs numériques.

Vérifier les surfaces utilisées pour le calcul.

Résultat :
aucune surface de référence manquante
aucune surface de référence nulle ou négative
Vérifier les doublons sur numero_dpe.

Résultat :
0 doublon
Vérifier qu’une même adresse peut contenir plusieurs DPE.

Cette situation existe dans les données et doit être prise en compte dans l’interprétation.
Contrôles qualité
Nombre de lignes avant nettoyage :

10 000
Nombre de lignes après filtrage des classes A à G :

10 000
Nombre de DPE sans classe énergétique exploitable :

0
Nombre de surfaces de référence manquantes :

0
Nombre de surfaces de référence nulles ou négatives :

0
Nombre de doublons sur numero_dpe :

0
Nombre final d’observations utilisées :

10 000
Visualisations finales
Visualisation 1 :

Diagramme en barres de la répartition des classes A à G.
Mettre en évidence :
C : 36,92 %
D : 30,53 %
Visualisation 2 :

Carte KPI :
8,68 % de passoires F/G
868 DPE concernés
Visualisation 3 :

Carte KPI :
208 532,3 m² de surface E/F/G
Visualisations bonus :

Répartition par département.
Répartition par commune.
Répartition par type de bâtiment.
Répartition par période de construction.
Interprétation globale
Le parc étudié est principalement concentré dans les classes intermédiaires :

C : 36,92 %
D : 30,53 %
Les classes C et D représentent ensemble :

67,45 % des DPE
Les passoires énergétiques F et G représentent :

8,68 %
soit 868 DPE
Les classes E, F et G représentent :

24,40 % des DPE
soit 2 440 observations
La surface associée aux classes E, F et G est estimée à :

208 532,3 m²
Ces résultats permettent de distinguer deux niveaux d’action :

priorité forte :
classes F et G
priorité élargie :
classes E, F et G
Limites de l’analyse
Une ligne DPE ne correspond pas toujours à un bâtiment complet.
Une même adresse peut contenir plusieurs DPE.
Un DPE est une estimation conventionnelle et non une consommation réelle.
Le jeu de 10 000 DPE étudié ne représente pas nécessairement l’ensemble du parc immobilier français.
Le KPI de surface mélange deux niveaux d’observation :
surface du logement pour les maisons et appartements ;
surface de l’immeuble pour les DPE immeuble.
Il existe donc un risque de double comptage si un DPE immeuble et des DPE appartements du même bâtiment sont tous deux présents.
Pour une estimation physique définitive du parc, il faudrait dédupliquer les bâtiments ou choisir un niveau d’analyse unique.
Décision finale
Prioriser les actions de rénovation énergétique sur les logements et bâtiments les moins performants.
Cibler en premier les 868 DPE classés F et G.
Étendre ensuite la réflexion aux 2 440 DPE classés E, F ou G.
Utiliser les 208 532,3 m² comme indicateur de volume à traiter, tout en conservant la limite méthodologique liée au double comptage possible.
Conclusion
Le parc étudié est majoritairement composé de DPE classés C et D.
8,68 % des DPE sont des passoires énergétiques F ou G.
24,40 % des DPE sont classés E, F ou G.
La surface E/F/G calculée atteint 208 532,3 m².
Ces indicateurs permettent d’identifier clairement les catégories à traiter en priorité et d’orienter les décisions de rénovation énergétique.
Phrase courte pour l’oral
Notre analyse porte sur 10 000 DPE.
Les classes C et D représentent 67,45 % du parc étudié.
Les passoires F et G représentent 8,68 %, soit 868 DPE.
Les classes E, F et G représentent 2 440 DPE et environ 208 532 m² de surface.
L’objectif est d’utiliser ces indicateurs pour identifier et prioriser les besoins de rénovation énergétique.