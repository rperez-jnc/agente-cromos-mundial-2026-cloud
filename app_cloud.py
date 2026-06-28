from io import BytesIO

import pandas as pd
import streamlit as st

from auth_cloud import exigir_login_cloud
from db_cloud import crear_usuario, listar_usuarios
from data_manager_cloud import (
    aplicar_checks_estado_usuario,
    aplicar_entrega_repetidas_lote,
    aplicar_intercambio_lote,
    aplicar_lote_cromos,
    cargar_datos_usuario,
    cambiar_cantidad,
    inicializar_coleccion_usuario_desde_lote,
    listar_faltantes,
    listar_movimientos,
    listar_repetidas,
    listar_todos,
    obtener_entradas_por_lote,
    obtener_resumen,
    resolver_codigo_en_coleccion,
)

from ui_style import aplicar_estilo, render_header


def dataframe_excel_bytes(hojas):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for nombre_hoja, filas in hojas.items():
            df = pd.DataFrame(filas)
            df.to_excel(writer, sheet_name=nombre_hoja[:31], index=False)

    output.seek(0)
    return output.getvalue()


st.set_page_config(
    page_title="Agente Cromos Mundial 2026",
    page_icon="⚽",
    layout="wide",
)
def generar_faltantes_txt(faltantes, usuario):
    lineas = []
    lineas.append("LISTADO DE CROMOS FALTANTES")
    lineas.append(f"Usuario: {usuario}")
    lineas.append("=" * 40)
    lineas.append("")

    if not faltantes:
        lineas.append("No tienes cromos faltantes.")
        return "\n".join(lineas)

    grupo_actual = None

    for fila in faltantes:
        grupo = f"{fila.get('Sección', '')} - {fila.get('Grupo', '')}"

        if grupo != grupo_actual:
            grupo_actual = grupo
            lineas.append("")
            lineas.append(grupo)
            lineas.append("-" * len(grupo))

        lineas.append(
            f"{fila.get('ID', '')} | "
            f"{fila.get('Nombre', '')} | "
            f"Tipo: {fila.get('Tipo', '')}"
        )

    return "\n".join(lineas)


def generar_repetidas_txt(repetidas, usuario):
    lineas = []
    lineas.append("LISTADO DE CROMOS REPETIDOS")
    lineas.append(f"Usuario: {usuario}")
    lineas.append("=" * 40)
    lineas.append("")

    if not repetidas:
        lineas.append("No tienes cromos repetidos.")
        return "\n".join(lineas)

    grupo_actual = None

    for fila in repetidas:
        grupo = f"{fila.get('Sección', '')} - {fila.get('Grupo', '')}"

        if grupo != grupo_actual:
            grupo_actual = grupo
            lineas.append("")
            lineas.append(grupo)
            lineas.append("-" * len(grupo))

        lineas.append(
            f"{fila.get('ID', '')} | "
            f"{fila.get('Nombre', '')} | "
            f"Cantidad total: {fila.get('Cantidad', '')} | "
            f"Repetidas: {fila.get('Repetidas', '')}"
        )

    return "\n".join(lineas)


def generar_lista_compacta_faltantes(faltantes):
    if not faltantes:
        return "No tengo cromos faltantes."

    codigos = [fila["ID"] for fila in faltantes]
    return ", ".join(codigos)


def generar_lista_compacta_repetidas(repetidas):
    if not repetidas:
        return "No tengo cromos repetidos."

    partes = []

    for fila in repetidas:
        partes.append(f"{fila['ID']} x{fila['Repetidas']}")

    return ", ".join(partes)

aplicar_estilo()

usuario_actual = exigir_login_cloud()

render_header()

datos = cargar_datos_usuario(usuario_actual["id"])
resumen = obtener_resumen(datos)

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total cromos", resumen["total"])
col2.metric("Conseguidos", resumen["conseguidos"])
col3.metric("Faltantes", resumen["faltantes"])
col4.metric("Repetidas", resumen["repetidas"])
col5.metric("% completado", f'{resumen["porcentaje"]}%')

st.divider()

st.subheader("Modo rápido móvil")

codigo_movil_input = st.text_input(
    "Código del cromo",
    placeholder="Ejemplo: ESP1, ARG09, BRA10, COD12",
    key="codigo_movil_input_cloud",
)

codigo_movil = resolver_codigo_en_coleccion(datos, codigo_movil_input)

if codigo_movil_input.strip():
    if codigo_movil not in datos["cromos"]:
        st.error(f"El código {codigo_movil_input.strip().upper()} no existe.")
    else:
        cromo_movil = datos["cromos"][codigo_movil]
        cantidad_movil = cromo_movil["cantidad"]
        repetidas_movil = max(0, cantidad_movil - 1)
        estado_movil = "Falta" if cantidad_movil == 0 else "Conseguido"

        st.info(
            f"{codigo_movil} | "
            f"{cromo_movil['seccion']} | "
            f"{cromo_movil['nombre']} | "
            f"Estado: {estado_movil} | "
            f"Cantidad: {cantidad_movil} | "
            f"Repetidas: {repetidas_movil}"
        )

        col_movil_1, col_movil_2, col_movil_3 = st.columns(3)

        with col_movil_1:
            if st.button("Añadir conseguido", use_container_width=True):
                cambiar_cantidad(
                    datos,
                    codigo_movil,
                    1,
                    "Cromo añadido desde modo rápido móvil",
                )
                st.success(f"{codigo_movil} añadido correctamente.")
                st.rerun()

        with col_movil_2:
            if st.button("Entregar repetida", use_container_width=True):
                if cantidad_movil <= 1:
                    st.error("No tienes repetida de este cromo.")
                else:
                    cambiar_cantidad(
                        datos,
                        codigo_movil,
                        -1,
                        "Repetida entregada desde modo rápido móvil",
                    )
                    st.success(f"Repetida de {codigo_movil} descontada.")
                    st.rerun()

        with col_movil_3:
            if st.button("Quitar unidad", use_container_width=True):
                if cantidad_movil <= 0:
                    st.error("No puedes bajar de 0.")
                else:
                    cambiar_cantidad(
                        datos,
                        codigo_movil,
                        -1,
                        "Corrección desde modo rápido móvil",
                    )
                    st.success(f"{codigo_movil} corregido.")
                    st.rerun()

st.divider()

st.subheader("Modo intercambio")

with st.expander("Registrar intercambio de cromos"):
    col_int_1, col_int_2 = st.columns(2)

    with col_int_1:
        texto_recibo = st.text_area(
            "Cromos que recibo",
            placeholder="Ejemplo: ESP1, ARG09, BRA10",
            height=120,
            key="intercambio_recibo_cloud",
        )

    with col_int_2:
        texto_entrego = st.text_area(
            "Repetidas que entrego",
            placeholder="Ejemplo: POR5, JPN03, COD12",
            height=120,
            key="intercambio_entrego_cloud",
        )

    confirmar_intercambio = st.checkbox(
        "Confirmo que quiero aplicar este intercambio",
        key="confirmar_intercambio_cloud",
    )

    if st.button("Aplicar intercambio", use_container_width=True):
        if not confirmar_intercambio:
            st.error("Marca primero la casilla de confirmación.")
        else:
            resultado = aplicar_intercambio_lote(
                datos,
                texto_recibo,
                texto_entrego,
                "Intercambio registrado desde la app cloud",
            )

            if resultado["errores"]:
                st.error("No se ha aplicado el intercambio porque hay errores.")
                for error in resultado["errores"]:
                    st.warning(error)
            else:
                st.success(
                    f"Intercambio aplicado. "
                    f"Lote: {resultado['lote_id']}. "
                    f"Recibidos: {len(resultado['recibidos'])}. "
                    f"Nuevos: {len(resultado['recibidos_nuevos'])}. "
                    f"Repetidos recibidos: {len(resultado['recibidos_repetidos'])}. "
                    f"Entregados: {len(resultado['entregados'])}."
                )
                st.rerun()

st.divider()
st.divider()
st.divider()

st.subheader("Inicializar mi colección con checks")

with st.expander("Marcar manualmente los cromos que ya tengo"):
    st.warning(
        "Esta sección está pensada para cargar tu colección inicial. "
        "Puedes marcar los cromos que tienes usando checks. "
        "Si desmarcas un cromo, su cantidad quedará a 0."
    )

    filas_check = []

    for fila in listar_todos(datos):
        filas_check.append(
            {
                "Tengo": fila["Cantidad"] > 0,
                "ID": fila["ID"],
                "Sección": fila["Sección"],
                "Grupo": fila["Grupo"],
                "Número": fila["Número"],
                "Nombre": fila["Nombre"],
                "Tipo": fila["Tipo"],
                "Cantidad actual": fila["Cantidad"],
                "Repetidas": fila["Repetidas"],
                "Orden álbum": fila["Orden álbum"],
            }
        )

    df_checks = pd.DataFrame(filas_check)

    col_filtro_1, col_filtro_2, col_filtro_3 = st.columns(3)

    with col_filtro_1:
        grupos_disponibles = ["Todos"] + sorted(df_checks["Grupo"].dropna().unique().tolist())
        filtro_grupo_checks = st.selectbox(
            "Grupo",
            grupos_disponibles,
            key="filtro_grupo_checks_cloud",
        )

    with col_filtro_2:
        secciones_disponibles = ["Todas"] + sorted(df_checks["Sección"].dropna().unique().tolist())
        filtro_seccion_checks = st.selectbox(
            "Sección",
            secciones_disponibles,
            key="filtro_seccion_checks_cloud",
        )

    with col_filtro_3:
        filtro_texto_checks = st.text_input(
            "Buscar",
            placeholder="ESP, Argentina, FWC, Coca-Cola...",
            key="filtro_texto_checks_cloud",
        )

    df_visible = df_checks.copy()

    if filtro_grupo_checks != "Todos":
        df_visible = df_visible[df_visible["Grupo"] == filtro_grupo_checks]

    if filtro_seccion_checks != "Todas":
        df_visible = df_visible[df_visible["Sección"] == filtro_seccion_checks]

    if filtro_texto_checks.strip():
        texto = filtro_texto_checks.strip().lower()

        df_visible = df_visible[
            df_visible["ID"].astype(str).str.lower().str.contains(texto)
            | df_visible["Sección"].astype(str).str.lower().str.contains(texto)
            | df_visible["Grupo"].astype(str).str.lower().str.contains(texto)
            | df_visible["Nombre"].astype(str).str.lower().str.contains(texto)
        ]

    st.caption(
        f"Cromos visibles: {len(df_visible)}. "
        "Marca o desmarca la columna Tengo y pulsa Guardar checks visibles."
    )

    df_editado = st.data_editor(
        df_visible,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Tengo": st.column_config.CheckboxColumn(
                "Tengo",
                help="Marca si tienes este cromo",
                default=False,
            )
        },
        disabled=[
            "ID",
            "Sección",
            "Grupo",
            "Número",
            "Nombre",
            "Tipo",
            "Cantidad actual",
            "Repetidas",
            "Orden álbum",
        ],
        key="editor_checks_inicial_cloud",
    )

    col_check_1, col_check_2, col_check_3 = st.columns(3)

    with col_check_1:
        if st.button("Guardar checks visibles", use_container_width=True):
            resultado = aplicar_checks_estado_usuario(
                datos,
                df_editado.to_dict("records"),
                "Marcaje inicial con checks",
            )

            if resultado["errores"]:
                st.error("No se han guardado los checks por errores.")
                for error in resultado["errores"]:
                    st.warning(error)
            else:
                st.success(
                    f"Checks guardados. "
                    f"Procesados: {len(resultado['procesados'])}. "
                    f"Marcados: {len(resultado['marcados'])}. "
                    f"Desmarcados: {len(resultado['desmarcados'])}. "
                    f"Sin cambios: {resultado['sin_cambios']}."
                )
                st.rerun()

    with col_check_2:
        if st.button("Marcar todos los visibles", use_container_width=True):
            filas_marcar = df_visible.copy()
            filas_marcar["Tengo"] = True

            resultado = aplicar_checks_estado_usuario(
                datos,
                filas_marcar.to_dict("records"),
                "Marcaje masivo visible con checks",
            )

            if resultado["errores"]:
                st.error("No se han marcado los visibles por errores.")
                for error in resultado["errores"]:
                    st.warning(error)
            else:
                st.success(
                    f"Visibles marcados. "
                    f"Procesados: {len(resultado['procesados'])}."
                )
                st.rerun()

    with col_check_3:
        if st.button("Desmarcar todos los visibles", use_container_width=True):
            filas_desmarcar = df_visible.copy()
            filas_desmarcar["Tengo"] = False

            resultado = aplicar_checks_estado_usuario(
                datos,
                filas_desmarcar.to_dict("records"),
                "Desmarcaje masivo visible con checks",
            )

            if resultado["errores"]:
                st.error("No se han desmarcado los visibles por errores.")
                for error in resultado["errores"]:
                    st.warning(error)
            else:
                st.success(
                    f"Visibles desmarcados. "
                    f"Procesados: {len(resultado['procesados'])}."
                )
                st.rerun()

st.subheader("Actualizar muchos cromos a la vez")

with st.expander("Entrada por lote"):
    texto_lote = st.text_area(
        "Códigos que he conseguido",
        placeholder="ESP1, ESP2, ARG09, BRA10",
        height=120,
        key="texto_lote_recibidos_cloud",
    )

    if st.button("Marcar todos como conseguidos", use_container_width=True):
        resultado = aplicar_lote_cromos(
            datos,
            texto_lote,
            1,
            "Lote añadido desde app cloud",
        )

        if resultado["errores"]:
            st.warning("Hay incidencias:")
            for error in resultado["errores"]:
                st.write(error)

        st.success(
            f"Lote aplicado. Procesados: {len(resultado['procesados'])}. "
            f"Nuevos: {len(resultado['nuevos'])}. "
            f"Repetidos: {len(resultado['repetidos'])}."
        )
        st.rerun()

with st.expander("Entrega de repetidas por lote"):
    texto_entrega = st.text_area(
        "Códigos repetidos que entrego",
        placeholder="ESP1, ESP2, ARG09",
        height=120,
        key="texto_lote_entrega_cloud",
    )

    if st.button("Entregar repetidas en lote", use_container_width=True):
        resultado = aplicar_entrega_repetidas_lote(
            datos,
            texto_entrega,
            "Repetidas entregadas desde app cloud",
        )

        if resultado["errores"]:
            st.error("No se ha aplicado la entrega por errores:")
            for error in resultado["errores"]:
                st.warning(error)
        else:
            st.success(
                f"Entrega aplicada. Lote: {resultado['lote_id']}. "
                f"Procesados: {len(resultado['procesados'])}."
            )
            st.rerun()

st.divider()

st.subheader("Búsqueda rápida")

texto_busqueda = st.text_input(
    "Buscar por código, selección, grupo o nombre",
    placeholder="ESP, Argentina, FWC, Coca-Cola...",
    key="busqueda_cloud",
)

todos = listar_todos(datos)

if texto_busqueda.strip():
    t = texto_busqueda.strip().lower()

    filtrados = [
        fila
        for fila in todos
        if t in str(fila["ID"]).lower()
        or t in str(fila["Sección"]).lower()
        or t in str(fila["Grupo"]).lower()
        or t in str(fila["Nombre"]).lower()
    ]

    st.dataframe(pd.DataFrame(filtrados[:100]), use_container_width=True)

st.divider()

tab_todos, tab_faltantes, tab_repetidas, tab_movimientos, tab_entradas = st.tabs(
    ["Todos", "Faltantes", "Repetidas", "Movimientos", "Entradas por lote"]
)

with tab_todos:
    st.dataframe(pd.DataFrame(todos), use_container_width=True)

with tab_faltantes:
    st.dataframe(pd.DataFrame(listar_faltantes(datos)), use_container_width=True)

with tab_repetidas:
    st.dataframe(pd.DataFrame(listar_repetidas(datos)), use_container_width=True)

with tab_movimientos:
    st.dataframe(pd.DataFrame(listar_movimientos(datos)), use_container_width=True)

with tab_entradas:
    st.dataframe(pd.DataFrame(obtener_entradas_por_lote(datos)), use_container_width=True)

st.divider()

st.subheader("Informes")

faltantes = listar_faltantes(datos)
repetidas = listar_repetidas(datos)
movimientos = listar_movimientos(datos)
entradas = obtener_entradas_por_lote(datos)

st.caption(
    "Descarga listados separados para compartir o revisar rápidamente tus cromos faltantes y repetidos."
)

col_inf_1, col_inf_2 = st.columns(2)

with col_inf_1:
    st.markdown("### Cromos faltantes")

    st.metric("Total faltantes", len(faltantes))

    faltantes_txt = generar_faltantes_txt(
        faltantes,
        usuario_actual["usuario"],
    )

    st.download_button(
        "Descargar faltantes TXT",
        data=faltantes_txt.encode("utf-8"),
        file_name=f"cromos_faltantes_{usuario_actual['usuario']}.txt",
        mime="text/plain",
        use_container_width=True,
    )

    faltantes_excel = dataframe_excel_bytes(
        {
            "Faltantes": faltantes,
        }
    )

    st.download_button(
        "Descargar faltantes Excel",
        data=faltantes_excel,
        file_name=f"cromos_faltantes_{usuario_actual['usuario']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    with st.expander("Lista compacta de faltantes"):
        st.code(generar_lista_compacta_faltantes(faltantes))

with col_inf_2:
    st.markdown("### Cromos repetidos")

    st.metric("Total repetidas", sum(fila["Repetidas"] for fila in repetidas))

    repetidas_txt = generar_repetidas_txt(
        repetidas,
        usuario_actual["usuario"],
    )

    st.download_button(
        "Descargar repetidas TXT",
        data=repetidas_txt.encode("utf-8"),
        file_name=f"cromos_repetidos_{usuario_actual['usuario']}.txt",
        mime="text/plain",
        use_container_width=True,
    )

    repetidas_excel = dataframe_excel_bytes(
        {
            "Repetidas": repetidas,
        }
    )

    st.download_button(
        "Descargar repetidas Excel",
        data=repetidas_excel,
        file_name=f"cromos_repetidos_{usuario_actual['usuario']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    with st.expander("Lista compacta de repetidas"):
        st.code(generar_lista_compacta_repetidas(repetidas))

st.divider()

st.markdown("### Informe completo")

excel_bytes = dataframe_excel_bytes(
    {
        "Resumen": [resumen],
        "Todos": todos,
        "Faltantes": faltantes,
        "Repetidas": repetidas,
        "Movimientos": movimientos,
        "Entradas": entradas,
    }
)

st.download_button(
    "Descargar Excel completo",
    data=excel_bytes,
    file_name=f"coleccion_cromos_{usuario_actual['usuario']}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)

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