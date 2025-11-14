from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import pandas as pd
from opera_retrieval.diagnostics import compute_heading

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