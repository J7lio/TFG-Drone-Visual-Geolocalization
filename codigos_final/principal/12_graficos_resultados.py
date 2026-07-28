"""
12_graficos_resultados.py

Lee resultados_vuelo_completo.csv (de 11_ejecutar_vuelo_completo.py) y
telemetria.csv completo (para dibujar la trayectoria entera, aunque solo
se haya evaluado el matching en los frames > 60m) y genera las gráficas
de resultados en graficos/.

Uso:
    python 12_graficos_resultados.py
"""
import csv
import os

import matplotlib.pyplot as plt
import numpy as np

from geo_utils import meters_per_degree

FLIGHT_DIR = os.path.join("vuelo_20260716_095840")
TELEMETRY_CSV = os.path.join(FLIGHT_DIR, "telemetria.csv")
RESULTADOS_CSV = "resultados_vuelo_completo.csv"
OUT_DIR = "../graficos"

# Estilo compartido: marcas finas, ejes recesivos, sin chartjunk.
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#888888",
    "axes.labelcolor": "#333333",
    "xtick.color": "#555555",
    "ytick.color": "#555555",
    "grid.color": "#dddddd",
    "grid.linewidth": 0.6,
    "text.color": "#222222",
})

COLOR_LINEA = "#2a78d6"     # azul (identidad única -> sin leyenda de color)
COLOR_ERROR = "#e34948"     # rojo/coral para error (semántica: "coste")
COLOR_FALLO = "#b0b0b0"     # gris para el outlier/fallo

# Colores categóricos fijos para las dos fases del matching
COLOR_RETRIEVAL = "#2a78d6"  # azul: retrieval global (descriptor + ranking)
COLOR_LOFTR = "#eda100"      # ámbar: matching local LoFTR + MAGSAC++


def load_telemetry():
    with open(TELEMETRY_CSV, newline="") as f:
        return list(csv.DictReader(f))


def load_resultados():
    with open(RESULTADOS_CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["alt"] = float(r["alt"])
        r["lat_real"] = float(r["lat_real"])
        r["lon_real"] = float(r["lon_real"])
        r["lat_gt"] = float(r["lat_gt"])
        r["lon_gt"] = float(r["lon_gt"])
        r["tiempo_s"] = float(r["tiempo_s"])
        r["tiempo_retrieval_s"] = float(r["tiempo_retrieval_s"])
        r["tiempo_loftr_s"] = float(r["tiempo_loftr_s"])
        r["n_candidatos_probados"] = int(r["n_candidatos_probados"])
        r["inliers"] = int(r["inliers"])
        r["lat_est"] = float(r["lat_est"]) if r["lat_est"] != "" else None
        r["lon_est"] = float(r["lon_est"]) if r["lon_est"] != "" else None
        r["error_bruto_m"] = float(r["error_bruto_m"]) if r["error_bruto_m"] != "" else None
        r["error_m"] = float(r["error_m"]) if r["error_m"] != "" else None
    return rows


def grafico_trayectoria(telemetria, resultados, out_path):
    lats = np.array([float(r["Latitud"]) for r in telemetria])
    lons = np.array([float(r["Longitud"]) for r in telemetria])
    alts = np.array([float(r["Alt_Relativa(m)"]) for r in telemetria])

    # Convierte lat/lon a metros locales relativos al despegue: más
    # legible que grados con muchos decimales sobre un rango pequeño.
    lat0, lon0 = lats[0], lons[0]
    m_per_deg_lat, m_per_deg_lon = meters_per_degree(lat0)
    xs = (lons - lon0) * m_per_deg_lon
    ys = (lats - lat0) * m_per_deg_lat

    lats_q = np.array([r["lat_real"] for r in resultados])
    lons_q = np.array([r["lon_real"] for r in resultados])
    xs_q = (lons_q - lon0) * m_per_deg_lon
    ys_q = (lats_q - lat0) * m_per_deg_lat

    fig, ax = plt.subplots(figsize=(7, 6))

    # Línea de fondo para dar continuidad al recorrido, puntos coloreados
    # por altitud encima (viridis: perceptualmente uniforme).
    ax.plot(xs, ys, color="#cccccc", linewidth=1.0, zorder=1)
    sc = ax.scatter(xs, ys, c=alts, cmap="viridis", s=14, zorder=2,
                     edgecolors="none")

    # Anillo en los frames usados como query (>60m), para distinguir
    # crucero (evaluado) de despegue/aterrizaje (no evaluado).
    ax.scatter(xs_q, ys_q, facecolors="none", edgecolors="#222222",
               linewidths=0.4, s=28, zorder=3, label="Frames evaluados (>60m)")

    ax.scatter([xs[0]], [ys[0]], marker="^", color="#1baf7a", s=90,
               zorder=4, label="Despegue")
    ax.scatter([xs[-1]], [ys[-1]], marker="s", color="#e34948", s=70,
               zorder=4, label="Aterrizaje")

    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label("Altitud relativa (m)")

    ax.set_xlabel("Este (m, relativo al despegue)")
    ax.set_ylabel("Norte (m, relativo al despegue)")
    ax.set_title("Trayectoria del vuelo, coloreada por altitud")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, linewidth=0.5)
    ax.legend(loc="best", frameon=False, fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Guardado: {out_path}")


def grafico_trayectoria_error(telemetria, resultados, out_path, error_max_m=100.0, alt_min=None, alt_max=None, subtitulo=None):
    """Para cada query evaluada, dibuja sus tres puntos (GPS crudo,
    corregido por pitch/roll, estimado por el pipeline), enlazados solo
    dentro de cada frame -- no se conectan entre frames consecutivos
    porque el pitch/roll oscila mucho de uno a otro (dron sin gimbal) y
    generaría un zigzag sin significado real.

    alt_min/alt_max filtran las queries dibujadas por altitud, para
    separar los dos tramos de vuelo (~80m y ~120m) en gráficas distintas.
    La línea de fondo (trayectoria GPS completa) se mantiene siempre
    entera como contexto."""
    if alt_min is not None or alt_max is not None:
        resultados = [
            r for r in resultados
            if (alt_min is None or r["alt"] >= alt_min) and (alt_max is None or r["alt"] < alt_max)
        ]

    lats = np.array([float(r["Latitud"]) for r in telemetria])
    lons = np.array([float(r["Longitud"]) for r in telemetria])

    lat0, lon0 = lats[0], lons[0]
    m_per_deg_lat, m_per_deg_lon = meters_per_degree(lat0)
    xs = (lons - lon0) * m_per_deg_lon
    ys = (lats - lat0) * m_per_deg_lat

    # Colores categóricos fijos, uno por identidad (nunca por magnitud)
    COL_CSV = "#555555"       # gris oscuro: posición GPS cruda
    COL_GT = "#2a78d6"        # azul: corregida por pitch/roll (nadir)
    COL_EST = "#e34948"       # rojo: estimada por el pipeline

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    ax.plot(xs, ys, color="#dddddd", linewidth=1.0, zorder=1, label="Trayectoria (GPS)")

    n_fuera_escala = 0
    etiquetas_puestas = set()

    def scatter_una_vez(x, y, color, label, **kwargs):
        lbl = label if label not in etiquetas_puestas else None
        etiquetas_puestas.add(label)
        ax.scatter([x], [y], color=color, label=lbl, **kwargs)

    for r in resultados:
        if r["error_m"] is None:
            continue
        cx = (r["lon_real"] - lon0) * m_per_deg_lon
        cy = (r["lat_real"] - lat0) * m_per_deg_lat
        gx = (r["lon_gt"] - lon0) * m_per_deg_lon
        gy = (r["lat_gt"] - lat0) * m_per_deg_lat

        scatter_una_vez(cx, cy, COL_CSV, "GPS crudo (csv)", s=14, zorder=3, edgecolors="none")

        if r["error_m"] > error_max_m:
            scatter_una_vez(gx, gy, "black", "Fallo (fuera de escala)", marker="x", s=45, zorder=4)
            n_fuera_escala += 1
            continue

        ex = (r["lon_est"] - lon0) * m_per_deg_lon
        ey = (r["lat_est"] - lat0) * m_per_deg_lat

        # Enlaza SOLO el trío de este frame: csv -> corregido -> estimado
        ax.plot([cx, gx, ex], [cy, gy, ey], color="#bbbbbb", linewidth=0.6, zorder=2)
        scatter_una_vez(gx, gy, COL_GT, "Corregido (nadir pitch/roll)", s=14, zorder=4, edgecolors="none")
        scatter_una_vez(ex, ey, COL_EST, "Estimado (pipeline)", s=14, zorder=4, edgecolors="none")

    ax.set_xlabel("Este (m, relativo al despegue)")
    ax.set_ylabel("Norte (m, relativo al despegue)")
    titulo = "Posición GPS, corregida por pitch/roll y estimada, por frame"
    if subtitulo:
        titulo += f"\n{subtitulo} (n={len(resultados)})"
    if n_fuera_escala:
        titulo += f"\n({n_fuera_escala} fallo(s) >{error_max_m:.0f}m marcado(s) con X)"
    ax.set_title(titulo, fontsize=10)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, linewidth=0.5)
    ax.legend(loc="best", frameon=False, fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Guardado: {out_path}")


def grafico_error_distribucion(resultados, out_path, corte_m=40.0):
    """Compara el error bruto (contra el GPS crudo) frente al corregido
    (contra el punto de terreno real, vía nadir_offset_m)."""
    bruto = np.array([r["error_bruto_m"] for r in resultados if r["error_bruto_m"] is not None])
    corregido = np.array([r["error_m"] for r in resultados if r["error_m"] is not None])

    bins = np.linspace(0, corte_m, 21)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    # Recorta la vista a corte_m para que los fallos catastróficos no
    # aplasten la distribución; se reportan aparte, sin ocultarlos.
    ax.hist(bruto[bruto <= corte_m], bins=bins, color=COLOR_ERROR, alpha=0.55,
            edgecolor="white", linewidth=0.5, label=f"Bruto (vs GPS) — mediana {np.median(bruto):.1f}m")
    ax.hist(corregido[corregido <= corte_m], bins=bins, color=COLOR_LINEA, alpha=0.55,
            edgecolor="white", linewidth=0.5, label=f"Corregido (nadir_offset_m) — mediana {np.median(corregido):.1f}m")

    ax.axvline(np.median(bruto), color=COLOR_ERROR, linewidth=1.2, linestyle="--")
    ax.axvline(np.median(corregido), color=COLOR_LINEA, linewidth=1.2, linestyle="--")

    n_fallos_bruto = (bruto > corte_m).sum()
    n_fallos_corr = (corregido > corte_m).sum()
    ax.set_xlim(0, corte_m)
    ax.set_xlabel("Error de localización (m)")
    ax.set_ylabel("Nº de frames")
    titulo = f"Error de localización: bruto vs. corregido por pitch/roll (n={len(corregido)})"
    if n_fallos_bruto or n_fallos_corr:
        titulo += f"\n(no mostrados >{corte_m:.0f}m: {n_fallos_bruto} bruto, {n_fallos_corr} corregido)"
    ax.set_title(titulo, fontsize=10)
    ax.grid(True, axis="y", linewidth=0.5)
    ax.legend(loc="upper right", frameon=False, fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Guardado: {out_path}")


def grafico_tiempo_por_query(resultados, out_path):
    """Excluye la 1ª query: ese tiempo es carga de modelos en frío, no
    matching, y aplastaría la escala del resto."""
    tiempos_todas = np.array([r["tiempo_s"] for r in resultados])
    tiempos = tiempos_todas[1:]
    x = np.arange(2, len(resultados) + 1)  # numeración real de query, empezando en la 2ª

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x, tiempos, color=COLOR_LINEA, linewidth=1.2, marker="o", markersize=3)

    ax.set_xlabel("Query (orden cronológico, sin la 1ª -- carga de modelos)")
    ax.set_ylabel("Tiempo por query (s)")
    ax.set_title(f"Tiempo de matching por query (media={tiempos.mean():.2f}s, total={tiempos.sum():.1f}s)",
                 fontsize=10)
    ax.grid(True, linewidth=0.5)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Guardado: {out_path}")


def grafico_tiempo_desglose(resultados, out_path):
    """Desglosa tiempo_s en sus dos fases (barras apiladas): retrieval
    global (VLAD+DINOv3-SAT) vs. matching local (LoFTR+MAGSAC++). Excluye
    la 1ª query (carga de modelos en frío)."""
    ret = np.array([r["tiempo_retrieval_s"] for r in resultados])[1:]
    loftr = np.array([r["tiempo_loftr_s"] for r in resultados])[1:]
    x = np.arange(2, len(resultados) + 1)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x, ret, color=COLOR_RETRIEVAL, width=0.85, edgecolor="white",
           linewidth=0.3, label="Retrieval global (VLAD+DINOv3-SAT)")
    ax.bar(x, loftr, bottom=ret, color=COLOR_LOFTR, width=0.85, edgecolor="white",
           linewidth=0.3, label="Matching local (LoFTR+MAGSAC++)")

    ax.set_xlabel("Query (orden cronológico, sin la 1ª -- carga de modelos)")
    ax.set_ylabel("Tiempo (s)")
    ax.set_title(f"Desglose del tiempo por query: retrieval={ret.mean():.3f}s de media "
                 f"({ret.sum()/(ret.sum()+loftr.sum())*100:.0f}%) vs. "
                 f"LoFTR={loftr.mean():.3f}s de media ({loftr.sum()/(ret.sum()+loftr.sum())*100:.0f}%)",
                 fontsize=9.5)
    ax.grid(True, axis="y", linewidth=0.5)
    ax.legend(loc="upper right", frameon=False, fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Guardado: {out_path}")


def grafico_tiempo_vs_candidatos(resultados, out_path):
    candidatos = np.array([r["n_candidatos_probados"] for r in resultados])
    tiempos = np.array([r["tiempo_s"] for r in resultados])

    # Descarta la query de calentamiento (carga de modelos en frío):
    # tiempo anómalamente alto frente a la mediana del resto.
    idx_calentamiento = int(np.argmax(tiempos))
    es_calentamiento = np.zeros(len(tiempos), dtype=bool)
    if tiempos[idx_calentamiento] > 3 * np.median(tiempos):
        es_calentamiento[idx_calentamiento] = True
    candidatos, tiempos = candidatos[~es_calentamiento], tiempos[~es_calentamiento]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(candidatos, tiempos, color=COLOR_LINEA, s=22, alpha=0.8,
               edgecolors="none", label="Queries")

    if len(np.unique(candidatos)) > 1:
        coef = np.polyfit(candidatos, tiempos, 1)
        xs = np.linspace(candidatos.min(), candidatos.max(), 50)
        ax.plot(xs, np.polyval(coef, xs), color="#222222", linewidth=1.0, linestyle="--")
        ax.text(0.05, 0.95, f"~{coef[0]*1000:.0f} ms/candidato", transform=ax.transAxes,
                fontsize=9, va="top", color="#222222")
    else:
        ax.text(0.05, 0.95, f"~{tiempos.mean()*1000:.0f} ms/query (casi todas con 1 candidato)",
                transform=ax.transAxes, fontsize=9, va="top", color="#222222")

    ax.set_xlabel("Candidatos probados hasta el early-exit")
    ax.set_ylabel("Tiempo de la query (s)")
    ax.set_title("Coste por query vs. nº de candidatos LoFTR probados\n"
                  "(excluida 1ª query -- carga de modelos)")
    ax.grid(True, linewidth=0.5)
    ax.legend(loc="lower right", frameon=False, fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Guardado: {out_path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    telemetria = load_telemetry()
    resultados = load_resultados()

    grafico_trayectoria(telemetria, resultados, os.path.join(OUT_DIR, "trayectoria_altitud.png"))
    # Umbral 100m: separa los dos tramos de altitud del vuelo (~80m y ~120m).
    grafico_trayectoria_error(telemetria, resultados, os.path.join(OUT_DIR, "trayectoria_error_80m.png"),
                               alt_max=100.0, subtitulo="Queries a ~80m de altitud (<100m)")
    grafico_trayectoria_error(telemetria, resultados, os.path.join(OUT_DIR, "trayectoria_error_120m.png"),
                               alt_min=100.0, subtitulo="Queries a ~120m de altitud (>=100m)")
    grafico_error_distribucion(resultados, os.path.join(OUT_DIR, "error_localizacion.png"))
    grafico_tiempo_por_query(resultados, os.path.join(OUT_DIR, "tiempo_por_query.png"))
    grafico_tiempo_desglose(resultados, os.path.join(OUT_DIR, "tiempo_desglose.png"))
    grafico_tiempo_vs_candidatos(resultados, os.path.join(OUT_DIR, "tiempo_vs_candidatos.png"))

    errores = [r["error_m"] for r in resultados if r["error_m"] is not None]
    tiempos = [r["tiempo_s"] for r in resultados]
    print(f"\nResumen: {len(resultados)} queries | "
          f"error mediana={np.median(errores):.1f}m media={np.mean(errores):.1f}m | "
          f"tiempo medio={np.mean(tiempos):.2f}s total={np.sum(tiempos):.1f}s")


if __name__ == "__main__":
    main()
