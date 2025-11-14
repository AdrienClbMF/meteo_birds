from dataclasses import dataclass, field
from typing import List, Literal
import os
from datetime import datetime
from opera_retrieval.settings import API_BASE_URL, RADAR_DATA_PATH
from opera_retrieval.utils import get_api_data
from opera_retrieval.formatting import radar_tar_to_dataset
import xarray as xr

@dataclass
class OpenDataServer:
    nom: str = "MF_OpenData"

    def get_radar_composite(
            self,
            input_date: datetime,
            product_type: Literal['archive', 'realtime'] = 'archive', 
            algo_name: Literal['cirrus', 'odyssey', 'nimbus'] = 'cirrus',
            product_name: str = 'REFLECTIVITY',
            format: Literal['bufr', 'HDF5'] = 'HDF5'
            ) -> xr.Dataset :
        
        # Query build
        ##################################     
        date_str = input_date.strftime("%Y-%m-%dT%H0000Z")
        query_url = f'{API_BASE_URL}/radar/opera/1.0/{product_type}/{algo_name}/composite/{product_name}/{date_str}?format={format}'

        # Filename build
        ##################################
        fn_hour = "00"
        if input_date.hour >= 12 :
            fn_hour = "12"

        fn_dat_str = f"{input_date.strftime('%Y-%m-%d')}T{fn_hour}0000"
        filename = f"OPERA_{algo_name}_{product_name}_{fn_dat_str}.tar"
        
        # Data retrieval and local save
        ##################################
        print(f"Querying API via {query_url}")
        data_path = get_api_data(
            api_url=query_url,
            output_path=os.path.join(RADAR_DATA_PATH, filename)
        )

        # HDF5-TAR archive conversion to xarray
        ##################################
        radar_ds = radar_tar_to_dataset(data_path)

        return radar_ds


