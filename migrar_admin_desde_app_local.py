import json
import re
import tomllib
from datetime import datetime
from pathlib import Path

import psycopg


RUTA_JSON_APP_ANTERIOR = Path(
    r"C:\Users\usuario\Documents\agente-cromos-mundial-2026\data\coleccion.json"
)


def leer_secrets():
    ruta = Path(".streamlit") / "secrets.toml"

    if not ruta.exists():
        raise FileNotFoundError("No existe .streamlit/secrets.toml")

    with ruta.open("rb") as f:
        return tomllib.load(f)


def normalizar_codigo(codigo):
    codigo = str(codigo or "").strip().upper()
    codigo = codigo.replace(" ", "").replace("-", "")

    match = re.match(r"^([A-Z]+)(\d+)$", codigo)

    if match:
        prefijo = match.group(1)
        numero = match.group(2).zfill(2)
        return f"{prefijo}{numero}"

    return codigo


def resolver_codigo(codigo, ids_validos):
    codigo = normalizar_codigo(codigo)

    if codigo in ids_validos:
        return codigo

    if codigo.startswith("COD"):
        codigo_cdd = "CDD" + codigo[3:]

        if codigo_cdd in ids_validos:
            return codigo_cdd

    return codigo


def obtener_cantidad(valor):
    if isinstance(valor, int):
        return max(0, valor)

    if isinstance(valor, float):
        return max(0, int(valor))

    if not isinstance(valor, dict):
        return 0

    for clave in ["cantidad", "Cantidad", "qty", "unidades"]:
        if clave in valor:
            try:
                return max(0, int(valor.get(clave) or 0))
            except Exception:
                return 0

    for clave in ["tengo", "Tengo", "conseguido", "Conseguido"]:
        if clave in valor:
            return 1 if bool(valor.get(clave)) else 0

    estado = str(valor.get("estado", valor.get("Estado", ""))).strip().lower()

    if estado in ["tengo", "conseguido", "si", "sí", "true"]:
        return 1

    return 0


def extraer_cromos_json(datos_json):
    if isinstance(datos_json, dict) and "cromos" in datos_json:
        cromos = datos_json["cromos"]
    else:
        cromos = datos_json

    resultado = {}

    if isinstance(cromos, dict):
        for cromo_id, valor in cromos.items():
            codigo = normalizar_codigo(cromo_id)
            cantidad = obtener_cantidad(valor)

            if cantidad > 0:
                resultado[codigo] = cantidad

        return resultado

    if isinstance(cromos, list):
        for item in cromos:
            if not isinstance(item, dict):
                continue

            codigo = (
                item.get("id")
                or item.get("ID")
                or item.get("codigo")
                or item.get("Código")
                or item.get("cromo_id")
            )

            if not codigo:
                grupo = str(item.get("grupo", "")).strip().upper()
                numero = str(item.get("numero", "")).strip()

                if grupo and numero:
                    codigo = f"{grupo}{numero}"

            if not codigo:
                continue

            codigo = normalizar_codigo(codigo)
            cantidad = obtener_cantidad(item)

            if cantidad > 0:
                resultado[codigo] = cantidad

        return resultado

    raise TypeError("No reconozco el formato de data/coleccion.json")


def main():
    if not RUTA_JSON_APP_ANTERIOR.exists():
        raise FileNotFoundError(
            f"No encuentro el JSON anterior en: {RUTA_JSON_APP_ANTERIOR}"
        )

    secrets = leer_secrets()
    database_url = secrets["DATABASE_URL"]
    usuario_admin = secrets.get("APP_ADMIN_USER", "admin")

    print("Leyendo colección antigua...")
    with RUTA_JSON_APP_ANTERIOR.open("r", encoding="utf-8") as f:
        datos_json = json.load(f)

    cantidades_origen = extraer_cromos_json(datos_json)

    print(f"Cromos con cantidad > 0 en JSON antiguo: {len(cantidades_origen)}")
    print(f"Unidades totales en JSON antiguo: {sum(cantidades_origen.values())}")
    print(
        "Repetidas en JSON antiguo:",
        sum(max(0, cantidad - 1) for cantidad in cantidades_origen.values()),
    )

    print("Conectando con Neon...")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM usuarios
                WHERE LOWER(usuario) = LOWER(%s)
                """,
                (usuario_admin,),
            )

            row = cur.fetchone()

            if not row:
                raise ValueError(f"No existe el usuario admin: {usuario_admin}")

            usuario_id = row[0]

            cur.execute("SELECT id FROM cromos_base")
            ids_validos = {row[0] for row in cur.fetchall()}

            cantidades_finales = {}
            errores = []

            for codigo_origen, cantidad in cantidades_origen.items():
                codigo_resuelto = resolver_codigo(codigo_origen, ids_validos)

                if codigo_resuelto not in ids_validos:
                    errores.append(codigo_origen)
                    continue

                cantidades_finales[codigo_resuelto] = (
                    cantidades_finales.get(codigo_resuelto, 0) + cantidad
                )

            if errores:
                print("")
                print("Códigos no encontrados:")
                for codigo in errores:
                    print(f"- {codigo}")

                raise ValueError(
                    "Hay códigos del JSON antiguo que no existen en la plantilla. "
                    "Corrige esos códigos antes de migrar."
                )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            carpeta_backup = Path("backups_migracion")
            carpeta_backup.mkdir(exist_ok=True)

            cur.execute(
                """
                SELECT cromo_id, cantidad
                FROM coleccion_usuario
                WHERE usuario_id = %s
                ORDER BY cromo_id
                """,
                (usuario_id,),
            )

            estado_anterior = {
                row[0]: row[1]
                for row in cur.fetchall()
            }

            backup_path = carpeta_backup / f"admin_antes_migracion_{timestamp}.json"

            with backup_path.open("w", encoding="utf-8") as f:
                json.dump(
                    estado_anterior,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            print(f"Backup local creado: {backup_path}")

            lote_id = f"MIG_{timestamp}"

            print("Reseteando colección admin en Neon...")

            cur.execute(
                """
                UPDATE coleccion_usuario
                SET cantidad = 0,
                    actualizado_en = NOW()
                WHERE usuario_id = %s
                """,
                (usuario_id,),
            )

            print("Aplicando cantidades migradas...")

            for cromo_id, cantidad_final in cantidades_finales.items():
                cantidad_antes = estado_anterior.get(cromo_id, 0)
                diferencia = cantidad_final - cantidad_antes

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

                if diferencia != 0:
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
                            "migracion_app_local",
                            diferencia,
                            cantidad_antes,
                            cantidad_final,
                            "migrado",
                            "Migración desde data/coleccion.json de la app local anterior",
                        ),
                    )

            conn.commit()

    print("")
    print("Migración completada correctamente.")
    print("--------------------------------")
    print(f"Usuario migrado: {usuario_admin}")
    print(f"Cromos distintos migrados: {len(cantidades_finales)}")
    print(f"Unidades totales migradas: {sum(cantidades_finales.values())}")
    print(
        "Repetidas migradas:",
        sum(max(0, cantidad - 1) for cantidad in cantidades_finales.values()),
    )
    print("")
    print("Ahora entra en la app online con admin y revisa:")
    print("- Total conseguidos")
    print("- Repetidas")
    print("- Faltantes")
    print("- Movimientos")


if __name__ == "__main__":
    main()