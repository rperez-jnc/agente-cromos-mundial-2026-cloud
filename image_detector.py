from io import BytesIO

import numpy as np
from PIL import Image

from collection_template import generar_cromos_mundial_2026


def detectar_cromos_naranja_desde_imagen(
    image_bytes,
    x1_pct=17,
    x2_pct=97,
    y1_pct=13,
    y2_pct=86,
    umbral_naranja_pct=4.0
):
    """
    Detecta celdas marcadas en naranja en una imagen de la plantilla.

    La detección es aproximada:
    - recorta la zona de la cuadrícula de cromos;
    - divide en 50 filas x 20 columnas;
    - calcula el porcentaje de píxeles naranjas por celda;
    - devuelve los cromos cuyo porcentaje supera el umbral.
    """

    imagen = Image.open(BytesIO(image_bytes)).convert("RGB")
    ancho, alto = imagen.size

    x1 = int(ancho * x1_pct / 100)
    x2 = int(ancho * x2_pct / 100)
    y1 = int(alto * y1_pct / 100)
    y2 = int(alto * y2_pct / 100)

    if x2 <= x1 or y2 <= y1:
        raise ValueError("El recorte de la cuadrícula no es válido.")

    recorte = imagen.crop((x1, y1, x2, y2))
    arr = np.array(recorte).astype(np.int16)

    filas = 50
    columnas = 20

    cromos_ordenados = generar_cromos_mundial_2026()

    if len(cromos_ordenados) != filas * columnas:
        raise ValueError(
            f"La plantilla tiene {len(cromos_ordenados)} cromos, "
            f"pero se esperaban {filas * columnas}."
        )

    alto_recorte, ancho_recorte, _ = arr.shape

    alto_celda = alto_recorte / filas
    ancho_celda = ancho_recorte / columnas

    detectados = []

    for fila in range(filas):
        for columna in range(columnas):
            indice = fila * columnas + columna
            cromo = cromos_ordenados[indice]

            cx1 = int(columna * ancho_celda + ancho_celda * 0.12)
            cx2 = int((columna + 1) * ancho_celda - ancho_celda * 0.12)
            cy1 = int(fila * alto_celda + alto_celda * 0.18)
            cy2 = int((fila + 1) * alto_celda - alto_celda * 0.18)

            celda = arr[cy1:cy2, cx1:cx2]

            if celda.size == 0:
                continue

            r = celda[:, :, 0]
            g = celda[:, :, 1]
            b = celda[:, :, 2]

            mascara_naranja = (
                (r > 145) &
                (g > 70) &
                (g < 220) &
                (b < 190) &
                ((r - g) > 3) &
                ((r - b) > 25)
            )

            porcentaje_naranja = float(mascara_naranja.mean() * 100)

            if porcentaje_naranja >= umbral_naranja_pct:
                detectados.append({
                    "ID": cromo["id"],
                    "Sección": cromo["seccion"],
                    "Grupo": cromo["grupo"],
                    "Número": cromo["numero"],
                    "Nombre": cromo["nombre"],
                    "Porcentaje naranja": round(porcentaje_naranja, 2),
                    "Fila": fila + 1,
                    "Columna": columna + 1
                })

    return detectados