"""Extraction of meteorological diagnostics from radar data for bird tracking.

This script extracts reflectivity diagnostics from radar data for bird tracking
datasets. It downloads missing radar data if needed and computes various
meteorological diagnostics based on different cone configurations.

Attributes:
    INTEREST_FILES (list): List of bird tracking files to process.
    DIAG_RADII_LST (range): Range of radii for diagnostic cones.
    DIAG_OVERTURES_LST (range): Range of opening angles for diagnostic cones.
    DIAG_QUANTILES_LST (list): List of quantiles to compute for diagnostics.
    DIAG_NAMES (list): Generated names for all diagnostic combinations.
    GET_LACKING_DATA (bool): Flag to indicate if missing data should be downloaded.
"""
import pandas as pd
from datetime import datetime, timezone
from meteo_birds.open_data_server import OpenDataServer
from meteo_birds.utils import (
    get_available_radar_dates,
    process_birds_data
)
from meteo_birds.settings import BIRDS_DATA_PATH
from meteo_birds.formatting import extract_radar_da
from meteo_birds.diagnostics import extract_reflectivity_cone

# =============================================================================
# Reading bird data and adding additional columns info to link it to RADAR data
# =============================================================================

INTEREST_FILES = [
    #"simulation_trk_241908",
    "simulation_trk_243157",
    "simulation_trk_370105",
    "simulation_trk_370122"
]

DIAG_RADII_LST = range(10,90,10)
DIAG_OVERTURES_LST = range(45,180,45)
DIAG_QUANTILES_LST = [.5,.75,.9,1]
DIAG_NAMES = []

for rayon in DIAG_RADII_LST :
    for overture in DIAG_OVERTURES_LST :
        cone_name = f"Cone_O_{overture}_R_{rayon}"
        for quant in DIAG_QUANTILES_LST :
            DIAG_NAMES.append(f"{cone_name}_Q_{quant*100:.0f}")


GET_LACKING_DATA = False

def radar_db_download(
        birds_df : pd.DataFrame,
        download_lacking_data: bool = True
        ) -> None :
    """Download missing radar data for bird tracking files.

    This function checks for missing radar data files in the local database
    and downloads them if needed using the OpenDataServer.

    Args:
        birds_df (pd.DataFrame): DataFrame containing bird tracking data
        download_lacking_data (bool): Flag indicating whether to download
            missing data. Defaults to True.
    """
    # Detecting lacking files in the local DB
    lacking_files = [fn for fn in birds_df.RADAR_archive_fn.unique()
                    if fn not in get_available_radar_dates().values()]
    lacking_dates = [datetime.strptime(dat_str.split("_")[-1].split(".")[0],  '%Y-%m-%dT%H%M%S').replace(tzinfo=timezone.utc)
                    for dat_str in lacking_files]

    print(f"There are {len(lacking_dates)} dates lacking")


    # Getting the lacking data through the custom DataServer object
    if download_lacking_data :
        mf_server = OpenDataServer()

        for dat in lacking_dates[::-1] :
            try :
                _ = mf_server.get_radar_composite(dat)
            except Exception as e :
                print(f"Did not manage to download file for date {dat} : {e}")

def computing_diagnostics(
    birds_df : pd.DataFrame,
    bird_row_info : pd.Series,
    idx : int
    ) -> None :
    """Compute meteorological diagnostics for a bird tracking point.

    This function extracts radar data for a specific bird tracking point and
    computes various reflectivity diagnostics based on different cone configurations.

    Args:
        birds_df (pd.DataFrame): DataFrame containing bird tracking data
        bird_row_info (pd.Series): Series containing information for a single bird tracking point
        idx (int): The index of the considered bird tracking point
    """

    print(f"[{idx}/{birds_df.shape[0]}] : Point {bird_row_info.Longitude}/{bird_row_info.Latitude} at {bird_row_info.UTC_datetime}")
    radar_ds = extract_radar_da(bird_row_info.RADAR_hdf5_dat.replace(tzinfo=timezone.utc))
    if radar_ds :
        for rayon in DIAG_RADII_LST :
            for overture in DIAG_OVERTURES_LST :
                # print(" \n")
                # print(f"Computing cone with radius {rayon} and angle {overture}, on position ({bird_row_info.Longitude}, {bird_row_info.Latitude})... ", end="")
                cone_name = f"Cone_O_{overture}_R_{rayon}"
                cone_da = extract_reflectivity_cone(
                    radar_ds,
                    bird_row_info.Latitude,
                    bird_row_info.Longitude,
                    bird_row_info.direction_deg,
                    overture,
                    rayon
                )
                # print("OK")
                for quant in DIAG_QUANTILES_LST :
                    diag_name = f"{cone_name}_Q_{quant*100:.0f}"
                    birds_df.at[idx, diag_name] = cone_da.quantile(quant, skipna=True).item()
    else :
        print(f"PROBLEM : No archive available for {row.RADAR_hdf5_dat}")



if __name__ == "__main__":
    for bird_file in INTEREST_FILES :
        print(f"Handling File {bird_file}.csv \n")

        try : 
            birds_df = process_birds_data(BIRDS_DATA_PATH / f"{bird_file}.csv", csv_fmt_type=2)
        except Exception as e:
            print(f"Did not manage to load {bird_file} : {e}")
            print(f"Skipping file {bird_file}")
            continue

        # =============================================================================
        # Downloading a local RADAR database, corresponding to the bird data datetimes
        # =============================================================================
        radar_db_download(birds_df, GET_LACKING_DATA)

        # =============================================================================
        # Choosing which diagnostics to retrieve
        # =============================================================================

        # Génération et ajout dynamique de colonnes pour les diagnostics 
        # de réflectivité météorologique basés sur des combinaisons 
        # de rayons, angles d'ouverture et quantiles

        lacking_diags = [diag for diag in DIAG_NAMES 
                        if diag not in birds_df.columns]       
        birds_df = pd.concat(
            [birds_df] + [pd.Series(None, name=n) 
                        for n in lacking_diags],
            axis=1
        )

        # =============================================================================
        # Extracting data 
        # ============================================================================

        for idx, row in birds_df.iterrows() :
            #print(f"{idx/birds_df.shape[0]*100:.0f}%", end="\r")
            computing_diagnostics(birds_df, row, idx)

        completed_file_path = BIRDS_DATA_PATH / f"{INTEREST_FILES[0]}_reflectivity.csv"
        birds_df.to_csv(completed_file_path)
        print(f"File {bird_file}.csv has been completed and saved to {completed_file_path} \n")
