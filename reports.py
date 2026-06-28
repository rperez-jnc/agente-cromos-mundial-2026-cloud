from pathlib import Path
from datetime import datetime
from io import BytesIO

import pandas as pd

REPORTS_DIR = Path("informes")


def generar_resumen_txt(datos, resumen):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lineas = [
        "RESUMEN COLECCIÓN CROMOS MUNDIAL 2026",
        f"Generado: {fecha}",
        "",
        f"Total cromos: {resumen['total']}",
        f"Conseguidos: {resumen['conseguidos']}",
        f"Faltantes: {resumen['faltantes']}",
        f"Repetidas: {resumen['repetidas']}",
        f"Porcentaje completado: {resumen['porcentaje']}%",
        ""
    ]

    return "\n".join(lineas)


def generar_faltantes_txt(faltantes):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lineas = [
        "CROMOS FALTANTES - MUNDIAL 2026",
        f"Generado: {fecha}",
        "",
    ]

    if not faltantes:
        lineas.append("No falta ningún cromo.")
    else:
        seccion_actual = None

        for cromo_id, cromo in faltantes.items():
            if cromo["seccion"] != seccion_actual:
                seccion_actual = cromo["seccion"]
                lineas.append("")
                lineas.append(f"## {seccion_actual}")

            lineas.append(
                f"- {cromo_id} | Nº {cromo['numero']} | {cromo['nombre']}"
            )

    return "\n".join(lineas)


def generar_repetidas_txt(repetidas):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lineas = [
        "CROMOS REPETIDOS - MUNDIAL 2026",
        f"Generado: {fecha}",
        "",
    ]

    if not repetidas:
        lineas.append("No tienes cromos repetidos.")
    else:
        seccion_actual = None

        for cromo_id, cromo in repetidas.items():
            if cromo["seccion"] != seccion_actual:
                seccion_actual = cromo["seccion"]
                lineas.append("")
                lineas.append(f"## {seccion_actual}")

            lineas.append(
                f"- {cromo_id} | Nº {cromo['numero']} | {cromo['nombre']} | Repetidas: {cromo['repetidas']}"
            )

    return "\n".join(lineas)


def guardar_txt(nombre_archivo, contenido):
    REPORTS_DIR.mkdir(exist_ok=True)

    ruta = REPORTS_DIR / nombre_archivo

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)

    return ruta

def generar_excel_bytes(datos, resumen):
    cromos = datos["cromos"]
    movimientos = datos["movimientos"]

    filas_todos = []
    filas_tengo = []
    filas_faltantes = []
    filas_repetidas = []

    for cromo_id, cromo in cromos.items():
        cantidad = cromo["cantidad"]
        repetidas = max(0, cantidad - 1)

        fila_base = {
            "ID": cromo_id,
            "Sección": cromo["seccion"],
            "Número": cromo["numero"],
            "Nombre": cromo["nombre"],
            "Tipo": cromo["tipo"],
            "Cantidad total": cantidad,
            "Lo tengo": "Sí" if cantidad >= 1 else "No",
            "Cantidad repetida": repetidas,
            "Estado": "Falta" if cantidad == 0 else "Conseguido"
        }

        filas_todos.append(fila_base)

        if cantidad >= 1:
            filas_tengo.append({
                "ID": cromo_id,
                "Sección": cromo["seccion"],
                "Número": cromo["numero"],
                "Nombre": cromo["nombre"],
                "Tipo": cromo["tipo"],
                "Cantidad total": cantidad,
                "Cantidad repetida": repetidas
            })

        if cantidad == 0:
            filas_faltantes.append({
                "ID": cromo_id,
                "Sección": cromo["seccion"],
                "Número": cromo["numero"],
                "Nombre": cromo["nombre"],
                "Tipo": cromo["tipo"]
            })

        if cantidad > 1:
            filas_repetidas.append({
                "ID": cromo_id,
                "Sección": cromo["seccion"],
                "Número": cromo["numero"],
                "Nombre": cromo["nombre"],
                "Tipo": cromo["tipo"],
                "Cantidad total": cantidad,
                "Cantidad repetida": repetidas
            })

    df_resumen = pd.DataFrame([
        {"Métrica": "Total cromos", "Valor": resumen["total"]},
        {"Métrica": "Conseguidos", "Valor": resumen["conseguidos"]},
        {"Métrica": "Faltantes", "Valor": resumen["faltantes"]},
        {"Métrica": "Repetidas", "Valor": resumen["repetidas"]},
        {"Métrica": "% completado", "Valor": resumen["porcentaje"]},
    ])

    df_todos = pd.DataFrame(filas_todos)
    df_tengo = pd.DataFrame(filas_tengo)
    df_faltantes = pd.DataFrame(filas_faltantes)
    df_repetidas = pd.DataFrame(filas_repetidas)
    df_movimientos = pd.DataFrame(movimientos)

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
        df_todos.to_excel(writer, sheet_name="Todos", index=False)
        df_tengo.to_excel(writer, sheet_name="Tengo", index=False)
        df_faltantes.to_excel(writer, sheet_name="Faltantes", index=False)
        df_repetidas.to_excel(writer, sheet_name="Repetidas", index=False)
        df_movimientos.to_excel(writer, sheet_name="Movimientos", index=False)

    output.seek(0)
    return output.getvalue()
def guardar_excel(nombre_archivo, contenido_excel):
    REPORTS_DIR.mkdir(exist_ok=True)

    ruta = REPORTS_DIR / nombre_archivo

    with open(ruta, "wb") as f:
        f.write(contenido_excel)

    return ruta

def generar_entradas_lotes_txt(datos):
    movimientos = datos.get("movimientos", [])
    cromos = datos.get("cromos", {})

    lineas = [
        "INFORME DE ENTRADAS POR LOTE - CROMOS MUNDIAL 2026",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "Este informe separa los cromos conseguidos nuevos de los repetidos.",
        "Los movimientos antiguos pueden aparecer como 'No disponible' si se registraron antes de guardar cantidad antes/después.",
        ""
    ]

    entradas = [
        mov for mov in movimientos
        if mov.get("cantidad", 0) > 0
    ]

    if not entradas:
        lineas.append("No hay entradas registradas.")
        return "\n".join(lineas)

    entradas = sorted(
        entradas,
        key=lambda x: (x.get("fecha", ""), x.get("lote_id", ""), x.get("cromo_id", ""))
    )

    lote_actual = None

    for mov in entradas:
        lote_id = mov.get("lote_id") or mov.get("fecha", "")
        fecha = mov.get("fecha", "")
        cromo_id = mov.get("cromo_id", "")
        cromo = cromos.get(cromo_id, {})

        if lote_id != lote_actual:
            lote_actual = lote_id
            lineas.append("")
            lineas.append(f"LOTE: {lote_id}")
            lineas.append(f"Fecha/hora: {fecha}")

        clasificacion = mov.get("clasificacion_entrada") or "No disponible"

        lineas.append(
            f"- {clasificacion.upper()} | "
            f"{cromo_id} | "
            f"{cromo.get('seccion', '')} | "
            f"{cromo.get('nombre', '')} | "
            f"Antes: {mov.get('cantidad_antes', '')} | "
            f"Después: {mov.get('cantidad_despues', '')} | "
            f"Comentario: {mov.get('comentario', '')}"
        )

    return "\n".join(lineas)


def generar_entradas_lotes_excel_bytes(datos):
    movimientos = datos.get("movimientos", [])
    cromos = datos.get("cromos", {})

    filas_detalle = []

    for mov in movimientos:
        if mov.get("cantidad", 0) <= 0:
            continue

        cromo_id = mov.get("cromo_id", "")
        cromo = cromos.get(cromo_id, {})

        filas_detalle.append({
            "Fecha/Hora": mov.get("fecha", ""),
            "Lote entrada": mov.get("lote_id", ""),
            "Tipo movimiento": mov.get("tipo", ""),
            "Clasificación entrada": mov.get("clasificacion_entrada") or "No disponible",
            "ID": cromo_id,
            "Grupo": cromo.get("grupo", ""),
            "Sección": cromo.get("seccion", ""),
            "Número": cromo.get("numero", ""),
            "Nombre": cromo.get("nombre", ""),
            "Cantidad entrada": mov.get("cantidad", ""),
            "Cantidad antes": mov.get("cantidad_antes", ""),
            "Cantidad después": mov.get("cantidad_despues", ""),
            "Comentario": mov.get("comentario", "")
        })

    df_detalle = pd.DataFrame(filas_detalle)

    if df_detalle.empty:
        df_detalle = pd.DataFrame(columns=[
            "Fecha/Hora",
            "Lote entrada",
            "Tipo movimiento",
            "Clasificación entrada",
            "ID",
            "Grupo",
            "Sección",
            "Número",
            "Nombre",
            "Cantidad entrada",
            "Cantidad antes",
            "Cantidad después",
            "Comentario"
        ])

        df_resumen = pd.DataFrame(columns=[
            "Lote entrada",
            "Fecha/Hora",
            "Clasificación entrada",
            "Total cromos"
        ])
    else:
        df_resumen = (
            df_detalle
            .groupby(["Lote entrada", "Fecha/Hora", "Clasificación entrada"])
            .size()
            .reset_index(name="Total cromos")
        )

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_resumen.to_excel(writer, sheet_name="ResumenEntradas", index=False)
        df_detalle.to_excel(writer, sheet_name="DetalleEntradas", index=False)

    output.seek(0)
    return output.getvalue()