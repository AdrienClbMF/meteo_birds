import requests
from pathlib import Path
from meteo_birds.settings import (
    API_KEY,
    RADAR_DATA_PATH
)
from xarray import DataArray
from typing import Dict
from datetime import datetime, timedelta
from typing import List
import os



def get_api_data(api_url: str, output_path: str, 
                 max_retries: int = 5,
                 stop_on_maxretry: bool = False) -> Path:
    """
    Télécharge un fichier tar contenant des données radar depuis l'API
    Météo-France et le sauvegarde en local.

    Args:
        api_url (str): URL complète de l'API radar.
        output_path (str): Chemin local où sauvegarder le tar.

    Returns:
        Path: Chemin vers le fichier tar téléchargé.
    
    Raises:
        RuntimeError: En cas d'erreur HTTP ou d'écriture du fichier.
    """
    headers = {
        "accept": "application/tar",
        "apikey": API_KEY,
    }

    output_path = Path(output_path)

    for attempt in range(1, max_retries + 1):
        try:
            print(f"⬇️  Downloading radar data from API (attempt {attempt}/{max_retries})...")
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Sauvegarder en local
            output_path.write_bytes(response.content)
            print(f"✅ File saved to {output_path}")
            return output_path

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Attempt {attempt}/{max_retries} — HTTP error: {e}")
            if attempt == max_retries :
                if stop_on_maxretry:
                    raise RuntimeError(f"Erreur HTTP lors du téléchargement depuis {api_url}: {e}")
                else :
                    print("Giving up on this file. \n\n")

        # Pause 5s avant la prochaine tentative
        if attempt < max_retries:
            import time
            print("⏳ Waiting 5s before retry...")
            time.sleep(5)


def radar_da_stats(da : DataArray) -> Dict:
    """
    Retourne les statistiques de base d'un xarray.DataArray radar.
    
    Args:
        da (xarray.DataArray)
    
    Returns:
        dict: min, max, mean, std, median
    """
    stats = {
        "min": float(da.min().values),
        "max": float(da.max().values),
        "mean": float(da.mean().values),
        "std": float(da.std().values),
        "median": float(da.median().values)
    }
    return stats


def get_available_radar_dates() -> Dict[datetime, str] :
    filenames = [fn for fn in os.listdir(RADAR_DATA_PATH) if fn.endswith('.tar')]
    associated_dates =  [datetime.strptime(fn.split("_")[-1].split('.')[0], "%Y-%m-%dT%H%M%S")
                         for fn in filenames]
    return {
        dat: fn for dat, fn in zip(associated_dates, filenames)
    }

def dat_to_dat_half(dat):
    """Round a datetime to the start of the 0–12h or 12–24h half-day."""
    dat = dat.replace(minute=0, second=0, microsecond=0)
    hour = 12 if dat.hour >= 12 else 0
    return dat.replace(hour=hour)

def dat_to_5mn(dat):
    # Nombre total de secondes depuis le début de l'heure
    total_seconds = dat.minute * 60 + dat.second + dat.microsecond / 1e6
    remainder = total_seconds % (5 * 60)

    # Décide si on arrondit vers le bas ou vers le haut
    if remainder < (2.5 * 60):
        new_time = dat - timedelta(seconds=remainder)
    else:
        new_time = dat + timedelta(seconds=(5 * 60 - remainder))

    return new_time.replace(second=0, microsecond=0)