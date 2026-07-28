"""
11_ejecutar_vuelo_completo.py

Corre el pipeline completo (retrieval VLAD+DINOv3-SAT -> LoFTR+MAGSAC++,
con early-exit + fp16 + MAX_SIDE=384) sobre todas las queries de
10_preparar_queries_vuelo_completo.py y vuelca los resultados a un CSV.

Separado de 12_graficos_resultados.py para no re-correr LoFTR cada vez
que se ajusta una gráfica.

Uso:
    python 11_ejecutar_vuelo_completo.py
"""
import csv
import time

import cv2
import kornia.feature as KF
import numpy as np
import rasterio
import torch
from pyproj import Transformer

from geo_utils import px2geo, haversine_m, nadir_offset_m, meters_per_degree
from descriptor_produccion import get_gallery_embeddings, get_descriptor  # VLAD+DINOv3-SAT

FLIGHT_DIR = "vuelo_20260716_095840"
TELEMETRY_CSV = f"{FLIGHT_DIR}/telemetria.csv"
GALLERY_DIR = "gallery_tiles"
GALLERY_CSV = "gallery_index.csv"
QUERIES_CSV = "queries_index_completo.csv"
BASEMAP_PATH = "basemap.tif"
RESULTADOS_CSV = "resultados_vuelo_completo.csv"

TOP_K_GLOBAL = 20  # candidatos probados como máximo por query (early-exit corta antes)
MAX_SIDE = 384
USE_FP16 = torch.cuda.is_available()
CONF_THRESHOLD = 0.3
RANSAC_THRESHOLD_PX = 5.0
EARLY_EXIT_INLIERS = 100

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using {DEVICE} device.")

_loftr = None


def load_loftr():
    global _loftr
    if _loftr is None:
        print(f"Cargando LoFTR{' en FP16' if USE_FP16 else ''}...")
        _loftr = KF.LoFTR(pretrained="outdoor").to(DEVICE).eval()
        if USE_FP16:
            _loftr = _loftr.half()
    return _loftr


def load_gallery_index():
    with open(GALLERY_CSV, newline="") as f:
        return list(csv.DictReader(f))


def load_queries():
    with open(QUERIES_CSV, newline="") as f:
        return list(csv.DictReader(f))


def load_gray_tensor(path, max_side=MAX_SIDE):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(img, (new_w, new_h))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    dtype = torch.float16 if USE_FP16 else torch.float32
    tensor = torch.from_numpy(gray).to(dtype)[None, None] / 255.0
    return tensor.to(DEVICE), scale, (w, h)


@torch.no_grad()
def match_pair(drone_path, tile_path):
    loftr = load_loftr()
    t0, scale0, size0 = load_gray_tensor(drone_path)
    t1, scale1, size1 = load_gray_tensor(tile_path)

    out = loftr({"image0": t0, "image1": t1})
    mkpts0 = out["keypoints0"].float().cpu().numpy()
    mkpts1 = out["keypoints1"].float().cpu().numpy()
    conf = out["confidence"].float().cpu().numpy()

    keep = conf > CONF_THRESHOLD
    mkpts0, mkpts1 = mkpts0[keep], mkpts1[keep]
    if len(mkpts0) < 4:
        return None

    mkpts0_full = mkpts0 / scale0
    mkpts1_full = mkpts1 / scale1

    H, mask = cv2.findHomography(mkpts0_full, mkpts1_full, cv2.USAC_MAGSAC, RANSAC_THRESHOLD_PX)
    if H is None:
        return None

    return {"H": H, "inliers": int(mask.sum()), "n_matches": len(mkpts0), "drone_size": size0}


def global_retrieval_topk(query_path, gallery_rows, gallery_matrix, k=TOP_K_GLOBAL):
    q_desc = get_descriptor(query_path)
    sims = gallery_matrix @ q_desc
    top_idx = np.argsort(-sims)[:k]
    return top_idx, sims


def load_telemetria_por_frame():
    with open(TELEMETRY_CSV, newline="") as f:
        return {r["Archivo_Frame"]: r for r in csv.DictReader(f)}


def punto_verdad_terreno(lat, lon, pitch_deg, roll_deg, rumbo_deg, alt_m):
    """GPS/IMU -> punto de terreno real que mira el centro de la imagen
    (ver nadir_offset_m en geo_utils.py)."""
    north, east = nadir_offset_m(pitch_deg, roll_deg, rumbo_deg, alt_m)
    m_lat, m_lon = meters_per_degree(lat)
    return lat + north / m_lat, lon + east / m_lon


def main():
    gallery_rows = load_gallery_index()
    queries = load_queries()
    if not queries:
        print("queries_index_completo.csv vacío. Corre antes 10_preparar_queries_vuelo_completo.py")
        return

    telemetria = load_telemetria_por_frame()
    gallery_matrix = get_gallery_embeddings(gallery_rows, GALLERY_DIR)

    with rasterio.open(BASEMAP_PATH) as src:
        gt = src.transform
        crs = src.crs
    transformer_back = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

    resultados = []
    t_inicio_total = time.time()

    for i, q in enumerate(queries):
        lat_real, lon_real = float(q["lat"]), float(q["lon"])
        fname = q["file"].split("/")[-1]
        t_row = telemetria[fname]
        pitch, roll = float(t_row["Pitch(deg)"]), float(t_row["Roll(deg)"])
        lat_gt, lon_gt = punto_verdad_terreno(
            lat_real, lon_real, pitch, roll, float(q["rumbo_original"]), float(q["alt_original"]))
        t0 = time.time()

        t_ret0 = time.time()
        top_idx, sims = global_retrieval_topk(q["file"], gallery_rows, gallery_matrix)
        tiempo_retrieval_s = time.time() - t_ret0

        best = None
        n_probados = 0
        tiempo_loftr_s = 0.0
        for idx in top_idx:
            row = gallery_rows[idx]
            tile_path = f"{GALLERY_DIR}/{row['file']}"
            t_loftr0 = time.time()
            result = match_pair(q["file"], tile_path)
            tiempo_loftr_s += time.time() - t_loftr0
            n_probados += 1
            if result is None:
                continue
            if best is None or result["inliers"] > best["inliers"]:
                best = {**result, "row": row}
            if best is not None and best["inliers"] >= EARLY_EXIT_INLIERS:
                break

        tiempo_s = time.time() - t0

        if best is None:
            resultados.append({
                "file": q["file"], "timestamp": q["timestamp"],
                "lat_real": lat_real, "lon_real": lon_real,
                "lat_gt": lat_gt, "lon_gt": lon_gt,
                "pitch": pitch, "roll": roll,
                "alt": q["alt_original"], "rumbo": q["rumbo_original"],
                "lat_est": "", "lon_est": "", "error_bruto_m": "", "error_m": "",
                "inliers": 0, "n_candidatos_probados": n_probados,
                "tile_ganador": "", "tiempo_s": round(tiempo_s, 3),
                "tiempo_retrieval_s": round(tiempo_retrieval_s, 4),
                "tiempo_loftr_s": round(tiempo_loftr_s, 4),
            })
            print(f"[{i+1}/{len(queries)}] {q['file']}: SIN MATCH ({tiempo_s:.2f}s)")
            continue

        w, h = best["drone_size"]
        center_drone = np.float32([[w / 2, h / 2]]).reshape(-1, 1, 2)
        center_tile = cv2.perspectiveTransform(center_drone, best["H"])
        x0, y0 = int(best["row"]["x0"]), int(best["row"]["y0"])
        px_full = center_tile[0, 0, 0] + x0
        py_full = center_tile[0, 0, 1] + y0
        X_geo, Y_geo = px2geo(px_full, py_full, gt)
        lon_est, lat_est = transformer_back.transform(X_geo, Y_geo)
        # error_bruto_m: contra la posición GPS cruda.
        # error_m: contra el punto de terreno corregido (nadir_offset_m).
        error_bruto_m = haversine_m(lat_real, lon_real, lat_est, lon_est)
        error_m = haversine_m(lat_gt, lon_gt, lat_est, lon_est)

        resultados.append({
            "file": q["file"], "timestamp": q["timestamp"],
            "lat_real": lat_real, "lon_real": lon_real,
            "lat_gt": lat_gt, "lon_gt": lon_gt,
            "pitch": pitch, "roll": roll,
            "alt": q["alt_original"], "rumbo": q["rumbo_original"],
            "lat_est": lat_est, "lon_est": lon_est,
            "error_bruto_m": round(error_bruto_m, 2), "error_m": round(error_m, 2),
            "inliers": best["inliers"], "n_candidatos_probados": n_probados,
            "tile_ganador": best["row"]["file"], "tiempo_s": round(tiempo_s, 3),
            "tiempo_retrieval_s": round(tiempo_retrieval_s, 4),
            "tiempo_loftr_s": round(tiempo_loftr_s, 4),
        })
        print(f"[{i+1}/{len(queries)}] {q['file']}: error={error_m:.1f}m (bruto={error_bruto_m:.1f}m) "
              f"inliers={best['inliers']} candidatos={n_probados} ({tiempo_s:.2f}s = "
              f"{tiempo_retrieval_s:.3f}s retrieval + {tiempo_loftr_s:.3f}s LoFTR)")

    elapsed = time.time() - t_inicio_total

    with open(RESULTADOS_CSV, "w", newline="") as f:
        fieldnames = ["file", "timestamp", "lat_real", "lon_real", "lat_gt", "lon_gt",
                      "pitch", "roll", "alt", "rumbo",
                      "lat_est", "lon_est", "error_bruto_m", "error_m", "inliers",
                      "n_candidatos_probados", "tile_ganador", "tiempo_s",
                      "tiempo_retrieval_s", "tiempo_loftr_s"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(resultados)

    n_ok = sum(1 for r in resultados if r["error_m"] != "")
    errores = [r["error_m"] for r in resultados if r["error_m"] != ""]
    errores_bruto = [r["error_bruto_m"] for r in resultados if r["error_bruto_m"] != ""]
    print(f"\n{'-'*60}")
    print(f"{n_ok}/{len(resultados)} queries con match | tiempo total: {elapsed:.1f}s "
          f"({elapsed/len(resultados):.2f}s/query de media)")
    if errores:
        print(f"Error medio corregido (nadir_offset_m): {np.mean(errores):.2f}m  |  "
              f"error medio bruto (vs GPS crudo): {np.mean(errores_bruto):.2f}m")
    print(f"Resultados guardados en '{RESULTADOS_CSV}'")


if __name__ == "__main__":
    main()
