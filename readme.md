# 🌦️🐦 MétéoBirds

**MétéoBirds** est un projet visant à croiser des données météorologiques d’observation de la convection avec des trajectoires d’oiseaux.  
Il fournit des outils pour télécharger, manipuler, explorer et visualiser les mosaïques radar OPERA européennes, ainsi que pour extraire des diagnostics pertinents pour l’étude du comportement des oiseaux.

---

## 🚀 Fonctionnalités principales

### 1. **Téléchargement des données OPERA**
- Récupération automatique des mosaïques radar OPERA Europe au format archivé `.tar`.
- Stockage local dans un dossier dédié : `data_radar/`.
- Gestion centralisée via la dataclass `OpenDataServer` (fichier `open_data_server.py`).
- Méthode `get_radar_composite()` avec **retry automatique** en cas d’erreur réseau ou serveur.
- Abstraction propre facilitant l’évolution future (sources multiples, API différentes…).

---

## 🗂️ Structure des modules

### `open_data_server.py`
- Contient la dataclass `OpenDataServer`.
- Fonctions principales :
  - `get_radar_composite()`: Télécharge et décompresse les archives `.tar`.
  - Gestion du retry automatique.
  - Paramétrage flexible (serveur, dates, formats, etc.).

---

### `formatting.py`
Outils pour explorer et manipuler les données OPERA :

- Parcours des `.tif` dans les archives OPERA.
- Extraction “à la volée” des champs ODIM **HDF5** encodés dans ces `.tif`.
- Reprojection dans le système **LAEA (Lambert Azimuthal Equal Area)**.
- Conversion automatique en objets `xarray.Dataset`.
- Fonctionnalité pour exporter en **GeoTIFF** compatible SIG (ex. QGIS).

---

### `plots.py`
Outils de visualisation :

- Plot des mosaïques radar (réflectivité, intensité convective, etc.).
- Option de **sous-échantillonnage** pour accélérer le rendu (résolution native très fine).
- Support natif des objets `xarray.Dataset`.

---

### `diagnostics.py`
Outils d’analyse géométrique :

- Extraction d’un **cône** défini par :
  - un sommet (position de l’oiseau),
  - un cap (direction, cap de l'oiseau),
  - un rayon,
  - un angle d’ouverture (réparti symétriquement autour du cap).
- Permet d’extraire les pixels radar situés dans le **“cône de vision”** de l’oiseau.
- Calcul de statistiques sur ce sous-ensemble (intensité convective moyenne, maximum, quantiles, etc.).

---

### `settings.py`
Configuration centralisée :

- Répertoires utiles (ex: dossier `data_radar/`).
- Localisation du fichier de **credentials** pour l’API Météo-France.
- URL de base de l’API.
- Paramètres généraux du projet.

---

## 📁 Organisation des dossiers
```
meteobirds/
│
├── open_data_server.py # Téléchargement et gestion des données OPERA
├── formatting.py # Extraction ODIM, conversion xarray, export GeoTIFF
├── plots.py # Visualisation radar
├── diagnostics.py # Extraction en cône + statistiques
├── settings.py # Chemins et paramètres API
├── data_radar/ # Données radar téléchargées
└── ...
```


---

## 🔧 Installation

```
bash
git clone https://github.com/<votre-utilisateur>/meteobirds.git
cd meteobirds
pip install -r requirements.txt
```
---

## ⚡ Pré-requis API et accès aux données

### 1. API Météo-France

Pour utiliser les fonctionnalités nécessitant l’API Météo-France :

1. Créez un compte sur le portail officiel : [https://portail-api.meteofrance.fr/web/fr/](https://portail-api.meteofrance.fr/web/fr/).
2. Une fois connecté, générez votre **token d’accès** (une longue string unique).
3. Stockez cette string dans un fichier texte dédié dans le dossier `credentials/` de votre projet.  
   Exemple :
   ```
   credentials/mf_api_token.txt
   ```
4. Assurez-vous que le fichier est bien référencé dans `settings.py` pour que l’API puisse l’utiliser automatiquement.

> 🔒 Ne partagez jamais ce fichier ou le token sur GitHub ou des plateformes publiques.

---

### 2. Accès aux données OPERA

Les mosaïques radar OPERA nécessitent une autorisation spécifique :

1. Contactez un administrateur ou la personne en charge des accès OPERA.
2. Envoyez une demande par mail en précisant votre projet et vos besoins.
3. Une fois l’accès accordé, vous pourrez télécharger les archives radar Europe (`.tar`) et les stocker localement dans le dossier `data_radar/`.

> 💡 Astuce : Conservez les fichiers `.tar` bruts pour un traitement ultérieur avec les utilitaires de `formatting.py` afin de reconstruire les `xarray.Dataset`.


## 🗺️ Utilisation dans QGIS

Lors de l’import d’un GeoTIFF généré via formatting.py,
sélectionnez la projection personnalisée LAEA ci-dessus (WKT ou Proj4).

L’emprise est donnée comme inconnue dans le WKT d’origine,
mais QGIS peut dériver les limites à partir du GeoTIFF.

#### ⚠️ Projection à paramétrer dans QGIS, en tant que projection custom

**WKT :**
```
PROJCRS["unknown",
BASEGEOGCRS["unknown",
DATUM["Unknown based on WGS84 ellipsoid",
ELLIPSOID["WGS 84",6378137,298.257223563,
LENGTHUNIT["metre",1],
ID["EPSG",7030]]],
PRIMEM["Greenwich",0,
ANGLEUNIT["degree",0.0174532925199433],
ID["EPSG",8901]]],
CONVERSION["unknown",
METHOD["Lambert Azimuthal Equal Area",
ID["EPSG",9820]],
PARAMETER["Latitude of natural origin",55,
ANGLEUNIT["degree",0.0174532925199433],
ID["EPSG",8801]],
PARAMETER["Longitude of natural origin",10,
ANGLEUNIT["degree",0.0174532925199433],
ID["EPSG",8802]],
PARAMETER["False easting",1950000,
LENGTHUNIT["metre",1,
ID["EPSG",8806]]],
PARAMETER["False northing",-2100000,
LENGTHUNIT["metre",1,
ID["EPSG",8807]]],
CS[Cartesian,2],
AXIS["(E)",east,
ORDER[1],
LENGTHUNIT["metre",1,
ID["EPSG",9001]]],
AXIS["(N)",north,
ORDER[2],
LENGTHUNIT["metre",1,
ID["EPSG",9001]]]]
```

**Proj4 :**
```
+proj=laea +lat_0=55.0 +lon_0=10.0 +x_0=1950000.0 +y_0=-2100000.0 +units=m +ellps=WGS84
```


## 📜 Licence

À définir (MIT, GPL ou autre).

---

## 📬 Contact

Pour toute question ou idée d’amélioration :  
**<votre email / GitHub>**