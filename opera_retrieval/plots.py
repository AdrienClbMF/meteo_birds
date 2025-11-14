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


# RADARreflc colormap
vmin, vmax = 0, 150
turbo = cm.get_cmap("turbo", 256)

colors = [(0.96, 0.96, 0.96)] + [turbo(i) for i in range(1, 256)]
RFLC_CM = mcolors.ListedColormap(colors)

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
    ax.coastlines(resolution="50m")
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=1)
    ax.gridlines(draw_labels=True)

    # Set bounding box if provided
    if bbox is not None:
        lon_min, lon_max, lat_min, lat_max = bbox
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    plt.colorbar(im, ax=ax, label=var_name)
    plt.title(f"{title} on {date_str}", fontweight="bold")


    if add_poly :
        # Overlay add poly
        for poly in add_poly :
            x, y = poly.exterior.xy
            plt.plot(x, y, color="red", lw=2)

    plt.show()



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