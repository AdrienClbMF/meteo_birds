from pathlib import Path
import os

# Path of the current file
BASE_DIR = Path(__file__).parent

# Path to the radar data directory
RADAR_DATA_PATH = (BASE_DIR / "../data_radar").resolve()

# Path to the birds data directory
BIRDS_DATA_PATH = (BASE_DIR / "../data_birds").resolve()

# Path to the output geotiffs data directory
GEOTIFF_OUTPUT_PATH = (BASE_DIR / "../output_geotiffs").resolve()

# API main adress
################################################
API_BASE_URL = "https://partner-api.meteofrance.fr/partner"

# API Key Handling
################################################

def get_api_key(creds_path : Path) -> str:
    "Loads the API key from the credential file"
    try:
        api_key = Path(creds_path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Le fichier spécifié par API_KEY_PATH est introuvable: {creds_path}")
    except Exception as e:
        raise RuntimeError(f"❌ Impossible de lire la clé API depuis {creds_path}: {e}")

    # (Optionnel) Vérifie que la clé n’est pas vide
    if not api_key:
        raise ValueError(f"❌ Le fichier {creds_path} ne contient pas de clé API valide.")

    return api_key

CREDS_PATH = (BASE_DIR / "../credentials/api_key.secrets.txt").resolve()
API_KEY = get_api_key(CREDS_PATH)

# Lecture de la clé depuis le fichier



# BBOXES
###################################

SPAIN_BBOX = (-10,5,35,45)
CANTABRICS_BBOX = (-12,5,40,47)