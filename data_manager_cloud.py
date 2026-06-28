import re
from datetime import datetime

from db_cloud import get_conn


def normalizar_codigo_basico(codigo):
    codigo = str(codigo or "").strip().upper()
    codigo = codigo.replace(" ", "").replace("-", "")

    match = re.match(r"^([A-Z]+)(\d+)$", codigo)

    if match:
        prefijo = match.group(1)
        numero = match.group(2).zfill(2)
        return f"{prefijo}{numero}"

    return codigo


def normalizar_codigos_lote(texto):
    if not texto:
        return []

    partes = re.split(r"[\s,;]+", texto.strip())

    codigos = []

    for parte in partes:
        codigo = normalizar_codigo_basico(parte)

        if codigo:
            codigos.append(codigo)

    return codigos


def resolver_codigo_en_coleccion(datos, codigo):
    codigo = normalizar_codigo_basico(codigo)

    if codigo in datos["cromos"]:
        return codigo

    if codigo.startswith("COD"):
        codigo_cdd = "CDD" + codigo[3:]

        if codigo_cdd in datos["cromos"]:
            return codigo_cdd

    return codigo


def cargar_datos_usuario(usuario_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    cb.id,
                    cb.seccion,
                    cb.grupo,
                    cb.numero,
                    cb.nombre,
                    cb.tipo,
                    cb.orden_album,
                    cu.cantidad
                FROM coleccion_usuario cu
                INNER JOIN cromos_base cb ON cb.id = cu.cromo_id
                WHERE cu.usuario_id = %s
                ORDER BY cb.orden_album
                """,
                (usuario_id,),
            )

            cromos_rows = cur.fetchall()

            cur.execute(
                """
                SELECT
                    creado_en,
                    lote_id,
                    cromo_id,
                    tipo,
                    cantidad,
                    cantidad_antes,
                    cantidad_despues,
                    clasificacion_entrada,
                    comentario
                FROM movimientos
                WHERE usuario_id = %s
                ORDER BY creado_en DESC, id DESC
                LIMIT 1000
                """,
                (usuario_id,),
            )

            movimientos_rows = cur.fetchall()

    cromos = {}

    for row in cromos_rows:
        (
            cromo_id,
            seccion,
            grupo,
            numero,
            nombre,
            tipo,
            orden_album,
            cantidad,
        ) = row

        cromos[cromo_id] = {
            "seccion": seccion,
            "grupo": grupo,
            "numero": numero,
            "nombre": nombre,
            "tipo": tipo,
            "orden_album": orden_album,
            "cantidad": cantidad,
        }

    movimientos = []

    for row in movimientos_rows:
        (
            creado_en,
            lote_id,
            cromo_id,
            tipo,
            cantidad,
            cantidad_antes,
            cantidad_despues,
            clasificacion_entrada,
            comentario,
        ) = row

        movimientos.append(
            {
                "fecha": creado_en.strftime("%Y-%m-%d %H:%M:%S"),
                "lote_id": lote_id or "",
                "cromo_id": cromo_id,
                "tipo": tipo,
                "cantidad": cantidad,
                "cantidad_antes": cantidad_antes,
                "cantidad_despues": cantidad_despues,
                "clasificacion_entrada": clasificacion_entrada,
                "comentario": comentario or "",
            }
        )

    return {
        "_usuario_id": usuario_id,
        "cromos": cromos,
        "movimientos": movimientos,
    }


def registrar_movimiento(
    datos,
    cromo_id,
    tipo,
    cantidad,
    comentario="",
    lote_id=None,
    cantidad_antes=None,
    cantidad_despues=None,
    clasificacion_entrada=None,
):
    usuario_id = datos["_usuario_id"]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO movimientos (
                    usuario_id,
                    lote_id,
                    cromo_id,
                    tipo,
                    cantidad,
                    cantidad_antes,
                    cantidad_despues,
                    clasificacion_entrada,
                    comentario
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    usuario_id,
                    lote_id,
                    cromo_id,
                    tipo,
                    cantidad,
                    cantidad_antes,
                    cantidad_despues,
                    clasificacion_entrada,
                    comentario,
                ),
            )


def cambiar_cantidad(datos, cromo_id, diferencia, comentario=""):
    usuario_id = datos["_usuario_id"]
    cromo_id = resolver_codigo_en_coleccion(datos, cromo_id)

    if cromo_id not in datos["cromos"]:
        raise ValueError(f"El cromo {cromo_id} no existe.")

    cantidad_actual = datos["cromos"][cromo_id]["cantidad"]
    nueva_cantidad = cantidad_actual + diferencia

    if nueva_cantidad < 0:
        raise ValueError("La cantidad no puede ser negativa.")

    clasificacion_entrada = None

    if diferencia > 0:
        clasificacion_entrada = "nuevo" if cantidad_actual == 0 else "repetido"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE coleccion_usuario
                SET cantidad = %s,
                    actualizado_en = NOW()
                WHERE usuario_id = %s
                  AND cromo_id = %s
                """,
                (nueva_cantidad, usuario_id, cromo_id),
            )

            cur.execute(
                """
                INSERT INTO movimientos (
                    usuario_id,
                    lote_id,
                    cromo_id,
                    tipo,
                    cantidad,
                    cantidad_antes,
                    cantidad_despues,
                    clasificacion_entrada,
                    comentario
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    usuario_id,
                    None,
                    cromo_id,
                    "cambio_manual",
                    diferencia,
                    cantidad_actual,
                    nueva_cantidad,
                    clasificacion_entrada,
                    comentario,
                ),
            )

    datos["cromos"][cromo_id]["cantidad"] = nueva_cantidad

    return nueva_cantidad


def obtener_resumen(datos):
    cromos = datos["cromos"]

    total = len(cromos)
    conseguidos = sum(1 for cromo in cromos.values() if cromo["cantidad"] > 0)
    faltantes = sum(1 for cromo in cromos.values() if cromo["cantidad"] == 0)
    repetidas = sum(max(0, cromo["cantidad"] - 1) for cromo in cromos.values())

    porcentaje = 0

    if total:
        porcentaje = round((conseguidos / total) * 100, 2)

    return {
        "total": total,
        "conseguidos": conseguidos,
        "faltantes": faltantes,
        "repetidas": repetidas,
        "porcentaje": porcentaje,
    }


def listar_faltantes(datos):
    filas = []

    for cromo_id, cromo in datos["cromos"].items():
        if cromo["cantidad"] == 0:
            filas.append(
                {
                    "ID": cromo_id,
                    "Sección": cromo["seccion"],
                    "Grupo": cromo["grupo"],
                    "Número": cromo["numero"],
                    "Nombre": cromo["nombre"],
                    "Tipo": cromo["tipo"],
                    "Orden álbum": cromo["orden_album"],
                }
            )

    return filas


def listar_repetidas(datos):
    filas = []

    for cromo_id, cromo in datos["cromos"].items():
        repetidas = max(0, cromo["cantidad"] - 1)

        if repetidas > 0:
            filas.append(
                {
                    "ID": cromo_id,
                    "Sección": cromo["seccion"],
                    "Grupo": cromo["grupo"],
                    "Número": cromo["numero"],
                    "Nombre": cromo["nombre"],
                    "Tipo": cromo["tipo"],
                    "Cantidad": cromo["cantidad"],
                    "Repetidas": repetidas,
                    "Orden álbum": cromo["orden_album"],
                }
            )

    return filas


def aplicar_lote_cromos(datos, texto_codigos, diferencia, comentario="Actualización por lote"):
    usuario_id = datos["_usuario_id"]
    codigos_originales = normalizar_codigos_lote(texto_codigos)

    lote_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    resultado = {
        "lote_id": lote_id,
        "procesados": [],
        "nuevos": [],
        "repetidos": [],
        "errores": [],
    }

    operaciones = []

    for codigo_original in codigos_originales:
        cromo_id = resolver_codigo_en_coleccion(datos, codigo_original)

        if cromo_id not in datos["cromos"]:
            resultado["errores"].append(f"{codigo_original}: no existe.")
            continue

        cantidad_actual = datos["cromos"][cromo_id]["cantidad"]
        nueva_cantidad = cantidad_actual + diferencia

        if nueva_cantidad < 0:
            resultado["errores"].append(
                f"{cromo_id}: no se puede dejar cantidad negativa."
            )
            continue

        clasificacion_entrada = None

        if diferencia > 0:
            clasificacion_entrada = "nuevo" if cantidad_actual == 0 else "repetido"

        operaciones.append(
            {
                "cromo_id": cromo_id,
                "cantidad_actual": cantidad_actual,
                "nueva_cantidad": nueva_cantidad,
                "clasificacion_entrada": clasificacion_entrada,
            }
        )

    if not operaciones:
        return resultado

    with get_conn() as conn:
        with conn.cursor() as cur:
            for op in operaciones:
                cromo_id = op["cromo_id"]

                cur.execute(
                    """
                    UPDATE coleccion_usuario
                    SET cantidad = %s,
                        actualizado_en = NOW()
                    WHERE usuario_id = %s
                      AND cromo_id = %s
                    """,
                    (op["nueva_cantidad"], usuario_id, cromo_id),
                )

                cur.execute(
                    """
                    INSERT INTO movimientos (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        tipo,
                        cantidad,
                        cantidad_antes,
                        cantidad_despues,
                        clasificacion_entrada,
                        comentario
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        "lote",
                        diferencia,
                        op["cantidad_actual"],
                        op["nueva_cantidad"],
                        op["clasificacion_entrada"],
                        comentario,
                    ),
                )

                datos["cromos"][cromo_id]["cantidad"] = op["nueva_cantidad"]

                resultado["procesados"].append(cromo_id)

                if op["clasificacion_entrada"] == "nuevo":
                    resultado["nuevos"].append(cromo_id)
                elif op["clasificacion_entrada"] == "repetido":
                    resultado["repetidos"].append(cromo_id)

    return resultado


def obtener_entradas_por_lote(datos):
    filas = []

    for mov in datos.get("movimientos", []):
        if mov.get("cantidad", 0) <= 0:
            continue

        cromo_id = mov.get("cromo_id", "")
        cromo = datos["cromos"].get(cromo_id, {})

        filas.append(
            {
                "Fecha/Hora": mov.get("fecha", ""),
                "Lote entrada": mov.get("lote_id", ""),
                "Clasificación": mov.get("clasificacion_entrada") or "No disponible",
                "ID": cromo_id,
                "Grupo": cromo.get("grupo", ""),
                "Sección": cromo.get("seccion", ""),
                "Número": cromo.get("numero", ""),
                "Nombre": cromo.get("nombre", ""),
                "Cantidad entrada": mov.get("cantidad", ""),
                "Cantidad antes": mov.get("cantidad_antes", ""),
                "Cantidad después": mov.get("cantidad_despues", ""),
                "Comentario": mov.get("comentario", ""),
            }
        )

    return filas

def listar_todos(datos):
    filas = []

    for cromo_id, cromo in datos["cromos"].items():
        cantidad = cromo["cantidad"]

        filas.append(
            {
                "ID": cromo_id,
                "Sección": cromo["seccion"],
                "Grupo": cromo["grupo"],
                "Número": cromo["numero"],
                "Nombre": cromo["nombre"],
                "Tipo": cromo["tipo"],
                "Cantidad": cantidad,
                "Estado": "Tengo" if cantidad > 0 else "Falta",
                "Repetidas": max(0, cantidad - 1),
                "Orden álbum": cromo["orden_album"],
            }
        )

    return filas


def listar_movimientos(datos):
    filas = []

    for mov in datos.get("movimientos", []):
        cromo_id = mov.get("cromo_id", "")
        cromo = datos["cromos"].get(cromo_id, {})

        filas.append(
            {
                "Fecha": mov.get("fecha", ""),
                "Lote": mov.get("lote_id", ""),
                "ID": cromo_id,
                "Grupo": cromo.get("grupo", ""),
                "Sección": cromo.get("seccion", ""),
                "Nombre": cromo.get("nombre", ""),
                "Tipo movimiento": mov.get("tipo", ""),
                "Cantidad": mov.get("cantidad", ""),
                "Cantidad antes": mov.get("cantidad_antes", ""),
                "Cantidad después": mov.get("cantidad_despues", ""),
                "Clasificación": mov.get("clasificacion_entrada", ""),
                "Comentario": mov.get("comentario", ""),
            }
        )

    return filas


def aplicar_entrega_repetidas_lote(datos, texto_codigos, comentario="Entrega de repetidas"):
    usuario_id = datos["_usuario_id"]
    codigos_originales = normalizar_codigos_lote(texto_codigos)
    lote_id = datetime.now().strftime("ENT_%Y%m%d_%H%M%S")

    resultado = {
        "lote_id": lote_id,
        "procesados": [],
        "errores": [],
    }

    entregas = {}

    for codigo_original in codigos_originales:
        cromo_id = resolver_codigo_en_coleccion(datos, codigo_original)

        if cromo_id not in datos["cromos"]:
            resultado["errores"].append(f"{codigo_original}: no existe.")
            continue

        entregas[cromo_id] = entregas.get(cromo_id, 0) + 1

    for cromo_id, unidades in entregas.items():
        cantidad_actual = datos["cromos"][cromo_id]["cantidad"]

        if cantidad_actual - unidades < 1:
            resultado["errores"].append(
                f"{cromo_id}: no tienes suficientes repetidas. "
                f"Cantidad actual: {cantidad_actual}, intentas entregar: {unidades}."
            )

    if resultado["errores"]:
        return resultado

    with get_conn() as conn:
        with conn.cursor() as cur:
            for cromo_id, unidades in entregas.items():
                cantidad_actual = datos["cromos"][cromo_id]["cantidad"]
                nueva_cantidad = cantidad_actual - unidades

                cur.execute(
                    """
                    UPDATE coleccion_usuario
                    SET cantidad = %s,
                        actualizado_en = NOW()
                    WHERE usuario_id = %s
                      AND cromo_id = %s
                    """,
                    (nueva_cantidad, usuario_id, cromo_id),
                )

                cur.execute(
                    """
                    INSERT INTO movimientos (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        tipo,
                        cantidad,
                        cantidad_antes,
                        cantidad_despues,
                        clasificacion_entrada,
                        comentario
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        "entrega_repetida_lote",
                        -unidades,
                        cantidad_actual,
                        nueva_cantidad,
                        None,
                        comentario,
                    ),
                )

                datos["cromos"][cromo_id]["cantidad"] = nueva_cantidad
                resultado["procesados"].append(cromo_id)

    return resultado


def aplicar_intercambio_lote(datos, texto_recibo, texto_entrego, comentario="Intercambio de cromos"):
    usuario_id = datos["_usuario_id"]

    codigos_recibo_originales = normalizar_codigos_lote(texto_recibo)
    codigos_entrego_originales = normalizar_codigos_lote(texto_entrego)

    lote_id = datetime.now().strftime("INT_%Y%m%d_%H%M%S")

    resultado = {
        "lote_id": lote_id,
        "recibidos": [],
        "recibidos_nuevos": [],
        "recibidos_repetidos": [],
        "entregados": [],
        "errores": [],
    }

    codigos_recibo = []
    entregas = {}

    for codigo_original in codigos_recibo_originales:
        cromo_id = resolver_codigo_en_coleccion(datos, codigo_original)

        if cromo_id not in datos["cromos"]:
            resultado["errores"].append(f"RECIBO {codigo_original}: no existe.")
            continue

        codigos_recibo.append(cromo_id)

    for codigo_original in codigos_entrego_originales:
        cromo_id = resolver_codigo_en_coleccion(datos, codigo_original)

        if cromo_id not in datos["cromos"]:
            resultado["errores"].append(f"ENTREGO {codigo_original}: no existe.")
            continue

        entregas[cromo_id] = entregas.get(cromo_id, 0) + 1

    for cromo_id, unidades in entregas.items():
        cantidad_actual = datos["cromos"][cromo_id]["cantidad"]

        if cantidad_actual - unidades < 1:
            resultado["errores"].append(
                f"ENTREGO {cromo_id}: no tienes suficientes repetidas. "
                f"Cantidad actual: {cantidad_actual}, intentas entregar: {unidades}."
            )

    if not codigos_recibo and not entregas:
        resultado["errores"].append("No has indicado cromos para recibir ni entregar.")

    if resultado["errores"]:
        return resultado

    with get_conn() as conn:
        with conn.cursor() as cur:
            for cromo_id in codigos_recibo:
                cantidad_actual = datos["cromos"][cromo_id]["cantidad"]
                nueva_cantidad = cantidad_actual + 1
                clasificacion = "nuevo" if cantidad_actual == 0 else "repetido"

                cur.execute(
                    """
                    UPDATE coleccion_usuario
                    SET cantidad = %s,
                        actualizado_en = NOW()
                    WHERE usuario_id = %s
                      AND cromo_id = %s
                    """,
                    (nueva_cantidad, usuario_id, cromo_id),
                )

                cur.execute(
                    """
                    INSERT INTO movimientos (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        tipo,
                        cantidad,
                        cantidad_antes,
                        cantidad_despues,
                        clasificacion_entrada,
                        comentario
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        "intercambio_recibo",
                        1,
                        cantidad_actual,
                        nueva_cantidad,
                        clasificacion,
                        comentario,
                    ),
                )

                datos["cromos"][cromo_id]["cantidad"] = nueva_cantidad
                resultado["recibidos"].append(cromo_id)

                if clasificacion == "nuevo":
                    resultado["recibidos_nuevos"].append(cromo_id)
                else:
                    resultado["recibidos_repetidos"].append(cromo_id)

            for cromo_id, unidades in entregas.items():
                cantidad_actual = datos["cromos"][cromo_id]["cantidad"]
                nueva_cantidad = cantidad_actual - unidades

                cur.execute(
                    """
                    UPDATE coleccion_usuario
                    SET cantidad = %s,
                        actualizado_en = NOW()
                    WHERE usuario_id = %s
                      AND cromo_id = %s
                    """,
                    (nueva_cantidad, usuario_id, cromo_id),
                )

                cur.execute(
                    """
                    INSERT INTO movimientos (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        tipo,
                        cantidad,
                        cantidad_antes,
                        cantidad_despues,
                        clasificacion_entrada,
                        comentario
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        "intercambio_entrego",
                        -unidades,
                        cantidad_actual,
                        nueva_cantidad,
                        None,
                        comentario,
                    ),
                )

                datos["cromos"][cromo_id]["cantidad"] = nueva_cantidad
                resultado["entregados"].append(cromo_id)

    return resultado

def inicializar_coleccion_usuario_desde_lote(
    datos,
    texto_codigos,
    comentario="Inicialización de colección desde lote",
):
    usuario_id = datos["_usuario_id"]
    codigos_originales = normalizar_codigos_lote(texto_codigos)

    resultado = {
        "procesados": [],
        "nuevos": [],
        "repetidos": [],
        "errores": [],
    }

    cantidades_por_codigo = {}

    for codigo_original in codigos_originales:
        cromo_id = resolver_codigo_en_coleccion(datos, codigo_original)

        if cromo_id not in datos["cromos"]:
            resultado["errores"].append(f"{codigo_original}: no existe en la colección.")
            continue

        cantidades_por_codigo[cromo_id] = cantidades_por_codigo.get(cromo_id, 0) + 1

    if not cantidades_por_codigo:
        resultado["errores"].append("No has indicado ningún cromo válido.")
        return resultado

    if resultado["errores"]:
        return resultado

    lote_id = datetime.now().strftime("INI_%Y%m%d_%H%M%S")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE coleccion_usuario
                SET cantidad = 0,
                    actualizado_en = NOW()
                WHERE usuario_id = %s
                """,
                (usuario_id,),
            )

            for cromo_id, cantidad_final in cantidades_por_codigo.items():
                cur.execute(
                    """
                    UPDATE coleccion_usuario
                    SET cantidad = %s,
                        actualizado_en = NOW()
                    WHERE usuario_id = %s
                      AND cromo_id = %s
                    """,
                    (cantidad_final, usuario_id, cromo_id),
                )

                cur.execute(
                    """
                    INSERT INTO movimientos (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        tipo,
                        cantidad,
                        cantidad_antes,
                        cantidad_despues,
                        clasificacion_entrada,
                        comentario
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        "inicializacion",
                        cantidad_final,
                        0,
                        cantidad_final,
                        "nuevo" if cantidad_final == 1 else "repetido",
                        comentario,
                    ),
                )

                datos["cromos"][cromo_id]["cantidad"] = cantidad_final
                resultado["procesados"].append(cromo_id)

                if cantidad_final == 1:
                    resultado["nuevos"].append(cromo_id)
                else:
                    resultado["repetidos"].append(cromo_id)

    return resultado

def aplicar_checks_estado_usuario(
    datos,
    filas_editadas,
    comentario="Marcaje inicial manual con checks",
):
    usuario_id = datos["_usuario_id"]

    resultado = {
        "procesados": [],
        "marcados": [],
        "desmarcados": [],
        "errores": [],
        "sin_cambios": 0,
    }

    operaciones = []

    for fila in filas_editadas:
        cromo_id = resolver_codigo_en_coleccion(datos, fila.get("ID", ""))
        tengo = bool(fila.get("Tengo", False))

        if cromo_id not in datos["cromos"]:
            resultado["errores"].append(f"{cromo_id}: no existe.")
            continue

        cantidad_actual = datos["cromos"][cromo_id]["cantidad"]

        if tengo:
            nueva_cantidad = max(1, cantidad_actual)
        else:
            nueva_cantidad = 0

        if nueva_cantidad == cantidad_actual:
            resultado["sin_cambios"] += 1
            continue

        diferencia = nueva_cantidad - cantidad_actual

        clasificacion_entrada = None

        if diferencia > 0:
            clasificacion_entrada = "nuevo" if cantidad_actual == 0 else "repetido"

        operaciones.append(
            {
                "cromo_id": cromo_id,
                "cantidad_actual": cantidad_actual,
                "nueva_cantidad": nueva_cantidad,
                "diferencia": diferencia,
                "clasificacion_entrada": clasificacion_entrada,
            }
        )

    if resultado["errores"]:
        return resultado

    if not operaciones:
        return resultado

    lote_id = datetime.now().strftime("CHK_%Y%m%d_%H%M%S")

    with get_conn() as conn:
        with conn.cursor() as cur:
            for op in operaciones:
                cromo_id = op["cromo_id"]

                cur.execute(
                    """
                    UPDATE coleccion_usuario
                    SET cantidad = %s,
                        actualizado_en = NOW()
                    WHERE usuario_id = %s
                      AND cromo_id = %s
                    """,
                    (
                        op["nueva_cantidad"],
                        usuario_id,
                        cromo_id,
                    ),
                )

                cur.execute(
                    """
                    INSERT INTO movimientos (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        tipo,
                        cantidad,
                        cantidad_antes,
                        cantidad_despues,
                        clasificacion_entrada,
                        comentario
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        usuario_id,
                        lote_id,
                        cromo_id,
                        "marcaje_check",
                        op["diferencia"],
                        op["cantidad_actual"],
                        op["nueva_cantidad"],
                        op["clasificacion_entrada"],
                        comentario,
                    ),
                )

                datos["cromos"][cromo_id]["cantidad"] = op["nueva_cantidad"]
                resultado["procesados"].append(cromo_id)

                if op["nueva_cantidad"] > 0:
                    resultado["marcados"].append(cromo_id)
                else:
                    resultado["desmarcados"].append(cromo_id)

    return resultado

def obtener_resumen_lotes_entrada(datos):
    lotes = {}

    for mov in datos.get("movimientos", []):
        lote_id = mov.get("lote_id", "")
        cantidad = int(mov.get("cantidad") or 0)

        if not lote_id or cantidad <= 0:
            continue

        if lote_id not in lotes:
            lotes[lote_id] = {
                "Lote": lote_id,
                "Fecha entrada": mov.get("fecha", ""),
                "Cromos distintos": set(),
                "Unidades entrada": 0,
                "Nuevos": 0,
                "Ya los tenía": 0,
                "Repetidos dentro del lote": 0,
            }

        cromo_id = mov.get("cromo_id", "")
        cantidad_antes = int(mov.get("cantidad_antes") or 0)

        lotes[lote_id]["Cromos distintos"].add(cromo_id)
        lotes[lote_id]["Unidades entrada"] += cantidad

        if cantidad_antes > 0:
            lotes[lote_id]["Ya los tenía"] += 1
        else:
            lotes[lote_id]["Nuevos"] += 1

    filas = []

    for lote in lotes.values():
        filas.append(
            {
                "Fecha entrada": lote["Fecha entrada"],
                "Lote": lote["Lote"],
                "Cromos distintos": len(lote["Cromos distintos"]),
                "Unidades entrada": lote["Unidades entrada"],
                "Nuevos": lote["Nuevos"],
                "Ya los tenía": lote["Ya los tenía"],
                "Repetidos dentro del lote": lote["Repetidos dentro del lote"],
            }
        )

    filas.sort(key=lambda x: x["Fecha entrada"], reverse=True)

    return filas


def obtener_detalle_lote_entrada(datos, lote_id):
    acumulado = {}

    for mov in datos.get("movimientos", []):
        if mov.get("lote_id", "") != lote_id:
            continue

        cantidad = int(mov.get("cantidad") or 0)

        if cantidad <= 0:
            continue

        cromo_id = mov.get("cromo_id", "")
        cromo = datos["cromos"].get(cromo_id, {})

        if cromo_id not in acumulado:
            acumulado[cromo_id] = {
                "Fecha entrada": mov.get("fecha", ""),
                "Lote": lote_id,
                "ID": cromo_id,
                "Grupo": cromo.get("grupo", ""),
                "Sección": cromo.get("seccion", ""),
                "Número": cromo.get("numero", ""),
                "Nombre": cromo.get("nombre", ""),
                "Tipo": cromo.get("tipo", ""),
                "Cantidad entrada": 0,
                "Cantidad antes": int(mov.get("cantidad_antes") or 0),
                "Cantidad después": int(mov.get("cantidad_despues") or 0),
                "Veces en lote": 0,
            }

        acumulado[cromo_id]["Cantidad entrada"] += cantidad
        acumulado[cromo_id]["Veces en lote"] += 1
        acumulado[cromo_id]["Cantidad después"] = max(
            acumulado[cromo_id]["Cantidad después"],
            int(mov.get("cantidad_despues") or 0),
        )

    filas = []

    for fila in acumulado.values():
        ya_lo_tenia = fila["Cantidad antes"] > 0
        repetido_en_lote = fila["Cantidad entrada"] > 1 or fila["Veces en lote"] > 1

        if ya_lo_tenia and repetido_en_lote:
            clasificacion = "Ya lo tenía y repetido en el lote"
        elif ya_lo_tenia:
            clasificacion = "Ya lo tenía"
        elif repetido_en_lote:
            clasificacion = "Nuevo, pero repetido en el lote"
        else:
            clasificacion = "Nuevo"

        fila["Clasificación"] = clasificacion
        fila["Ya lo tenía"] = "Sí" if ya_lo_tenia else "No"
        fila["Repetido dentro del lote"] = "Sí" if repetido_en_lote else "No"

        filas.append(fila)

    filas.sort(key=lambda x: x["ID"])

    return filas
