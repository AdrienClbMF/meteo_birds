from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from pathlib import Path
import pandas as pd
from datetime import datetime

from .diagnostics import compute_heading
from .utils import (
    dat_to_dat_half,
    dat_to_5mn,
)
from .settings import BIRDS_DEFAULT_CSV


@dataclass
class BirdPoint:
    lat: float
    lon: float
    dat: datetime

    @property
    def as_dict(self):
        return {"lat": self.lat, "lon": self.lon, "dat": self.dat}

@dataclass
class BirdTracks:
    serial_ID: str
    species: str
    points: List[BirdPoint]= field(default_factory=list)

    @property
    def data(self):
        data_df = pd.DataFrame([point.as_dict() for point in self.points()])
        data_df["heading"] = compute_heading(data_df)
        return data_df
    

def load_birds_df(
        birds_csv : Path = BIRDS_DEFAULT_CSV,
        bird_id : int = None
        ) -> pd.DataFrame :
    birds_df = pd.read_csv(birds_csv, index_col=0)
                           
    if bird_id :
        birds_df = birds_df.loc[birds_df['device_id'] == bird_id]
        if birds_df.empty : 
            raise ValueError(f"Bird_id {bird_id} is not present in the birds file.")
    birds_df['UTC_datetime'] = birds_df['UTC_datetime'].apply(lambda str : datetime.fromisoformat(str))
    birds_df['RADAR_archive_dat'] = birds_df['UTC_datetime'].apply(lambda dat : dat_to_dat_half(dat))
    birds_df['RADAR_archive_fn'] = birds_df['RADAR_archive_dat'].apply(lambda dat : f"OPERA_cirrus_REFLECTIVITY_{dat.strftime('%Y-%m-%dT%H')}0000.tar")
    birds_df['RADAR_hdf5_dat'] = birds_df['UTC_datetime'].apply(lambda dat : dat_to_5mn(dat))

    # Calculer l'écart absolu en secondes
    birds_df['timedelta_bird_vs_radar'] = (birds_df['UTC_datetime'] - birds_df['RADAR_hdf5_dat']).abs()

    # Pour chaque RADAR_hdf5_dat, garder la ligne avec le delta minimum
    birds_df = birds_df.loc[birds_df.groupby('RADAR_hdf5_dat')['timedelta_bird_vs_radar'].idxmin()].copy()

    # Optionnel : supprimer la colonne delta si tu veux
    birds_df.drop(columns='timedelta_bird_vs_radar', inplace=True)
    return birds_df