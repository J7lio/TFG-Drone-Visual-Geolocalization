"""
01_download_basemap.py

Descarga un mosaico satelital (ESRI World Imagery) alrededor de unas
coordenadas centrales y lo exporta como GeoTIFF georreferenciado
(basemap.tif), el mapa de referencia del pipeline.

Pensado para zonas pequeñas (cientos de metros a pocos km). Para áreas
mucho mayores, usar una herramienta de descarga de teselas por lotes.

Requisitos:
    pip install contextily rasterio pyproj numpy

Uso:
    python 01_download_basemap.py
"""
import math

import contextily as ctx
import numpy as np
import rasterio
from rasterio.transform import from_bounds

# --- Centro de la zona a descargar ---
# Sustituir por las coordenadas reales de la zona aprox de vuelo antes de ejecutar.
LAT_CENTER = 0.0
LON_CENTER = 0.0

# --- Radio de la zona a descargar en metros a cada lado del centro ---
# 1500 m = área de ~3x3 km, radio usado en producción.
RADIO_M = 1500

# --- Nivel de zoom (18-19 recomendado) ---
ZOOM = 18

OUT_PATH = "basemap.tif"


def meters_per_degree_local(lat_deg):
    lat_rad = math.radians(lat_deg)
    m_per_deg_lat = 111132.92 - 559.82 * math.cos(2 * lat_rad) + 1.175 * math.cos(4 * lat_rad)
    m_per_deg_lon = 111412.84 * math.cos(lat_rad) - 93.5 * math.cos(3 * lat_rad)
    return m_per_deg_lat, m_per_deg_lon


def latlon_bounds(lat, lon, radio_m):
    m_per_deg_lat, m_per_deg_lon = meters_per_degree_local(lat)
    dlat = radio_m / m_per_deg_lat
    dlon = radio_m / m_per_deg_lon
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat  # W, S, E, N


def main():
    w, s, e, n = latlon_bounds(LAT_CENTER, LON_CENTER, RADIO_M)
    print(f"BBox solicitado (WGS84): W={w:.6f} S={s:.6f} E={e:.6f} N={n:.6f}")
    print(f"Descargando teselas ESRI World Imagery (zoom={ZOOM})...")

    # ll=True: bounds en lat/lon. Descarga y reproyecta a Web Mercator (EPSG:3857).
    img, ext = ctx.bounds2img(
        w, s, e, n,
        zoom=ZOOM,
        source=ctx.providers.Esri.WorldImagery,
        ll=True,
    )

    xmin, xmax, ymin, ymax = ext
    height, width = img.shape[0], img.shape[1]
    transform = from_bounds(xmin, ymin, xmax, ymax, width, height)

    # Eliminar el alpha de la imagen
    img_rgb = img[:, :, :3]

    with rasterio.open(
        OUT_PATH, "w",
        driver="GTiff",
        height=height, width=width,
        count=3, dtype=img_rgb.dtype,
        crs="EPSG:3857",
        transform=transform,
    ) as dst:
        for i in range(3):
            dst.write(img_rgb[:, :, i], i + 1)

    print(f"Mosaico guardado en {OUT_PATH} ({width}x{height} px, CRS=EPSG:3857)")


if __name__ == "__main__":
    main()
