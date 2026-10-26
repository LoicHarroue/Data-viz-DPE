Question métier :
Où le besoin est-il à la fois fort en volume et en urgence ?	Surface à rénover × part de passoires

3 KPIs :
Part du parc par classe énergie (A à G)	nb de bâtiments par classe / total
Part de « passoires » (F et G)	bâtiments F+G / total, ou en % de surface
Surface à rénover	m² en classes E, F et G

choix de biblios : Dash, plotly, pandas, numpy
données pour la carte d'un repos publique gihub de gregoiredavid/france-geojson

Traitement des données :
On ne garde que 7 colonnes sur les ~65 : numero_dpe, date_fin_validite_dpe, etiquette_dpe, surface_utile, surface_shon, code_insee_ban et nom_commune_ban
On crée 4 CSV : communes.csv, departements.csv, regions.csv et france.csv
avec les comptages et surfaces A à G et les KPI déjà calculés : total, nb_passoires, part_passoires, surface_totale et surface_renover.

calculs :
On normalise l'étiquette (pas d'espaces, majuscules et range de A à G)
On exclus les numero_dpe qui figurent aussi dans numero_dpe_remplace
On exclus les numero_dpe si date_fin_validite_dpe est antérieure à aujourd’hui
On nettoie les doublons
On déduit la région grace a un dictionaire 
On exclu l'outre mer et on ne garde que les 2 premiers charactere des départements
On complete les code communes ex : code de 4 chiffres complété à 5 (1001 → 01001) et arrondissements regroupés : 751xx → 75056
On retient la surface_utile si > 0, sinon surface_shon ; mise à 0 si absente ou supérieure à 1 000 000 m² (le bâtiment reste compté)

calculs kpi :
simple comptage par classe, a tout les niveaux
somme des surfaces au m² par classes
création d'un total et de nb_passoires (F+G) pour le calcul de part_passoires (nb_passoires / total)
surface_totale simple somme de S_A à S_G
surface_renover	simple somme de S_E + S_F + S_G
On recalcule pour chaque niveaux afin de ne jamais moyennés les pourcentages
