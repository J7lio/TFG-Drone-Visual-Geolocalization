import cv2
import csv
import math
import os
import time
import threading
from datetime import datetime
from pymavlink import mavutil


# ──────────────────────────────────────────────
#  CONFIGURACIÓN
# ──────────────────────────────────────────────
CONEXION_MAVLINK = 'udp:127.0.0.1:14551'
INTERVALO_SEG    = 0.5   # 1 frame cada N segundos
PNG_COMPRESION   = 1     # 0=más rápido, 9=más pequeño. En Pi 3 usar 1 o 2
CAMARA_INDEX     = 0
OUTPUT_DIR       = "vuelos"

# Resoluciones soportadas por la Svpro AR0234, todas a 90fps MJPEG.
# Más resolución = más detalle pero PNGs más lentos de escribir a disco
# (vigilar en hardware modesto tipo Pi 3, si supera INTERVALO_SEG).
#
# Si cambia la resolución, actualizar también aspect_ratio en
# ground_footprint_m() (geo_utils.py) para que coincida.
RESOLUCIONES = {
    "1920x1200": (1920, 1200),  # nativa del sensor, aspecto 8:5 (1.6)
    "1920x1080": (1920, 1080),  # aspecto 16:9 (1.778)
    "1280x960":  (1280, 960),   # aspecto 4:3 (1.333) -- la usada hasta ahora
    "1280x720":  (1280, 720),   # aspecto 16:9 (1.778)
    "960x720":   (960, 720),    # aspecto 4:3 (1.333)
    "800x600":   (800, 600),    # aspecto 4:3 (1.333)
    "640x480":   (640, 480),    # aspecto 4:3 (1.333)
}
RESOLUCION = RESOLUCIONES["1920x1200"]  # nativa del sensor, sin recorte/escalado del ISP


# ──────────────────────────────────────────────
#  ESTADO COMPARTIDO entre el hilo MAVLink y el hilo principal
# ──────────────────────────────────────────────
datos = {
    # Actitud (ATTITUDE)
    'pitch': 0.0,       # Cabeceo en grados
    'roll':  0.0,       # Alabeo en grados
    'yaw':   0.0,       # Guiñada en grados (-180 a +180, relativa al arranque del EKF)
    # Brújula (VFR_HUD)
    'heading': 0,       # Rumbo magnético en grados (0-360, referenciado al Norte)
    # GPS + altitudes (GLOBAL_POSITION_INT)
    'lat':        0.0,  # Latitud decimal
    'lon':        0.0,  # Longitud decimal
    'alt_rel':    0.0,  # Altitud relativa al despegue en metros (barómetro, ±1m)
    'alt_amsl':   0.0,  # Altitud sobre nivel del mar en metros (GPS+baro, ±5-15m)
    # Estado de conexión
    'conectado': False
}
lock = threading.Lock()


# ──────────────────────────────────────────────
#  HILO MAVLINK (corre en segundo plano)
# ──────────────────────────────────────────────
def hilo_mavlink():
    """Escucha MAVLink y actualiza el diccionario 'datos' continuamente."""
    print(f"[MAVLink] Conectando en {CONEXION_MAVLINK}...")
    try:
        master = mavutil.mavlink_connection(CONEXION_MAVLINK)
        master.wait_heartbeat(timeout=10)
        print("[MAVLink] ¡Latido recibido! Telemetría activa.")
        with lock:
            datos['conectado'] = True
    except Exception as e:
        print(f"[MAVLink] Error al conectar: {e}")
        print("[MAVLink] Continuando sin telemetría (todos los valores = 0.0)")
        return

    while True:
        try:
            msg = master.recv_match(
                type=['ATTITUDE', 'GLOBAL_POSITION_INT', 'VFR_HUD'],
                blocking=True,
                timeout=1.0
            )
            if msg is None:
                continue

            tipo = msg.get_type()
            with lock:
                if tipo == 'ATTITUDE':
                    # ArduPilot manda radianes → convertimos a grados
                    datos['pitch'] = math.degrees(msg.pitch)
                    datos['roll']  = math.degrees(msg.roll)
                    datos['yaw']   = math.degrees(msg.yaw)

                elif tipo == 'GLOBAL_POSITION_INT':
                    # Coordenadas vienen × 1e7 → dividimos para decimal estándar
                    datos['lat']      = msg.lat / 1e7
                    datos['lon']      = msg.lon / 1e7
                    # alt viene en mm → metros. Es AMSL (sobre nivel del mar)
                    datos['alt_amsl'] = msg.alt / 1000.0
                    # relative_alt también en mm. Es relativa al punto de despegue
                    datos['alt_rel']  = msg.relative_alt / 1000.0

                elif tipo == 'VFR_HUD':
                    # Rumbo magnético 0-360° referenciado al Norte. Ya viene en grados enteros.
                    # Más fiable que el yaw de ATTITUDE para saber a dónde apunta el dron.
                    datos['heading'] = msg.heading

        except Exception:
            pass


# ──────────────────────────────────────────────
#  ESTADO COMPARTIDO del hilo de cámara
# ──────────────────────────────────────────────
frame_state = {
    'frame': None,       # último frame leído de la cámara (BGR, numpy array)
    'ts_captura': None,  # datetime del instante exacto en que se leyó ese frame
    'seq': 0,            # se incrementa en cada frame nuevo, para detectar duplicados
}
frame_lock = threading.Lock()
camara_activa = threading.Event()


def hilo_camara(cap):
    """Vacía sin parar el buffer de la cámara y publica solo el último
    frame disponible (con su timestamp de captura real) en frame_state.

    Corre en su propio hilo para que cv2.imwrite() (en el bucle
    principal) nunca retrase la lectura de la cámara: si cap.read() se
    llamara desde el bucle principal, cada bloqueo por escritura a disco
    dejaría acumular frames en el buffer interno de OpenCV, y el retraso
    crecería frame a frame."""
    while camara_activa.is_set():
        ret, frame = cap.read()
        ts_captura = datetime.now()
        if not ret:
            continue
        with frame_lock:
            frame_state['frame'] = frame
            frame_state['ts_captura'] = ts_captura
            frame_state['seq'] += 1


# ──────────────────────────────────────────────
#  UTILIDADES DE CÁMARA
# ──────────────────────────────────────────────
def recorte_cuadrado(frame):
    """Center crop: recorta el cuadrado central sin estirar la imagen."""
    h, w = frame.shape[:2]
    lado = min(h, w)
    y0 = (h - lado) // 2
    x0 = (w - lado) // 2
    return frame[y0:y0 + lado, x0:x0 + lado]


def iniciar_camara():
    cap = cv2.VideoCapture(CAMARA_INDEX)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir la cámara")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  RESOLUCION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCION[1])
    # Best-effort: en backends que lo soportan (p.ej. V4L2 en Linux/Pi)
    # limita la cola interna de OpenCV a 1 frame. No sustituye al hilo
    # dedicado (algunos backends lo ignoran), pero ayuda como capa extra.
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if (aw, ah) != RESOLUCION:
        print(f"[Cámara] AVISO: pediste {RESOLUCION[0]}x{RESOLUCION[1]} "
              f"pero el driver dio {aw}x{ah} (¿resolución no soportada "
              f"por esta conexión/USB?)")
    print(f"[Cámara] Captura {aw}x{ah}")
    return cap


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────
def main():
    sesion  = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta = os.path.join(OUTPUT_DIR, f"vuelo_{sesion}")
    os.makedirs(carpeta, exist_ok=True)
    ruta_csv = os.path.join(carpeta, "telemetria.csv")

    # Arrancar hilo MAVLink en segundo plano
    t = threading.Thread(target=hilo_mavlink, daemon=True)
    t.start()
    time.sleep(2)  # Dar margen para que intente conectar

    cap = iniciar_camara()

    # Arrancar hilo de cámara: drena cap.read() sin parar para que
    # cv2.imwrite() nunca bloquee la captura (ver docstring de hilo_camara)
    camara_activa.set()
    tc = threading.Thread(target=hilo_camara, args=(cap,), daemon=True)
    tc.start()

    print(f"\n[Captura] Intervalo: {INTERVALO_SEG}s | Carpeta: {carpeta}")
    print("[Captura] Pulsa Ctrl+C para detener\n")

    count      = 0
    ultimo     = 0.0
    ultimo_seq = -1
    t_inicio   = time.time()

    with open(ruta_csv, mode='w', newline='') as archivo_csv:
        escritor = csv.writer(archivo_csv)
        escritor.writerow([
            'Timestamp',
            'Archivo_Frame',
            'Pitch(deg)',
            'Roll(deg)',
            'Yaw_EKF(deg)',       # -180 a +180, del filtro interno ArduPilot
            'Rumbo_Norte(deg)',    # 0 a 360, brújula magnética — usar este para orientación
            'Latitud',
            'Longitud',
            'Alt_Relativa(m)',    # Barómetro desde despegue, ±1m — mejor para escala
            'Alt_AMSL(m)',        # GPS+baro sobre nivel del mar, ±5-15m
        ])

        try:
            while True:
                # ── Coger el frame más reciente publicado por hilo_camara ──
                with frame_lock:
                    frame      = frame_state['frame']
                    ts_captura = frame_state['ts_captura']
                    seq        = frame_state['seq']

                if frame is None or seq == ultimo_seq:
                    time.sleep(0.01)  # aún no hay frame nuevo; no quemar CPU
                    continue

                ahora = time.time()
                if ahora - ultimo < INTERVALO_SEG:
                    time.sleep(0.01)
                    continue

                # ── Leer telemetría INMEDIATAMENTE, antes de tocar disco ──
                # (emparejada con ts_captura, el instante real de la foto,
                # no con "ahora" que ya incluiría el retraso de imwrite())
                with lock:
                    snap = datos.copy()

                # ── Guardar frame PNG (lento, pero ya no bloquea la cámara) ──
                #frame = recorte_cuadrado(frame)
                ts       = ts_captura.strftime("%Y%m%d_%H%M%S_%f")[:-3]
                nombre   = f"frame_{ts}.png"
                ruta_png = os.path.join(carpeta, nombre)
                cv2.imwrite(ruta_png, frame,
                            [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESION])

                # ── Escribir fila CSV sincronizada ─────────────
                escritor.writerow([
                    ts,
                    nombre,
                    round(snap['pitch'],    2),
                    round(snap['roll'],     2),
                    round(snap['yaw'],      2),
                    snap['heading'],
                    snap['lat'],
                    snap['lon'],
                    round(snap['alt_rel'],  2),
                    round(snap['alt_amsl'], 2),
                ])
                archivo_csv.flush()

                count      += 1
                ultimo      = ahora
                ultimo_seq  = seq

                # ── Log en consola ─────────────────────────────
                print(
                    f"[{ts}] #{count:04d} | "
                    f"P:{snap['pitch']:5.1f}° R:{snap['roll']:5.1f}° "
                    f"Rumbo:{snap['heading']:3d}° | "
                    f"Lat:{snap['lat']:.6f} Lon:{snap['lon']:.6f} | "
                    f"Alt_rel:{snap['alt_rel']:.1f}m  Alt_AMSL:{snap['alt_amsl']:.1f}m"
                )

        except KeyboardInterrupt:
            pass

    camara_activa.clear()  # para el hilo_camara para poder liberar la cámara
    tc.join(timeout=2)
    elapsed = time.time() - t_inicio
    cap.release()

    print(f"\n{'─'*60}")
    print(f"Sesión:      {carpeta}")
    print(f"Frames PNG:  {count}")
    print(f"Telemetría:  {ruta_csv}")
    print(f"Duración:    {elapsed:.1f}s  ({count/elapsed:.2f} frames/s)")


if __name__ == "__main__":
    main()
