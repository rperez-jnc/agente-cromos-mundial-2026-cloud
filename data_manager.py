import json
import re
from pathlib import Path
from datetime import datetime
from collection_template import generar_cromos_mundial_2026

DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "coleccion.json"
BACKUP_DIR = DATA_DIR / "backups"

def crear_datos_iniciales():
    return {
        "cromos": {
            "ESP-01": {
                "seccion": "España",
                "numero": "01",
                "nombre": "Escudo España",
                "tipo": "escudo",
                "cantidad": 0
            },
            "ESP-02": {
                "seccion": "España",
                "numero": "02",
                "nombre": "Jugador España 1",
                "tipo": "jugador",
                "cantidad": 0
            },
            "ARG-01": {
                "seccion": "Argentina",
                "numero": "01",
                "nombre": "Escudo Argentina",
                "tipo": "escudo",
                "cantidad": 0
            },
            "ARG-02": {
                "seccion": "Argentina",
                "numero": "02",
                "nombre": "Jugador Argentina 1",
                "tipo": "jugador",
                "cantidad": 0
            }
        },
        "movimientos": []
    }


def cargar_datos():
    DATA_DIR.mkdir(exist_ok=True)

    if not DATA_FILE.exists():
        datos = crear_datos_iniciales()
        guardar_datos(datos)
        return datos

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_datos(datos):
    DATA_DIR.mkdir(exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def registrar_movimiento(
    datos,
    cromo_id,
    tipo,
    cantidad,
    comentario="",
    lote_id=None,
    cantidad_antes=None,
    cantidad_despues=None,
    clasificacion_entrada=None
):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    movimiento = {
        "fecha": fecha,
        "lote_id": lote_id if lote_id else fecha,
        "cromo_id": cromo_id,
        "tipo": tipo,
        "cantidad": cantidad,
        "cantidad_antes": cantidad_antes,
        "cantidad_despues": cantidad_despues,
        "clasificacion_entrada": clasificacion_entrada,
        "comentario": comentario
    }

    datos["movimientos"].append(movimiento)


def cambiar_cantidad(datos, cromo_id, diferencia, comentario=""):
    if cromo_id not in datos["cromos"]:
        raise ValueError(f"El cromo {cromo_id} no existe.")

    cantidad_actual = datos["cromos"][cromo_id]["cantidad"]
    nueva_cantidad = cantidad_actual + diferencia

    if nueva_cantidad < 0:
        raise ValueError("La cantidad no puede quedar por debajo de 0.")

    datos["cromos"][cromo_id]["cantidad"] = nueva_cantidad

    tipo = "entrada" if diferencia > 0 else "salida"

    clasificacion_entrada = None
    if diferencia > 0:
        clasificacion_entrada = "nuevo" if cantidad_actual == 0 else "repetido"

    registrar_movimiento(
        datos,
        cromo_id,
        tipo,
        diferencia,
        comentario,
        cantidad_antes=cantidad_actual,
        cantidad_despues=nueva_cantidad,
        clasificacion_entrada=clasificacion_entrada
    )

    guardar_datos(datos)


def obtener_resumen(datos):
    cromos = datos["cromos"]

    total = len(cromos)
    conseguidos = sum(1 for c in cromos.values() if c["cantidad"] >= 1)
    faltantes = sum(1 for c in cromos.values() if c["cantidad"] == 0)
    repetidas = sum(max(0, c["cantidad"] - 1) for c in cromos.values())

    porcentaje = round((conseguidos / total) * 100, 2) if total > 0 else 0

    return {
        "total": total,
        "conseguidos": conseguidos,
        "faltantes": faltantes,
        "repetidas": repetidas,
        "porcentaje": porcentaje
    }


def listar_faltantes(datos):
    return {
        cromo_id: cromo
        for cromo_id, cromo in datos["cromos"].items()
        if cromo["cantidad"] == 0
    }


def listar_repetidas(datos):
    return {
        cromo_id: {
            **cromo,
            "repetidas": cromo["cantidad"] - 1
        }
        for cromo_id, cromo in datos["cromos"].items()
        if cromo["cantidad"] > 1
    }

def inicializar_coleccion_mundial_2026():
    cromos_plantilla = generar_cromos_mundial_2026()

    nuevos_cromos = {}

    for cromo in cromos_plantilla:
        cromo_id = cromo["id"]

        nuevos_cromos[cromo_id] = {
            "seccion": cromo["seccion"],
            "grupo": cromo["grupo"],
            "numero": cromo["numero"],
            "nombre": cromo["nombre"],
            "tipo": cromo["tipo"],
            "orden_album": cromo["orden_album"],
            "cantidad": 0
        }

    datos = {
        "cromos": nuevos_cromos,
        "movimientos": []
    }

    registrar_movimiento(
        datos,
        "SISTEMA",
        "inicializacion",
        len(nuevos_cromos),
        "Colección Mundial 2026 inicializada desde plantilla"
    )

    guardar_datos(datos)

    return len(nuevos_cromos)


def normalizar_codigo_basico(codigo):
    if not codigo:
        return ""

    codigo = str(codigo).strip().upper()
    codigo = codigo.replace("-", "")
    codigo = codigo.replace(" ", "")

    # Convierte ESP1 -> ESP01, ARG9 -> ARG09, FWC2 -> FWC02
    match = re.match(r"^([A-Z]{2,4})(\d{1,2})$", codigo)

    if match:
        prefijo = match.group(1)
        numero = int(match.group(2))
        codigo = f"{prefijo}{numero:02d}"

    return codigo


def normalizar_codigos_lote(texto):
    if not texto:
        return []

    partes = re.split(r"[\s,;]+", texto.strip().upper())

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

    # Alias temporal: si el usuario escribe COD09 pero la plantilla actual tiene CDD09
    if codigo.startswith("COD"):
        codigo_cdd = "CDD" + codigo[3:]

        if codigo_cdd in datos["cromos"]:
            return codigo_cdd

    return codigo

def aplicar_lote_cromos(datos, texto_codigos, diferencia, comentario="Actualización por lote"):
    codigos = normalizar_codigos_lote(texto_codigos)

    lote_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    resultado = {
        "lote_id": lote_id,
        "procesados": [],
        "nuevos": [],
        "repetidos": [],
        "errores": []
    }

    if not codigos:
        resultado["errores"].append("No se ha indicado ningún código.")
        return resultado

    for codigo_original in codigos:
        codigo = resolver_codigo_en_coleccion(datos, codigo_original)

        if codigo not in datos["cromos"]:
            resultado["errores"].append(f"{codigo_original}: no existe en la colección.")
            continue

        cantidad_actual = datos["cromos"][codigo]["cantidad"]
        nueva_cantidad = cantidad_actual + diferencia

        if nueva_cantidad < 0:
            resultado["errores"].append(f"{codigo}: la cantidad no puede quedar por debajo de 0.")
            continue

        if diferencia < 0 and cantidad_actual <= 1:
            resultado["errores"].append(f"{codigo}: no tienes repetida para entregar.")
            continue

        datos["cromos"][codigo]["cantidad"] = nueva_cantidad

        tipo = "entrada_lote" if diferencia > 0 else "salida_lote"

        clasificacion_entrada = None

        if diferencia > 0:
            if cantidad_actual == 0:
                clasificacion_entrada = "nuevo"
                resultado["nuevos"].append(codigo)
            else:
                clasificacion_entrada = "repetido"
                resultado["repetidos"].append(codigo)

        registrar_movimiento(
            datos,
            codigo,
            tipo,
            diferencia,
            comentario,
            lote_id=lote_id,
            cantidad_antes=cantidad_actual,
            cantidad_despues=nueva_cantidad,
            clasificacion_entrada=clasificacion_entrada
        )

        resultado["procesados"].append(codigo)

    guardar_datos(datos)

    return resultado


def marcar_como_tengo_lote(datos, codigos, comentario="Importación desde imagen"):
    resultado = {
        "procesados": [],
        "errores": [],
        "ya_estaban": []
    }

    for codigo in codigos:
        codigo = resolver_codigo_en_coleccion(datos, codigo)

        if codigo not in datos["cromos"]:
            resultado["errores"].append(f"{codigo}: no existe en la colección.")
            continue

        cantidad_actual = datos["cromos"][codigo]["cantidad"]

        if cantidad_actual >= 1:
            resultado["ya_estaban"].append(codigo)
            continue

        datos["cromos"][codigo]["cantidad"] = 1

        registrar_movimiento(
            datos,
            codigo,
            "importacion_imagen",
            1,
            comentario
        )

        resultado["procesados"].append(codigo)

    guardar_datos(datos)

    return resultado
def aplicar_checks_estado(datos, filas_editadas, comentario="Marcaje manual con checks"):
    resultado = {
        "marcados": [],
        "desmarcados": [],
        "sin_cambios": [],
        "errores": []
    }

    for fila in filas_editadas:
        codigo = str(fila.get("ID", "")).strip().upper()
        tengo = bool(fila.get("Tengo", False))

        if not codigo:
            resultado["errores"].append("Fila sin código.")
            continue

        if codigo not in datos["cromos"]:
            resultado["errores"].append(f"{codigo}: no existe en la colección.")
            continue

        cantidad_actual = datos["cromos"][codigo]["cantidad"]

        if tengo:
            if cantidad_actual == 0:
                datos["cromos"][codigo]["cantidad"] = 1

                registrar_movimiento(
                    datos,
                    codigo,
                    "check_manual",
                    1,
                    comentario
                )

                resultado["marcados"].append(codigo)
            else:
                resultado["sin_cambios"].append(codigo)

        else:
            if cantidad_actual > 0:
                datos["cromos"][codigo]["cantidad"] = 0

                registrar_movimiento(
                    datos,
                    codigo,
                    "desmarcado_manual",
                    -cantidad_actual,
                    comentario
                )

                resultado["desmarcados"].append(codigo)
            else:
                resultado["sin_cambios"].append(codigo)

    guardar_datos(datos)

    return resultado

def obtener_entradas_por_lote(datos):
    movimientos = datos.get("movimientos", [])
    cromos = datos.get("cromos", {})

    filas = []

    for mov in movimientos:
        if mov.get("cantidad", 0) <= 0:
            continue

        cromo_id = mov.get("cromo_id", "")
        cromo = cromos.get(cromo_id, {})

        filas.append({
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
            "Comentario": mov.get("comentario", "")
        })

    filas = sorted(
        filas,
        key=lambda x: (
            x.get("Fecha/Hora", ""),
            x.get("Lote entrada", ""),
            x.get("ID", "")
        ),
        reverse=True
    )

    return filas

def crear_backup_manual(etiqueta="manual"):
    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)

    if not DATA_FILE.exists():
        raise FileNotFoundError("No existe data/coleccion.json para crear backup.")

    etiqueta_limpia = re.sub(r"[^A-ZÁÉÍÓÚÜÑa-záéíóúüñ0-9_-]+", "_", etiqueta).strip("_")

    if not etiqueta_limpia:
        etiqueta_limpia = "manual"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"coleccion_{timestamp}_{etiqueta_limpia}.json"

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        datos = json.load(f)

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    return str(backup_file)


def listar_backups():
    BACKUP_DIR.mkdir(exist_ok=True)

    backups = []

    for archivo in BACKUP_DIR.glob("*.json"):
        stat = archivo.stat()

        backups.append({
            "archivo": archivo.name,
            "ruta": str(archivo),
            "fecha_modificacion": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "tamano_kb": round(stat.st_size / 1024, 2)
        })

    backups = sorted(
        backups,
        key=lambda x: x["fecha_modificacion"],
        reverse=True
    )

    return backups


def restaurar_backup(nombre_archivo):
    BACKUP_DIR.mkdir(exist_ok=True)

    nombre_seguro = Path(nombre_archivo).name
    backup_file = BACKUP_DIR / nombre_seguro

    if not backup_file.exists():
        raise FileNotFoundError(f"No existe el backup {nombre_seguro}.")

    with open(backup_file, "r", encoding="utf-8") as f:
        datos = json.load(f)

    if "cromos" not in datos or "movimientos" not in datos:
        raise ValueError("El backup no tiene estructura válida de colección.")

    guardar_datos(datos)

    return len(datos["cromos"])
