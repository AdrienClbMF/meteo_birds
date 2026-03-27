
import os
from pathlib import Path
from datetime import timezone
import subprocess

import numpy as np

from scipy.interpolate import splprep, splev
from shapely import LineString

from .bird_tracks import load_birds_df
from .plots import plot_radar_basicdataset
from .formatting import extract_radar_da
from .diagnostics import cone_geometry
from .settings import FIGURES_PATH




def run_ffmpeg(cmd: list[str], workdir: Path):
    subprocess.run(
        cmd,
        cwd=workdir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def make_animation(image_dir: Path, bird_id:int):
    image_dir = image_dir.resolve()

    # 1️⃣ Palette
    run_ffmpeg(
        [
            "ffmpeg",
            "-framerate", "1",
            "-pattern_type", "glob",
            "-i", "*.jpg",
            "-vf", "palettegen",
            "palette.png",
        ],
        workdir=image_dir,
    )

    # 2️⃣ GIF
    run_ffmpeg(
        [
            "ffmpeg",
            "-framerate", "1",
            "-pattern_type", "glob",
            "-i", "*.jpg",
            "-i", "palette.png",
            "-filter_complex",
            "scale=640:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a",
            "-loop", "0",
            f"radar_anim_{bird_id}.gif",
        ],
        workdir=image_dir,
    )

    # 3️⃣ MP4 (WhatsApp)
    run_ffmpeg(
        [
            "ffmpeg",
            "-framerate", "2",
            "-pattern_type", "glob",
            "-i", "*.jpg",
            "-vf", "scale=640:-2:flags=lanczos",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "25",
            f"radar_whatsapp_{bird_id}.mp4",
        ],
        workdir=image_dir,
    )



def generate_bird_animation(
        bird_id : int,
        output_dir: Path = None) :
    specific_bird_df = load_birds_df(bird_id=bird_id)

    if output_dir is None :
        output_dir = FIGURES_PATH

    output_dir = output_dir / f"anim_track_{bird_id}"
    os.makedirs(output_dir, exist_ok=True)

    for idx, row in specific_bird_df.iterrows() :
        radar_ds = extract_radar_da(row.RADAR_hdf5_dat.replace(tzinfo=timezone.utc))
        if radar_ds :
            lat0, lon0, heading, hdf5_dat = row.Latitude, row.Longitude, row.direction_deg, row.RADAR_hdf5_dat
            O, R = 45, 50
            cone_poly, axis_line = cone_geometry(lat0, lon0, heading, O, R)

            leeway = 3.5
            bbox = (lon0-leeway, lon0+leeway, lat0-leeway, lat0+leeway) #(-12,5,40,47)
        
            draw_poly = [cone_poly, 
                        axis_line.buffer(.01, cap_style=2)]

            # Extraire les 10 derniers points disponibles
            last10 = specific_bird_df.loc[
                specific_bird_df.UTC_datetime <= row.UTC_datetime
            ].tail(10)[['Latitude', 'Longitude']]

            coords = np.array(list(zip(last10['Longitude'], last10['Latitude'])))


            if coords.shape[0] < 2:
                # Aucun point disponible : rien à faire
                pass
            elif coords.shape[0] <= 5:
                # Trop peu de points : on trace la LineString directe
                ls = LineString(coords)
                draw_poly.append(ls.buffer(0.01, cap_style=2))  # cap_style=2 → extrémités plates
            else:
                # Spline lissée pour plus de 5 points
                k = min(3, len(coords)-1)  # k doit être < nombre de points
                tck, u = splprep([coords[:,0], coords[:,1]], s=0, k=k)
                u_new = np.linspace(0, 1, 100)  # points pour la courbe lisse
                lon_smooth, lat_smooth = splev(u_new, tck)
                smoothed_linestring = LineString(zip(lon_smooth, lat_smooth))
                draw_poly.append(smoothed_linestring.buffer(0.01, cap_style=2))

            bird_altitude = row.Altitude_m
            if bird_altitude <= 0 :
                bird_altitude = "On Ground"
            else :
                bird_altitude = f"In flight at {bird_altitude}m"
            filename = f"{bird_id}_{row.RADAR_hdf5_dat.isoformat()}_rflc.jpg"
            plot_radar_basicdataset(
                radar_ds, 
                dat = row.RADAR_hdf5_dat, 
                bbox=bbox, 
                factor=3, 
                title = f'Rflc max, bird {bird_id} \n ({bird_altitude}) \n',
                add_poly=draw_poly,
                output_path= output_dir / filename
                )
    make_animation(output_dir)