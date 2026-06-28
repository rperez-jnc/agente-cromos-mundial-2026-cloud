import hashlib
import hmac
import secrets
from contextlib import contextmanager

import psycopg
import streamlit as st


def get_database_url():
    return st.secrets["DATABASE_URL"]


@contextmanager
def get_conn():
    conn = psycopg.connect(get_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()

    return f"pbkdf2_sha256${salt}${password_hash}"


def verificar_password(password: str, password_hash_guardado: str) -> bool:
    try:
        algoritmo, salt, password_hash = password_hash_guardado.split("$")

        if algoritmo != "pbkdf2_sha256":
            return False

        password_hash_calculado = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            200_000,
        ).hex()

        return hmac.compare_digest(password_hash_calculado, password_hash)

    except Exception:
        return False


def autenticar_usuario(usuario: str, password: str):
    usuario = usuario.strip().lower()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, usuario, nombre, password_hash, activo, es_admin
                FROM usuarios
                WHERE LOWER(usuario) = %s
                """,
                (usuario,),
            )

            row = cur.fetchone()

    if not row:
        return None

    usuario_id, usuario_db, nombre, password_hash_guardado, activo, es_admin = row

    if not activo:
        return None

    if not verificar_password(password, password_hash_guardado):
        return None

    return {
        "id": usuario_id,
        "usuario": usuario_db,
        "nombre": nombre,
        "es_admin": es_admin,
    }


def crear_usuario(usuario: str, nombre: str, password: str, es_admin: bool = False):
    usuario = usuario.strip().lower()
    nombre = nombre.strip()

    if not usuario:
        raise ValueError("El usuario no puede estar vacío.")

    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")

    if not password:
        raise ValueError("La contraseña no puede estar vacía.")

    password_hash = hash_password(password)

    with get_conn() as conn:
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
                VALUES (%s, %s, %s, TRUE, %s)
                ON CONFLICT (usuario) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    password_hash = EXCLUDED.password_hash,
                    activo = TRUE,
                    es_admin = EXCLUDED.es_admin
                RETURNING id
                """,
                (usuario, nombre, password_hash, es_admin),
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

    return usuario_id


def listar_usuarios():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, usuario, nombre, activo, es_admin, creado_en
                FROM usuarios
                ORDER BY id
                """
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "usuario": row[1],
            "nombre": row[2],
            "activo": row[3],
            "es_admin": row[4],
            "creado_en": row[5],
        }
        for row in rows
    ]


def obtener_resumen_usuario(usuario_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE cantidad > 0) AS conseguidos,
                    COUNT(*) FILTER (WHERE cantidad = 0) AS faltantes,
                    COALESCE(SUM(GREATEST(cantidad - 1, 0)), 0) AS repetidas
                FROM coleccion_usuario
                WHERE usuario_id = %s
                """,
                (usuario_id,),
            )

            total, conseguidos, faltantes, repetidas = cur.fetchone()

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