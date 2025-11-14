import pandas as pd
from pyproj import Geod
import numpy as np
import xarray as xr
from shapely.geometry import Polygon, LineString, Point

def compute_heading(df: pd.DataFrame,
                    lon_name: str = "lon",
                    lat_name: str = "lat") -> pd.Series:
    """
    Calcule le cap (en degrés, 0°=Nord, 90°=Est) entre points successifs
    dans une DataFrame contenant lat, lon.
    """
    geod = Geod(ellps="WGS84")
    
    # Décalage des coordonnées pour avoir les points successifs
    lon1, lat1 = df[lon_name].values[:-1], df[lat_name].values[:-1]
    lon2, lat2 = df[lon_name].values[1:], df[lat_name].values[1:]
    
    # Calcul des azimuts avant (cap du point i vers i+1)
    az, _, _ = geod.inv(lon1, lat1, lon2, lat2)
    
    # Ramener les angles dans [0, 360)
    az = (az + 360) % 360
    
    # Ajouter NaN au début pour aligner la taille
    return pd.Series([None, *az], index=df.index, name="heading")


def extract_reflectivity_cone(ds: xr.Dataset, 
                              lat0: float, lon0: float,
                              heading: float, 
                              O: float = 120, 
                              R: float = 40) -> xr.DataArray:
    """
    Extrait les valeurs de reflectivity dans un cône défini par (lat0, lon0, heading),
    une ouverture O (en degrés) et un rayon R (en km, défaut=40 km).
    Le calcul est optimisé en limitant le domaine à une bbox autour du point central.
    """
    geod = Geod(ellps="WGS84")
    R_m = R * 1000

    # Identifier les noms des coordonnées
    lat_name = "lat" if "lat" in ds else "latitude"
    lon_name = "lon" if "lon" in ds else "longitude"

    refl = ds["reflectivity"]
    lat = ds[lat_name]
    lon = ds[lon_name]

    # Calcul de la bbox géographique approximative
    dlat = R / 111.0
    dlon = R / (111.0 * np.cos(np.deg2rad(lat0)))
    lat_min, lat_max = lat0 - dlat, lat0 + dlat
    lon_min, lon_max = lon0 - dlon, lon0 + dlon

    mask_bbox = ((lat >= lat_min) & (lat <= lat_max) &
                    (lon >= lon_min) & (lon <= lon_max))
    
    # Extraire le sous-domaine minimal englobant la bbox
    iy, ix = np.where(mask_bbox)
    if len(iy) == 0:
        raise ValueError("La bbox ne recouvre aucun point de la grille.")
    y_min, y_max = iy.min(), iy.max()
    x_min, x_max = ix.min(), ix.max()
    ds_sub = ds.isel({lat.dims[0]: slice(y_min, y_max+1),
                        lat.dims[1]: slice(x_min, x_max+1)})
    lat = ds_sub[lat_name].values
    lon = ds_sub[lon_name].values
    refl = ds_sub["reflectivity"]
    lons, lats = lon, lat  # déjà 2D

    # Distances et azimuts à partir du centre
    az, _, dist = geod.inv(np.full_like(lons, lon0), 
                           np.full_like(lats, lat0), 
                           lons, lats)

    # Différence d'angle ramenée à [-180, 180]
    angle_diff = (az - heading + 180) % 360 - 180

    # Masque du cône
    mask = (np.abs(angle_diff) <= O/2) & (dist <= R_m)

    # Application du masque
    cone_refl = refl.where(mask)

    return cone_refl




def cone_geometry(lat0: float, lon0: float,
                  heading: float, 
                  O: float = 120,
                  R: float = 40):
    """
    Return Shapely geometries for a cone footprint:
    - A triangle (Polygon)
    - The central axis (LineString)
    
    Parameters
    ----------
    lat0, lon0 : float
        Cone apex coordinates.
    heading : float
        Central heading (degrees from north, clockwise).
    O : float, default=120
        Opening angle of the cone (degrees).
    R : float, default=40
        Cone length in km.
    """
    geod = Geod(ellps="WGS84")

    # Convert R to meters
    R_m = R * 1000

    # Endpoints of left and right rays
    left_az = heading - O / 2
    right_az = heading + O / 2

    lon_left, lat_left, _ = geod.fwd(lon0, lat0, left_az, R_m)
    lon_right, lat_right, _ = geod.fwd(lon0, lat0, right_az, R_m)

    # Central line endpoint
    lon_c, lat_c, _ = geod.fwd(lon0, lat0, heading, R_m)

    # Build geometries
    cone_poly = Polygon([
        (lon0, lat0),
        (lon_left, lat_left),
        (lon_right, lat_right),
        (lon0, lat0)
    ])
    axis_line = LineString([
        (lon0, lat0),
        (lon_c, lat_c)
    ])

    return cone_poly, axis_line