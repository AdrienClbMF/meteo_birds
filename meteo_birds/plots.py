import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import xarray as xr
import numpy as np
from typing import Tuple, Optional, List
from datetime import datetime
from shapely import Geometry
from pathlib import Path

from .settings import GRD_ELEVATION_FILEPATH


# RADARreflc colormap
vmin, vmax = 0, 150
turbo = cm.get_cmap("turbo", 256)

colors = [(0, 0, 0, 0)] + [turbo(i) for i in range(1, 256)]
RFLC_CM = mcolors.ListedColormap(colors)


def add_ground_elevation(
        ax: plt.Axes,
        crs: ccrs.CRS) -> None:
    """
    Ajoute le relief ETOPO1 Bedrock sur un axe Cartopy.
    
    Parameters
    ----------
    ax : plt.Axes
        L'axe matplotlib avec projection Cartopy.
    crs : ccrs.CRS
        La projection du raster (souvent ccrs.PlateCarree()).
    """
    if not GRD_ELEVATION_FILEPATH.exists():
        return

    # ouvrir le fichier
    try:
        ds = xr.open_dataset(GRD_ELEVATION_FILEPATH)
        z = ds["z"]
    except Exception as e:
        print(f"Erreur lors de l'ouverture du fichier de relief: {e}")
        return

    # récupérer l'étendue actuelle de l'axe pour zoom
    try:
        lon_min, lon_max, lat_min, lat_max = ax.get_extent(crs)
        # S'assurer que l'étendue est dans les limites valides
        lon_min = max(-180, lon_min)
        lon_max = min(180, lon_max)
        lat_min = max(-90, lat_min)
        lat_max = min(90, lat_max)
        extent = [lon_min, lon_max, lat_min, lat_max]
    except (ValueError, AttributeError) as e:
        print(f"Erreur lors de la récupération de l'extension de la carte: {e}")
        return

    # Extraire la portion du raster correspondant à l'étendue actuelle
    try:
        # Extraire les données dans l'étendue spécifiée
        z_subset = z.sel(x=slice(lon_min, lon_max), y=slice(lat_min, lat_max))
        
        # Convertir en valeurs numpy
        z_values = z_subset.values
        z_values[z_values < 0] = np.nan

        # Pour les fichiers ETOPO1 de haute résolution, on peut sous-échantillonner pour améliorer les performances
        # On utilise un facteur de sous-échantillonnage approprié
        if z_values.shape[0] > 2000:  # Si plus de 2000 lignes
            # Calculer un facteur de sous-échantillonnage raisonnable basé sur l'étendue
            # Pour éviter les problèmes de performance, on limite à 2000x4000 pixels
            factor_y = max(1, z_values.shape[0] // 2000)
            factor_x = max(1, z_values.shape[1] // 4000)
            
            # Appliquer le sous-échantillonnage
            z_values = z_values[::factor_y, ::factor_x]
        
        # tracer le relief avec imshow
        ax.imshow(
            z_values,
            origin="lower",
            extent=extent,
            transform=crs,
            cmap="terrain",    # remplacer par une cmap plus discrète si besoin
            vmin=-1400,
            vmax=4800,
            alpha=0.5,         # permet de superposer le radar
            zorder=0
        )
    except Exception as e:
        print(f"Erreur lors du tracé du relief: {e}")
    finally:
        # Fermer proprement le dataset
        try:
            ds.close()
        except:
            pass

def plot_radar_time_dataset(
    ds: xr.Dataset,
    timestep: int,
    var_name: str = "reflectivity",
    title: str = "Radar Composite",
    factor: int =10,
    bbox : Tuple[float, float, float, float] = None, 
):
    """
    Plot a radar composite from an xarray.Dataset containing:
      - 'reflectivity' (data > 0)
      - 'mask' (1 where valid, 0 elsewhere)

    Displays reflectivity in turbo colormap and a gray overlay where no data.

    Args:
        ds (xarray.Dataset): Dataset with 'reflectivity' and 'mask'
        var_name (str): Name of reflectivity variable
        title (str): Plot title
        factor (int): Subsampling factor for faster plotting
        bbox (tuple[float, float, float, float], optional):
            Geographic bounding box (lon_min, lon_max, lat_min, lat_max)
    """

    # Sous-échantillonnage
    reflectivity = ds[var_name][timestep, ::factor, ::factor]
    mask = ds["mask"][timestep, ::factor, ::factor]
    lat = ds["lat"][::factor, ::factor]
    lon = ds["lon"][::factor, ::factor]
    time = ds['time'][timestep].values
    date_str = np.datetime_as_string(time, unit="m")

    plt.figure(figsize=(12,10))
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Tracer la réflectivité
    im = ax.pcolormesh(
        lon, lat, reflectivity,
        cmap=RFLC_CM,
        shading="auto",
        vmin=vmin,
        vmax=vmax
    )

    # Build the mask overlay — 1 where no data, 0 where valid
    mask_overlay = np.where(mask == 0, 1.0, np.nan)

    # Use a ListedColormap with one color (gray) and force alpha handling
    gray_cmap = ListedColormap(["lightgray"])

    ax.pcolormesh(
        lon, lat, mask_overlay,
        cmap=gray_cmap,
        shading="auto",
        alpha=0.5,
        zorder=10
    )

    # Ajouter côtes et pays
    ax.coastlines(resolution="50m")
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=1)
    ax.gridlines(draw_labels=True)

    # Set bounding box if provided
    if bbox is not None:
        lon_min, lon_max, lat_min, lat_max = bbox
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    plt.colorbar(im, ax=ax, label=var_name)
    plt.title(f"{title} on {date_str}", fontweight="bold")
    plt.show()



def plot_radar_basicdataset(
    ds: xr.Dataset,
    dat: datetime,
    var_name: str = "reflectivity",
    title: str = "Radar Composite",
    factor: int =10,
    bbox : Tuple[float, float, float, float] = None, 
    add_poly: Optional[List[Geometry]] = None,
    output_path : Path = None,
    ground_elevation: bool = True
):
    """
    Plot a radar composite from an xarray.Dataset containing:
      - 'reflectivity' (data > 0)
      - 'mask' (1 where valid, 0 elsewhere)

    Displays reflectivity in turbo colormap and a gray overlay where no data.

    Args:
        ds (xarray.Dataset): Dataset with 'reflectivity' and 'mask'
        var_name (str): Name of reflectivity variable
        title (str): Plot title
        factor (int): Subsampling factor for faster plotting
        bbox (tuple[float, float, float, float], optional):
            Geographic bounding box (lon_min, lon_max, lat_min, lat_max)
    """

    # Sous-échantillonnage
    reflectivity = ds[var_name][::factor, ::factor]
    mask = ds["mask"][::factor, ::factor]
    lat = ds["lat"][::factor, ::factor]
    lon = ds["lon"][::factor, ::factor]
    date_str = dat.isoformat()

    plt.figure(figsize=(12,10))
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Tracer la réflectivité
    im = ax.pcolormesh(
        lon, lat, reflectivity,
        cmap=RFLC_CM,
        shading="auto"
    )

    # Build the mask overlay — 1 where no data, 0 where valid
    mask_overlay = np.where(mask == 0, 1.0, np.nan)

    # Use a ListedColormap with one color (gray) and force alpha handling
    gray_cmap = ListedColormap(["lightgray"])

    ax.pcolormesh(
        lon, lat, mask_overlay,
        cmap=gray_cmap,
        shading="auto",
        alpha=0.5,
        zorder=10
    )

    # Ajouter côtes et pays
    # =================================================
    # Ajouter côtes et frontières
    if ground_elevation :
        add_ground_elevation(ax, ccrs.PlateCarree())

    else :
        ax.add_feature(cfeature.LAND)
    ax.coastlines(resolution="50m", linewidth=2)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=1, ls ="--")

    # Grille avec labels
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False

    



    # Set bounding box if provided
    if bbox is not None:
        lon_min, lon_max, lat_min, lat_max = bbox
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    plt.colorbar(im, ax=ax, label=var_name)
    plt.title(f"{title} on {date_str}", fontweight="bold")


    if add_poly:
        # Overlay add poly
        poly_colors = ['red', 'green', 'orange', 'purple']
        for idx, poly in enumerate(add_poly):
            x, y = poly.exterior.xy
            color = poly_colors[idx % len(poly_colors)]  # cycle sur les couleurs
            plt.plot(x, y, color=color, lw=2)

    if output_path :
        plt.savefig(output_path)
    plt.show()
    plt.close()


def plot_radar_cone_da(
    da: xr.DataArray,
    add_poly: Optional[List[Geometry]] = None
):
    """
    Plot a radar composite from an xarray.Dataset containing:
      - 'reflectivity' (data > 0)
      - 'mask' (1 where valid, 0 elsewhere)

    Displays reflectivity in turbo colormap and a gray overlay where no data.

    Args:
        ds (xarray.Dataset): Dataset with 'reflectivity' and 'mask'
        var_name (str): Name of reflectivity variable
        title (str): Plot title
        factor (int): Subsampling factor for faster plotting
        bbox (tuple[float, float, float, float], optional):
            Geographic bounding box (lon_min, lon_max, lat_min, lat_max)
    """

    # Sous-échantillonnage
    lat = da["lat"]
    lon = da["lon"]

    plt.figure(figsize=(12,10))
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Tracer la réflectivité
    im = ax.pcolormesh(
        lon, lat, da,
        cmap=RFLC_CM,
        shading="auto"
    )

    # Ajouter côtes et pays
    ax.coastlines(resolution="50m")
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=1)
    ax.gridlines(draw_labels=True)

    plt.colorbar(im, ax=ax, label='Rflc')
    plt.title(f"Rflc cone", fontweight="bold")

    if add_poly :
        # Overlay add poly
        for poly in add_poly :
            x, y = poly.exterior.xy
            plt.plot(x, y, color="red", lw=2)

    plt.show()