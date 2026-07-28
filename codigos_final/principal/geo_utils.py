"""
geo_utils.py
Utilidades reutilizables:
  - Conversión pixel <-> coordenada geográfica usando el Geotransform (GT)
  - Estimación de la huella (footprint) en el suelo de una foto nadir de dron
  - Distancia Haversine para medir el error de localización en metros

Sin dependencias pesadas: solo necesita el objeto `transform` de rasterio
(un rasterio.transform.Affine), que ya expone directamente a, b, c, d, e, f.
"""
import math


def px2geo(x, y, gt):
    """
    Pixel (columna x, fila y) -> coordenada proyectada (X_geo, Y_geo).
    Se suma 0.5 para referenciar el centro del píxel, no su esquina.
    """
    X_geo = gt.c + (x + 0.5) * gt.a + (y + 0.5) * gt.b
    Y_geo = gt.f + (x + 0.5) * gt.d + (y + 0.5) * gt.e
    return X_geo, Y_geo


def geo2px(X_geo, Y_geo, gt):
    """Coordenada proyectada -> pixel (x, y). Inversa de px2geo."""
    inv = ~gt
    x, y = inv * (X_geo, Y_geo)
    return x - 0.5, y - 0.5


def ground_footprint_m(alt_m, hfov_deg=121.0, aspect_ratio=(4, 3)):
    """
    Estima el ancho y alto (en metros) del terreno cubierto por una foto
    nadir de dron, a partir de la altura relativa y el FOV horizontal.

    hfov_deg=121° es una calibración empírica para el sensor AR0234 en
    modo 1920x1200 (medida sobre imágenes reales a 80m y 120m de altura).
    Depende de la resolución de captura -- recalibrar si cambia (a
    1280x960 el HFOV efectivo medido es 108°).

    aspect_ratio acepta directamente (ancho_px, alto_px) del frame real;
    el valor (4, 3) es solo un fallback si no se conoce la resolución.
    """
    half_hfov = math.radians(hfov_deg / 2.0)
    width_m = 2 * alt_m * math.tan(half_hfov)
    height_m = width_m * (aspect_ratio[1] / aspect_ratio[0])
    return width_m, height_m


def web_mercator_scale(lat_deg):
    """
    Factor de escala local de Web Mercator (EPSG:3857) en la latitud dada:
    sec(lat) = 1 / cos(lat). Convierte una distancia real en metros a
    "metros proyectados" del raster (coinciden solo en el ecuador).
    """
    return 1.0 / math.cos(math.radians(lat_deg))


def meters_per_degree(lat_deg):
    """Aproximación local de metros por grado de latitud/longitud."""
    lat_rad = math.radians(lat_deg)
    m_per_deg_lat = 111132.92 - 559.82 * math.cos(2 * lat_rad) + 1.175 * math.cos(4 * lat_rad)
    m_per_deg_lon = 111412.84 * math.cos(lat_rad) - 93.5 * math.cos(3 * lat_rad)
    return m_per_deg_lat, m_per_deg_lon


def haversine_m(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dos coordenadas WGS84 (para medir error)."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def nadir_offset_m(pitch_deg, roll_deg, yaw_deg, alt_m):
    """
    Desplazamiento en tierra (norte, este), en metros, entre la posición
    GPS/IMU del dron y el punto de terreno que realmente mira el CENTRO
    de una cámara nadir rígida (sin gimbal), dado el pitch/roll del dron.

    Con pitch/roll=0 ambos puntos coinciden; en vuelo real no. Aplicar
    esta corrección al punto de verdad-terreno reduce el error medio de
    localización de ~12.3m a ~6.2m sobre las 76 queries del vuelo de
    validación (r=0.77 entre offset y error medido).

    Convención MAVLink/ArduPilot: pitch positivo = morro arriba, roll
    positivo = ala derecha abajo. yaw_deg es el rumbo respecto al norte
    (Rumbo_Norte de telemetria.csv). Asume terreno localmente plano.

    Devuelve (offset_norte_m, offset_este_m): sumar a la posición GPS
    para obtener el punto de terreno real que mira el centro de imagen.
    """
    theta = math.radians(pitch_deg)
    phi = math.radians(roll_deg)
    psi = math.radians(yaw_deg)
    denom = math.cos(theta) * math.cos(phi)
    north = alt_m * (math.cos(psi) * math.sin(theta) * math.cos(phi) + math.sin(psi) * math.sin(phi)) / denom
    east = alt_m * (math.sin(psi) * math.sin(theta) * math.cos(phi) - math.cos(psi) * math.sin(phi)) / denom
    return north, east
