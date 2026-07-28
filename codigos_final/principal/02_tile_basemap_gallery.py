"""
02_tile_basemap_gallery.py

Genera la "gallery" de parches satelitales a partir de basemap.tif,
recortando en una rejilla con solapamiento. Guarda cada parche como PNG
junto con un CSV que registra su coordenada central (lat/lon) y su
origen en píxeles del mosaico original.

Esta gallery es contra la que luego se comparará cada frame de dron
(ya normalizado por 00_preparar_queries.py) en la fase de recuperación
global (script 03).

Requisitos:
    pip install rasterio pyproj pillow numpy

Uso:
    python 02_tile_basemap_gallery.py
"""
import csv
import os

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer

from geo_utils import px2geo, ground_footprint_m, web_mercator_scale

BASEMAP_PATH = "basemap.tif"
OUT_DIR = "gallery_tiles"
CSV_PATH = "gallery_index.csv"

# Altitud de referencia para el tamaño de parche. Debe coincidir con
# GALLERY_REF_ALT_M en 00_preparar_queries.py.
REF_ALT_M = 80.0

# Un frame PNG real del vuelo, para leer el ancho x alto en píxeles.
# Se usa para igualar el ratio de la imagen del parche al de la imagen real.
REF_FRAME_PATH = "vuelo_20260716_095840/frame_20260716_095953_885.png"

OVERLAP = 0.3  # solapamiento entre parches contiguos
MIN_STD = 2.0  # descarta parches casi uniformes (posibles bordes sin datos)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with rasterio.open(BASEMAP_PATH) as src:
        gt = src.transform
        crs = src.crs
        width, height = src.width, src.height

        transformer_back = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

        # Factor de escala Web Mercator en la latitud del mosaico: convierte
        # metros reales de terreno a "metros proyectados" del raster.
        X_geo_c, Y_geo_c = px2geo(width / 2, height / 2, gt)
        _, lat_center = transformer_back.transform(X_geo_c, Y_geo_c)
        mercator_scale = web_mercator_scale(lat_center)

        with Image.open(REF_FRAME_PATH) as ref_img:
            frame_w, frame_h = ref_img.size

        width_m, height_m = ground_footprint_m(REF_ALT_M, aspect_ratio=(frame_w, frame_h))
        res_x = abs(gt.a)
        res_y = abs(gt.e)
        tile_w_px = max(16, int(width_m * mercator_scale / res_x))
        tile_h_px = max(16, int(height_m * mercator_scale / res_y))
        step_x = max(1, int(tile_w_px * (1 - OVERLAP)))
        step_y = max(1, int(tile_h_px * (1 - OVERLAP)))

        print(f"Mosaico: {width}x{height} px")
        print(f"Frame de referencia: {REF_FRAME_PATH} ({frame_w}x{frame_h}, "
              f"aspecto {frame_w / frame_h:.3f})")
        print(f"Latitud centro: {lat_center:.5f}° | factor Web Mercator: {mercator_scale:.4f}")
        print(f"Tamaño de parche: {tile_w_px}x{tile_h_px} px | paso: {step_x}x{step_y} px")

        rows = []
        tile_id = 0
        for y0 in range(0, max(1, height - tile_h_px), step_y):
            for x0 in range(0, max(1, width - tile_w_px), step_x):
                window = ((y0, y0 + tile_h_px), (x0, x0 + tile_w_px))
                patch = src.read([1, 2, 3], window=window)
                patch = np.moveaxis(patch, 0, -1)

                if patch.size == 0 or patch.std() < MIN_STD:
                    continue

                cx, cy = x0 + tile_w_px / 2, y0 + tile_h_px / 2
                X_geo, Y_geo = px2geo(cx, cy, gt)
                lon_c, lat_c = transformer_back.transform(X_geo, Y_geo)

                fname = f"tile_{tile_id:05d}.png"
                Image.fromarray(patch).save(os.path.join(OUT_DIR, fname))

                rows.append({
                    "tile_id": tile_id,
                    "file": fname,
                    "x0": x0, "y0": y0,
                    "lat": lat_c, "lon": lon_c,
                })
                tile_id += 1

        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["tile_id", "file", "x0", "y0", "lat", "lon"])
            writer.writeheader()
            writer.writerows(rows)

        print(f"Generados {tile_id} parches de gallery en '{OUT_DIR}/', índice en '{CSV_PATH}'")
        if tile_id == 0:
            print("AVISO: 0 parches generados. Amplía RADIO_M en 01_download_basemap.py "
                  "o baja MIN_STD si la zona es muy homogénea.")


if __name__ == "__main__":
    main()
