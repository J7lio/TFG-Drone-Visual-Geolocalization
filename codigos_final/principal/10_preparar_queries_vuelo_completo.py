"""
10_preparar_queries_vuelo_completo.py

Normaliza (rota a norte + recorta por altitud) todos los frames de un
vuelo con altitud > ALT_MIN_M, descartando despegue/aterrizaje.

Uso:
    python 10_preparar_queries_vuelo_completo.py
"""
import csv
import os

import cv2

GALLERY_REF_ALT_M = 80.0  # debe coincidir con REF_ALT_M de 02_tile_basemap_gallery.py
ALT_MIN_M = 60.0  # descarta despegue/aterrizaje; a 60m ya se está en crucero

FLIGHT_DIR = os.path.join("vuelo_20260716_095840")
TELEMETRY_CSV = os.path.join(FLIGHT_DIR, "telemetria.csv")
OUT_DIR = "queries_normalizadas_completo"
QUERIES_CSV = "queries_index_completo.csv"

ROTATE_SIGN = -1  # mismo signo verificado empíricamente en 00_preparar_queries.py


def rotar_a_norte(img, rumbo_deg):
    h, w = img.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, ROTATE_SIGN * rumbo_deg, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))


def recortar_por_altitud(img, alt_m, ref_alt_m=GALLERY_REF_ALT_M):
    if alt_m <= ref_alt_m:
        return img
    factor = ref_alt_m / alt_m
    h, w = img.shape[:2]
    new_w, new_h = int(w * factor), int(h * factor)
    x0 = (w - new_w) // 2
    y0 = (h - new_h) // 2
    return img[y0:y0 + new_h, x0:x0 + new_w]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(TELEMETRY_CSV, newline="") as f:
        telemetria = list(csv.DictReader(f))

    rows_out = []
    n_descartados = 0
    for row in telemetria:
        alt = float(row["Alt_Relativa(m)"])
        if alt < ALT_MIN_M:
            n_descartados += 1
            continue

        fname = row["Archivo_Frame"]
        raw_path = os.path.join(FLIGHT_DIR, fname)
        img = cv2.imread(raw_path, cv2.IMREAD_COLOR)
        if img is None:
            print(f"AVISO: no se pudo leer {raw_path}, se salta")
            continue

        rumbo = float(row["Rumbo_Norte(deg)"])
        img_final = recortar_por_altitud(rotar_a_norte(img, rumbo), alt)

        out_path = os.path.join(OUT_DIR, fname)
        cv2.imwrite(out_path, img_final)

        rows_out.append({
            "file": out_path.replace("\\", "/"),
            "lat": row["Latitud"],
            "lon": row["Longitud"],
            "alt_original": alt,
            "rumbo_original": rumbo,
            "timestamp": row["Timestamp"],
        })

    with open(QUERIES_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "lat", "lon", "alt_original", "rumbo_original", "timestamp"])
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"{len(rows_out)} queries normalizadas en '{OUT_DIR}/' (descartados {n_descartados} "
          f"frames con alt < {ALT_MIN_M}m -- despegue/aterrizaje)")
    print(f"Índice: '{QUERIES_CSV}'")


if __name__ == "__main__":
    main()
