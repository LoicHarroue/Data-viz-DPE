choix de biblios : Dash, plotly, pandas, numpy
données pour la carte d'un repos publique gihub de gregoiredavid/france-geojson

Traitement des données :
On ne garde que 7 colonnes sur les ~65 : numero_dpe, date_fin_validite_dpe, etiquette_dpe, surface_utile, surface_shon, code_insee_ban et nom_commune_ban
On crée 4 CSV : communes.csv, departements.csv, regions.csv et france.csv
avec les comptages et surfaces A à G et les KPI déjà calculés : total, nb_passoires, part_passoires, surface_totale et surface_renover.

Question métier :
Où le besoin est-il à la fois fort en volume et en urgence ?	Surface à rénover × part de passoires

3 KPIs :
Part du parc par classe énergie (A à G)	nb de bâtiments par classe / total
Part de « passoires » (F et G)	bâtiments F+G / total, ou en % de surface
Surface à rénover	m² en classes E, F et G