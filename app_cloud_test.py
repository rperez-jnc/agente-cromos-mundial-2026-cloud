import pandas as pd
import streamlit as st

from auth_cloud import exigir_login_cloud
from db_cloud import crear_usuario, listar_usuarios, obtener_resumen_usuario
from ui_style import aplicar_estilo, render_header

from data_manager_cloud import (
    aplicar_lote_cromos,
    cargar_datos_usuario,
    cambiar_cantidad,
    listar_faltantes,
    listar_repetidas,
    obtener_resumen,
    resolver_codigo_en_coleccion,
)


st.set_page_config(
    page_title="Agente Cromos Mundial 2026 Cloud",
    page_icon="⚽",
    layout="wide",
)

aplicar_estilo()

usuario_actual = exigir_login_cloud()

render_header()

st.subheader("Prueba de conexión multiusuario")

datos = cargar_datos_usuario(usuario_actual["id"])
resumen = obtener_resumen(datos)

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total cromos", resumen["total"])
col2.metric("Conseguidos", resumen["conseguidos"])
col3.metric("Faltantes", resumen["faltantes"])
col4.metric("Repetidas", resumen["repetidas"])
col5.metric("% completado", f'{resumen["porcentaje"]}%')

st.info(
    "Esta pantalla solo sirve para probar que el login multiusuario y Neon funcionan. "
    "Todavía no es la app completa de cromos."
)

st.divider()

st.subheader("Prueba rápida de colección")

codigo_prueba = st.text_input(
    "Código de cromo",
    placeholder="Ejemplo: ESP1, ESP01, ARG09, COD12",
    key="codigo_prueba_cloud",
)

codigo_resuelto = resolver_codigo_en_coleccion(datos, codigo_prueba)

if codigo_prueba.strip():
    if codigo_resuelto not in datos["cromos"]:
        st.error("Ese cromo no existe.")
    else:
        cromo = datos["cromos"][codigo_resuelto]

        st.info(
            f"{codigo_resuelto} | {cromo['seccion']} | {cromo['nombre']} | "
            f"Cantidad actual: {cromo['cantidad']}"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("Añadir cromo", use_container_width=True):
                cambiar_cantidad(
                    datos,
                    codigo_resuelto,
                    1,
                    "Prueba desde app cloud",
                )
                st.success("Cromo añadido.")
                st.rerun()

        with col_b:
            if st.button("Quitar cromo", use_container_width=True):
                try:
                    cambiar_cantidad(
                        datos,
                        codigo_resuelto,
                        -1,
                        "Corrección desde app cloud",
                    )
                    st.success("Cromo quitado.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

st.divider()

st.subheader("Prueba por lote")

texto_lote = st.text_area(
    "Códigos recibidos",
    placeholder="ESP1, ESP2, ARG09",
    key="texto_lote_cloud",
)

if st.button("Añadir lote de cromos", use_container_width=True):
    resultado = aplicar_lote_cromos(
        datos,
        texto_lote,
        1,
        "Lote de prueba desde app cloud",
    )

    if resultado["errores"]:
        st.warning("Hay incidencias en el lote.")
        for error in resultado["errores"]:
            st.write(error)

    st.success(
        f"Lote aplicado. Procesados: {len(resultado['procesados'])}. "
        f"Nuevos: {len(resultado['nuevos'])}. "
        f"Repetidos: {len(resultado['repetidos'])}."
    )

    st.rerun()

col_f, col_r = st.columns(2)

with col_f:
    with st.expander("Ver primeros faltantes"):
        st.dataframe(listar_faltantes(datos)[:50], use_container_width=True)

with col_r:
    with st.expander("Ver repetidas"):
        st.dataframe(listar_repetidas(datos), use_container_width=True)
if usuario_actual["es_admin"]:
    st.divider()

    st.subheader("Administración de usuarios")

    with st.expander("Crear o actualizar usuario"):
        nuevo_usuario = st.text_input("Usuario nuevo", placeholder="amigo1")
        nuevo_nombre = st.text_input("Nombre", placeholder="Nombre del amigo")
        nueva_password = st.text_input("Contraseña", type="password")
        nuevo_es_admin = st.checkbox("Es administrador")

        if st.button("Crear / actualizar usuario", use_container_width=True):
            try:
                usuario_id = crear_usuario(
                    nuevo_usuario,
                    nuevo_nombre,
                    nueva_password,
                    nuevo_es_admin,
                )

                st.success(f"Usuario creado/actualizado correctamente. ID: {usuario_id}")
                st.rerun()

            except Exception as e:
                st.error(f"Error creando usuario: {e}")

    usuarios = listar_usuarios()

    if usuarios:
        st.markdown("### Usuarios existentes")
        st.dataframe(pd.DataFrame(usuarios), use_container_width=True)