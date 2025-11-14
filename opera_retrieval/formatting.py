import io
import os
import tarfile
from datetime import datetime, timezone
from typing import Any, Tuple

import h5py
import numpy as np
import rasterio
import rioxarray
import xarray as xr
from pyproj import CRS, Proj, Transformer
from opera_retrieval.settings import RADAR_DATA_PATH
from opera_retrieval.utils import dat_to_dat_half

def odim_hdf5_to_dataset(
        hdf5_file: h5py.File, 
        var_name: str = "reflectivity",
        noise_as_zero: bool = True
    ) -> xr.Dataset:
    """
    Lit un HDF5 ODIM composite radar et renvoie un xarray.DataArray
    avec coordonnées lat/lon reconstruites à partir de la projection et des scales.
    
    Args:
        file_path (h5py.File): Fichier HDF5 ODIM.
        var_name (str): Nom du DataArray retourné.
        noise_as_zero (bool): Mettre les valeurs sous le seuil de détection utile, les valeurs négatives
                              correspondant à du bruit de fond ou du bruit radar, à 0.
    Returns:
        xr.DataArray: DataArray avec dims ("y","x") et coords lat/lon.
    """

    # Grille radar
    data = hdf5_file["dataset1"]["data1"]["data"][:]
    data = data[::-1, :]  # inverser l'axe Y pour que le nord soit en haut
    
    # Get les métadonnées de localisation
    where = dict(hdf5_file["where"].attrs)

    xsize = int(where["xsize"])
    ysize = int(where["ysize"])
    xscale = float(where["xscale"])
    yscale = float(where["yscale"])

    # Projection
    proj_laea = Proj(where["projdef"].decode())
    transformer = Transformer.from_proj(proj_laea, proj_laea.to_latlong(), always_xy=True)

    # Coin Lower Left en coordonnées projetées
    LL_lon = float(where["LL_lon"])
    LL_lat = float(where["LL_lat"])
    # Transformer LL en projection LAEA
    LL_x, LL_y = proj_laea(LL_lon, LL_lat)

    # Construire meshgrid projeté
    x_proj = LL_x + np.arange(xsize) * xscale
    y_proj = LL_y + np.arange(ysize) * yscale
    X, Y = np.meshgrid(x_proj, y_proj)

    # Transformer en lat/lon
    lon_grid, lat_grid = transformer.transform(X, Y)

    # Création des variables
    mask = np.where(data != -9999000.0, 1, 0)
    reflectivity = np.where(data != -9999000.0, data, np.nan)
    if noise_as_zero :
        reflectivity = np.where(reflectivity < 0, 0, reflectivity)


    # Construire le Dataset
    ds = xr.Dataset(
        {
            var_name: (("y","x"), reflectivity),
            "mask": (("y","x"), mask)
        },
        coords={
            "lat": (("y","x"), lat_grid),
            "lon": (("y","x"), lon_grid)
        }
    )

    ds.attrs["projdef"] = where["projdef"].decode()
    ds.attrs["xscale_m"] = float(where["xscale"])
    ds.attrs["yscale_m"] = float(where["yscale"])
    ds.attrs["xsize"] = int(where["xsize"])
    ds.attrs["ysize"] = int(where["ysize"])
    ds.attrs["LL_lat"] = float(where["LL_lat"])
    ds.attrs["LL_lon"] = float(where["LL_lon"])

    return ds

def radar_tar_to_dataset(
        tar_path: str, 
        timestep: int = 60) -> xr.Dataset:
    """
    Ouvre un fichier TAR contenant des HDF5 radar ODIM et
    concatène les fichiers sélectionnés selon la fréquence temporelle donnée.

    Args:
        tar_path (str): Chemin du fichier .tar (local).
        timestep (int): Pas de temps en minutes (p. ex. 5 pour ne garder que les multiples de 5).

    Returns:
        xr.Dataset: Dataset concaténé sur la dimension 'time'.
    """
    datasets = []

    with tarfile.open(tar_path, "r") as tar:
        for member in tar.getmembers():
            if not member.name.endswith(".hdf5"):
                continue  # ignorer autres fichiers éventuels

            # Extraire timestamp depuis le nom, ex: CIRRUS.REF_202506171200.hdf5
            try:
                ts_str = member.name.split("_")[1].split(".")[0]
                ts = datetime.strptime(ts_str, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
            except Exception:
                print(f"⚠️ Impossible de lire le timestamp dans {member.name}")
                continue

            # Filtrage selon timestep
            ts_minutes = ts.hour * 60 + ts.minute
            if ts_minutes % timestep != 0:
                continue

            print(f"📡 Lecture de {member.name} ({ts.isoformat()})")

            # Lecture en mémoire du fichier HDF5
            f = tar.extractfile(member)
            if f is None:
                continue
            with io.BytesIO(f.read()) as file_like, h5py.File(file_like, "r") as hdf:
                ds = odim_hdf5_to_dataset(hdf)
                ds = ds.expand_dims(time=[np.datetime64(ts)])
                datasets.append(ds)

    if not datasets:
        raise ValueError("Aucun fichier HDF5 valide trouvé dans le TAR.")

    print("∑ Concatening all datasets along time")
    ds_all = xr.concat(datasets, dim="time").sortby("time")
    return ds_all


def extract_radar_da(dat: datetime) -> xr.Dataset | None:
    """
    Extrait un fichier radar HDF5 depuis une archive tar correspondant à la date donnée.

    Parameters
    ----------
    dat : datetime
        Timestamp (UTC) du pas de temps radar à extraire.

    Returns
    -------
    xr.Dataset | None
        Dataset radar extrait, ou None si non trouvé.
    """
    if not dat.tzinfo :
        dat = dat.replace(tzinfo=timezone.utc)

    half_dat_str = dat_to_dat_half(dat).strftime("%Y-%m-%dT%H%M%S")
    filename = f"OPERA_cirrus_REFLECTIVITY_{half_dat_str}.tar"
    tar_path = RADAR_DATA_PATH / filename

    if not tar_path.exists():
        print(f"❌ Archive introuvable : {tar_path}")
        return None

    with tarfile.open(tar_path, "r") as tar:
        for member in tar.getmembers():
            if not member.name.endswith(".hdf5"):
                continue

            # Extraction du timestamp, ex: CIRRUS.REF_202506171200.hdf5
            try:
                ts_str = member.name.split("_")[1].split(".")[0]
                ts = datetime.strptime(ts_str, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
            except Exception as e:
                print(f"⚠️ Impossible de lire le timestamp dans {member.name}: {e}")
                continue

            if ts != dat:
                continue

            print(f"📡 Lecture de {member.name} ({ts.isoformat()})")

            f = tar.extractfile(member)
            if f is None:
                print(f"⚠️ Impossible d’extraire {member.name}")
                return None

            with io.BytesIO(f.read()) as file_like, h5py.File(file_like, "r") as hdf:
                da = odim_hdf5_to_dataset(hdf)
                return da

    print(f"⚠️ Aucun fichier HDF5 correspondant à {dat.isoformat()} trouvé dans {tar_path}")
    return None


def transform_bbox_to_raster_crs(
    bbox: Tuple[float, float, float, float],
    raster_crs: str
) -> Tuple[float, float, float, float]:
    """
    Transforme une bbox (lon_min, lon_max, lat_min, lat_max) en coordonnées
    dans le CRS du raster (proj4 string ou EPSG).

    Parameters
    ----------
    bbox : tuple
        (lon_min, lon_max, lat_min, lat_max) en degrés.
    raster_crs : str
        CRS du raster, ex: "+proj=laea +lat_0=55 +lon_0=10 +x_0=1950000 +y_0=-2100000 +units=m +ellps=WGS84"

    Returns
    -------
    tuple
        (x_min, x_max, y_min, y_max) dans le CRS du raster
    """

    lon_min, lon_max, lat_min, lat_max = bbox

    transformer = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)

    x_min, y_min = transformer.transform(lon_min, lat_min)
    x_max, y_max = transformer.transform(lon_max, lat_max)

    return x_min, x_max, y_min, y_max

def radar_timestep_ds_to_geotiff(
    ds: xr.Dataset,
    output_path: str,
    missing_value: Any = -9999,
    bbox: Tuple[float, float, float, float] = None  # (lon_min, lon_max, lat_min, lat_max)
) -> None:
    """
    Convertit un timestep radar en GeoTIFF mono-bande (reflectivity) avec CRS LAEA assigné,
    prêt pour QGIS, avec option de subset bbox après reprojection.
    """

    # --- Définir le CRS à partir de la projection LAEA ---
    crs_string = ds.attrs['projdef']    
    
    # Extraire les paramètres de projection pour construire la grille
    proj = Proj(ds.attrs['projdef'])
    x_0 = proj.x_0 if hasattr(proj, 'x_0') else 0.0
    y_0 = proj.y_0 if hasattr(proj, 'y_0') else 0.0
    x_scale = ds.attrs['xscale_m']
    y_scale = ds.attrs['yscale_m']

    # Coordonnées projetées (en mètres)
    x_coords = np.arange(ds.dims['x']) * x_scale + x_0
    y_coords = np.arange(ds.dims['y']) * (-y_scale) + y_0

    # Copier dataset pour éviter modification
    ds_copy = ds.copy()
    ds_copy = ds_copy.assign_coords({
        'x': x_coords, 
        'y': y_coords[::-1]
    })

    # Remplacer les NaN et appliquer le mask
    refl = ds_copy['reflectivity'].fillna(0)
    refl = xr.where(ds_copy['mask'] == 0, missing_value, refl)

    # Assigner CRS et dimensions spatiales
    refl.rio.write_crs(crs_string, inplace=True)
    wkt = refl.rio.crs.to_wkt()
    refl.rio.write_crs(wkt, inplace=True)
    refl.rio.set_spatial_dims(x_dim='x', y_dim='y', inplace=True)
    refl.rio.write_nodata(missing_value, inplace=True)

    # Subset bbox si fourni (en lon/lat)
    if bbox is not None:
        lon_min, lon_max, lat_min, lat_max = transform_bbox_to_raster_crs(
            bbox, ds.attrs['projdef']
        )
        refl = refl.rio.clip_box(
            minx=lon_min, maxx=lon_max, miny=lat_min, maxy=lat_max
        )

    # Sauvegarder le GeoTIFF
    refl.rio.to_raster(output_path, dtype='float32')
    print(f"✅ GeoTIFF mono-bande reflectivity créé : {output_path}")

        
def radar_tar_to_geotiff(
    tar_path: str, 
    output_dir: str,
    bbox: tuple = None,
    timestep: int = 60,
    as_biband: bool = False
) -> None:
    """
    Extrait les fichiers HDF5 radar d'un fichier TAR et les exporte en GeoTIFF multibande.

    Chaque HDF5 est transformé en un GeoTIFF avec deux bandes :
        - Band 1 : reflectivity
        - Band 2 : mask (0/1)

    Le CRS utilisé est WGS84 (EPSG:4326), et un sous-ensemble spatial
    peut être sélectionné via une bounding box.

    Args:
        tar_path (str): Chemin vers le fichier TAR contenant les HDF5 radar.
        output_dir (str): Dossier de sortie où seront enregistrés les GeoTIFFs.
        bbox (tuple, optional): (lon_min, lon_max, lat_min, lat_max) pour ne garder
                                qu’une région spécifique. Par défaut, None (tout le fichier).
        timestep (int, optional): Pas de temps en minutes pour filtrer les fichiers HDF5.
                                  Par défaut 60 (ne garder que les multiples d’heure).

    Raises:
        ValueError: Si aucun fichier HDF5 valide n’a été trouvé dans le TAR.

    Notes:
        - Les fichiers sont nommés d’après le nom original du HDF5, extension `.tif`.
        - Si la grille lat/lon est irrégulière, le sous-ensemble bbox utilise un masque booléen.
    """

    tar_empty = True

    with tarfile.open(tar_path, "r") as tar:
        for member in tar.getmembers():
            if not member.name.endswith(".hdf5"):
                continue

            # Extract timestamp
            try:
                ts_str = member.name.split("_")[1].split(".")[0]
                ts = datetime.strptime(ts_str, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
            except Exception:
                print(f"⚠️ Impossible de lire le timestamp dans {member.name}")
                continue

            ts_minutes = ts.hour * 60 + ts.minute
            if ts_minutes % timestep != 0:
                continue

            print(f"📡 Lecture de {member.name} ({ts.isoformat()})")

            f = tar.extractfile(member)
            if f is None:
                continue
            with io.BytesIO(f.read()) as file_like, h5py.File(file_like, "r") as hdf:
                ds = odim_hdf5_to_dataset(hdf)

                # Handling filename for geotif
                geotiff_fn = "_".join(member.name.split(".")[:-1]) + ".tif"
                out_path = os.path.join(output_dir, geotiff_fn)

                radar_timestep_ds_to_geotiff(
                    ds,
                    output_path=out_path,
                    bbox=bbox
                )
                tar_empty = False

    if tar_empty:
        raise ValueError("Aucun fichier HDF5 valide trouvé dans le TAR.")