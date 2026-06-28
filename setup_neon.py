import hashlib
import os
import secrets
import tomllib
from pathlib import Path

import psycopg

from collection_template import generar_cromos_mundial_2026


SECRETS_FILE = Path(".streamlit") / "secrets.toml"


def cargar_secrets():
    if not SECRETS_FILE.exists():
        raise FileNotFoundError("No existe .streamlit/secrets.toml")

    with open(SECRETS_FILE, "rb") as f:
        return tomllib.load(f)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()

    return f"pbkdf2_sha256${salt}${password_hash}"


def obtener_cromo_id(cromo):
    cromo_id = (
        cromo.get("id")
        or cromo.get("codigo")
        or cromo.get("cromo_id")
        or cromo.get("ID")
    )

    if cromo_id:
        return str(cromo_id).strip().upper()

    grupo = str(cromo.get("grupo", "")).strip().upper()
    numero = str(cromo.get("numero", "")).strip()

    if numero.isdigit():
        numero = numero.zfill(2)

    if not grupo or not numero:
        raise ValueError(f"No se puede calcular el ID del cromo: {cromo}")

    return f"{grupo}{numero}"


def iterar_cromos_generados(cromos):
    if isinstance(cromos, dict):
        for cromo_id, cromo in cromos.items():
            yield cromo_id, cromo
        return

    if isinstance(cromos, list):
        for cromo in cromos:
            if not isinstance(cromo, dict):
                raise TypeError(f"Elemento de cromos no válido: {cromo}")

            cromo_id = obtener_cromo_id(cromo)
            yield cromo_id, cromo
        return

    raise TypeError(f"Formato de cromos no válido: {type(cromos)}")


def insertar_cromos_base(conn):
    cromos = generar_cromos_mundial_2026()
    total = 0

    with conn.cursor() as cur:
        for cromo_id, cromo in iterar_cromos_generados(cromos):
            cur.execute(
                """
                INSERT INTO cromos_base (
                    id,
                    seccion,
                    grupo,
                    numero,
                    nombre,
                    tipo,
                    orden_album
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    seccion = EXCLUDED.seccion,
                    grupo = EXCLUDED.grupo,
                    numero = EXCLUDED.numero,
                    nombre = EXCLUDED.nombre,
                    tipo = EXCLUDED.tipo,
                    orden_album = EXCLUDED.orden_album
                """,
                (
                    cromo_id,
                    cromo.get("seccion", ""),
                    cromo.get("grupo", ""),
                    str(cromo.get("numero", "")),
                    cromo.get("nombre", ""),
                    cromo.get("tipo", "Normal"),
                    int(cromo.get("orden_album", cromo.get("orden", 0))),
                ),
            )

            total += 1

    print(f"Cromos base cargados: {total}")
def crear_usuario_admin(conn, usuario, password):
    password_hash = hash_password(password)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO usuarios (
                usuario,
                nombre,
                password_hash,
                activo,
                es_admin
            )
            VALUES (%s, %s, %s, TRUE, TRUE)
            ON CONFLICT (usuario) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                activo = TRUE,
                es_admin = TRUE
            RETURNING id
            """,
            (
                usuario,
                "Administrador",
                password_hash,
            ),
        )

        usuario_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO coleccion_usuario (
                usuario_id,
                cromo_id,
                cantidad
            )
            SELECT %s, id, 0
            FROM cromos_base
            ON CONFLICT (usuario_id, cromo_id) DO NOTHING
            """,
            (usuario_id,),
        )

    print(f"Usuario admin creado/actualizado: {usuario}")
    print(f"ID usuario admin: {usuario_id}")


def comprobar_resultado(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM cromos_base")
        total_cromos = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM usuarios")
        total_usuarios = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM coleccion_usuario")
        total_coleccion = cur.fetchone()[0]

    print("")
    print("Resumen Neon")
    print("------------")
    print(f"Cromos base: {total_cromos}")
    print(f"Usuarios: {total_usuarios}")
    print(f"Registros colección usuario: {total_coleccion}")


def main():
    secrets_data = cargar_secrets()

    database_url = secrets_data["DATABASE_URL"]
    admin_user = secrets_data.get("APP_ADMIN_USER", "admin")
    admin_password = secrets_data.get("APP_ADMIN_PASSWORD", "")

    if not admin_password:
        raise ValueError("APP_ADMIN_PASSWORD está vacío en secrets.toml")

    print("Conectando con Neon...")

    with psycopg.connect(database_url) as conn:
        insertar_cromos_base(conn)
        crear_usuario_admin(conn, admin_user, admin_password)
        conn.commit()
        comprobar_resultado(conn)

    print("")
    print("Setup completado correctamente.")


if __name__ == "__main__":
    main()