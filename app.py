import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, date
from auth import exigir_login
from ui_style import aplicar_estilo, render_header


from data_manager import (
    cargar_datos,
    cambiar_cantidad,
    obtener_resumen,
    listar_faltantes,
    listar_repetidas,
    inicializar_coleccion_mundial_2026,
    aplicar_lote_cromos,
    marcar_como_tengo_lote,
    normalizar_codigos_lote,
    aplicar_checks_estado,
    resolver_codigo_en_coleccion,
    obtener_entradas_por_lote,
    crear_backup_manual,
    listar_backups,
    restaurar_backup,
)

from reports import (
    generar_resumen_txt,
    generar_faltantes_txt,
    generar_repetidas_txt,
    guardar_txt,
    generar_excel_bytes,
    guardar_excel,
    generar_entradas_lotes_txt,
    generar_entradas_lotes_excel_bytes,
)

from image_detector import detectar_cromos_naranja_desde_imagen

def convertir_dataframe_a_excel_bytes(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="EntradasFiltradas", index=False)

    output.seek(0)
    return output.getvalue()


def texto_a_fecha(valor):
    try:
        return datetime.strptime(valor[:10], "%Y-%m-%d").date()
    except Exception:
        return None

st.set_page_config(
    page_title="Agente Cromos Mundial 2026",
    page_icon="⚽",
    layout="wide"
)

aplicar_estilo()
exigir_login()
render_header()

st.title("Agente Cromos Mundial 2026")

with st.expander("Configuración de colección"):
    st.warning(
        "Inicializar la colección sustituirá los cromos actuales por la plantilla completa del Mundial 2026."
    )

    confirmar_inicializacion = st.checkbox(
        "Confirmo que quiero inicializar la colección completa"
    )

    if st.button("Inicializar colección Mundial 2026 desde plantilla"):
        if not confirmar_inicializacion:
            st.error("Marca primero la casilla de confirmación.")
        else:
            total_cromos = inicializar_coleccion_mundial_2026()
            st.success(f"Colección inicializada correctamente con {total_cromos} cromos.")
            st.rerun()

    st.markdown("### Copias de seguridad")

    col_backup_1, col_backup_2 = st.columns(2)

    with col_backup_1:
        etiqueta_backup = st.text_input(
            "Etiqueta del backup",
            value="manual",
            key="etiqueta_backup"
        )

        if st.button("Crear copia de seguridad ahora"):
            try:
                ruta_backup = crear_backup_manual(etiqueta_backup)
                st.success(f"Copia creada correctamente: {ruta_backup}")
            except Exception as e:
                st.error(f"No se pudo crear la copia: {e}")

    with col_backup_2:
        backups = listar_backups()

        if not backups:
            st.info("Todavía no hay copias de seguridad.")
        else:
            opciones_backup = [backup["archivo"] for backup in backups]

            backup_seleccionado = st.selectbox(
                "Backup para restaurar",
                opciones_backup,
                key="backup_seleccionado"
            )

            confirmar_restore = st.checkbox(
                "Confirmo que quiero restaurar este backup",
                key="confirmar_restore"
            )

            if st.button("Restaurar backup seleccionado"):
                if not confirmar_restore:
                    st.error("Marca primero la casilla de confirmación.")
                else:
                    try:
                        total_restaurado = restaurar_backup(backup_seleccionado)
                        st.success(
                            f"Backup restaurado correctamente. Cromos cargados: {total_restaurado}"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo restaurar el backup: {e}")

    backups_actuales = listar_backups()

    if backups_actuales:
        st.markdown("#### Backups disponibles")
        st.dataframe(
            pd.DataFrame(backups_actuales),
            use_container_width=True,
            hide_index=True
        )
datos = cargar_datos()
resumen = obtener_resumen(datos)
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total cromos", resumen["total"])
col2.metric("Conseguidos", resumen["conseguidos"])
col3.metric("Faltantes", resumen["faltantes"])
col4.metric("Repetidas", resumen["repetidas"])
col5.metric("% completado", f'{resumen["porcentaje"]}%')

mensaje_lote = st.session_state.pop("mensaje_lote", None)
errores_lote = st.session_state.pop("errores_lote", [])

if mensaje_lote:
    st.success(mensaje_lote)

if errores_lote:
    with st.expander("Ver incidencias del lote"):
        for error in errores_lote:
            st.warning(error)

st.divider()

st.subheader("Modo rápido móvil")

st.caption(
    "Pensado para usar desde el móvil durante intercambios. "
    "Acepta códigos como ESP1, ESP01, ARG9, COD12."
)

codigo_movil_input = st.text_input(
    "Código del cromo",
    placeholder="Ejemplo: ESP1, ARG09, BRA10, COD12",
    key="codigo_movil_input"
)

codigo_movil = resolver_codigo_en_coleccion(datos, codigo_movil_input)

if codigo_movil_input.strip():
    if codigo_movil not in datos["cromos"]:
        st.error(f"El código {codigo_movil_input.strip().upper()} no existe en la colección.")
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
            if st.button("Añadir conseguido", use_container_width=True, key="movil_add"):
                cambiar_cantidad(
                    datos,
                    codigo_movil,
                    1,
                    "Cromo añadido desde modo rápido móvil"
                )
                st.success(f"{codigo_movil} añadido correctamente.")
                st.rerun()

        with col_movil_2:
            if st.button("Entregar repetida", use_container_width=True, key="movil_repetida"):
                if cantidad_movil <= 1:
                    st.error("No tienes repetida de este cromo.")
                else:
                    cambiar_cantidad(
                        datos,
                        codigo_movil,
                        -1,
                        "Repetida entregada desde modo rápido móvil"
                    )
                    st.success(f"Repetida de {codigo_movil} descontada.")
                    st.rerun()

        with col_movil_3:
            if st.button("Quitar unidad", use_container_width=True, key="movil_quitar"):
                if cantidad_movil <= 0:
                    st.error("No puedes bajar de 0.")
                else:
                    cambiar_cantidad(
                        datos,
                        codigo_movil,
                        -1,
                        "Corrección desde modo rápido móvil"
                    )
                    st.success(f"{codigo_movil} corregido.")
                    st.rerun()



st.divider()

st.subheader("Actualizar muchos cromos a la vez")

with st.expander("Pegar lista de cromos"):
    texto_lote = st.text_area(
        "Códigos de cromos",
        placeholder="ESP01, ESP02, ARG05, BRA10\nTambién puedes pegarlos en varias líneas.",
        height=140
    )

    col_lote_1, col_lote_2 = st.columns(2)

    with col_lote_1:
        if st.button("Marcar todos como conseguidos"):
            resultado = aplicar_lote_cromos(
                datos,
                texto_lote,
                1,
                "Cromos conseguidos por lote"
            )

            st.session_state["mensaje_lote"] = (
                f"Cromos marcados como conseguidos: {len(resultado['procesados'])}"
            )
            st.session_state["errores_lote"] = resultado["errores"]
            st.rerun()

    with col_lote_2:
        if st.button("Entregar repetidas en lote"):
            resultado = aplicar_lote_cromos(
                datos,
                texto_lote,
                -1,
                "Repetidas entregadas por lote"
            )

            st.session_state["mensaje_lote"] = (
                f"Repetidas entregadas: {len(resultado['procesados'])}"
            )
            st.session_state["errores_lote"] = resultado["errores"]
            st.rerun()

st.divider()

st.subheader("Búsqueda rápida para móvil")

busqueda = st.text_input(
    "Buscar por código, selección, grupo o nombre",
    placeholder="Ejemplo: ESP, España, ARG05, Brasil, Grupo H"
)

if busqueda:
    termino = busqueda.strip().upper()

    filas_busqueda = []

    for cromo_id, cromo in datos["cromos"].items():
        texto_busqueda = " ".join([
            cromo_id,
            cromo.get("seccion", ""),
            cromo.get("grupo", ""),
            cromo.get("numero", ""),
            cromo.get("nombre", ""),
            cromo.get("tipo", "")
        ]).upper()

        if termino in texto_busqueda:
            filas_busqueda.append({
                "ID": cromo_id,
                "Sección": cromo["seccion"],
                "Grupo": cromo.get("grupo", ""),
                "Número": cromo["numero"],
                "Nombre": cromo["nombre"],
                "Cantidad": cromo["cantidad"],
                "Repetidas": max(0, cromo["cantidad"] - 1),
                "Estado": "Falta" if cromo["cantidad"] == 0 else "Conseguido"
            })

    if filas_busqueda:
        st.dataframe(
            pd.DataFrame(filas_busqueda).head(100),
            use_container_width=True
        )

        if len(filas_busqueda) > 100:
            st.info("Mostrando solo los primeros 100 resultados. Afina más la búsqueda.")
    else:
        st.warning("No se han encontrado cromos con esa búsqueda.")

st.markdown("### Actualización directa por código")

codigo_rapido = st.text_input(
    "Código exacto del cromo",
    placeholder="Ejemplo: ESP01, ARG05, BRA10"
)



codigo_rapido_normalizado = resolver_codigo_en_coleccion(datos, codigo_rapido)

if codigo_rapido_normalizado:
    if codigo_rapido_normalizado not in datos["cromos"]:
        st.error(f"El código {codigo_rapido_normalizado} no existe en la colección.")
    else:
        cromo_rapido = datos["cromos"][codigo_rapido_normalizado]

        st.info(
            f"{codigo_rapido_normalizado} | "
            f"{cromo_rapido['seccion']} | "
            f"{cromo_rapido['nombre']} | "
            f"Cantidad actual: {cromo_rapido['cantidad']} | "
            f"Repetidas: {max(0, cromo_rapido['cantidad'] - 1)}"
        )

        col_rap_1, col_rap_2, col_rap_3 = st.columns(3)

        with col_rap_1:
            if st.button("Añadir por código", key="btn_add_codigo"):
                cambiar_cantidad(
                    datos,
                    codigo_rapido_normalizado,
                    1,
                    "Cromo conseguido por código rápido"
                )
                st.success("Cromo añadido correctamente.")
                st.rerun()

        with col_rap_2:
            if st.button("Entregar repetida por código", key="btn_repetida_codigo"):
                if cromo_rapido["cantidad"] <= 1:
                    st.error("No tienes repetidas de este cromo.")
                else:
                    cambiar_cantidad(
                        datos,
                        codigo_rapido_normalizado,
                        -1,
                        "Repetida entregada por código rápido"
                    )
                    st.success("Repetida descontada correctamente.")
                    st.rerun()

        with col_rap_3:
            if st.button("Quitar una unidad por código", key="btn_quitar_codigo"):
                if cromo_rapido["cantidad"] <= 0:
                    st.error("No puedes bajar de 0.")
                else:
                    cambiar_cantidad(
                        datos,
                        codigo_rapido_normalizado,
                        -1,
                        "Corrección manual por código rápido"
                    )
                    st.success("Cantidad corregida.")
                    st.rerun()

st.divider()

st.subheader("Actualizar colección")

cromo_ids = list(datos["cromos"].keys())

cromo_seleccionado = st.selectbox(
    "Selecciona un cromo",
    cromo_ids,
    format_func=lambda x: f'{x} - {datos["cromos"][x]["nombre"]}'
)

cromo = datos["cromos"][cromo_seleccionado]

st.write(f"**Sección:** {cromo['seccion']}")
st.write(f"**Número:** {cromo['numero']}")
st.write(f"**Nombre:** {cromo['nombre']}")
st.write(f"**Cantidad actual:** {cromo['cantidad']}")

col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("He conseguido este cromo"):
        cambiar_cantidad(datos, cromo_seleccionado, 1, "Cromo conseguido")
        st.success("Cromo añadido correctamente.")
        st.rerun()

with col_b:
    if st.button("He entregado una repetida"):
        if cromo["cantidad"] <= 1:
            st.error("No puedes entregar este cromo porque no tienes repetidas.")
        else:
            cambiar_cantidad(datos, cromo_seleccionado, -1, "Repetida entregada")
            st.success("Repetida descontada correctamente.")
            st.rerun()

with col_c:
    if st.button("Corregir: quitar una unidad"):
        if cromo["cantidad"] <= 0:
            st.error("No puedes bajar de 0.")
        else:
            cambiar_cantidad(datos, cromo_seleccionado, -1, "Corrección manual")
            st.success("Cantidad corregida.")
            st.rerun()

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(
    ["Todos", "Faltantes", "Repetidas", "Movimientos"]
)

with tab1:
    filas = []

    for cromo_id, cromo in datos["cromos"].items():
        filas.append({
            "ID": cromo_id,
            "Sección": cromo["seccion"],
            "Número": cromo["numero"],
            "Nombre": cromo["nombre"],
            "Tipo": cromo["tipo"],
            "Cantidad": cromo["cantidad"],
            "Estado": "Falta" if cromo["cantidad"] == 0 else "Conseguido",
            "Repetidas": max(0, cromo["cantidad"] - 1)
        })

    st.dataframe(pd.DataFrame(filas), use_container_width=True)

with tab2:
    faltantes = listar_faltantes(datos)

    filas = []

    for cromo_id, cromo in faltantes.items():
        filas.append({
            "ID": cromo_id,
            "Sección": cromo["seccion"],
            "Número": cromo["numero"],
            "Nombre": cromo["nombre"],
            "Tipo": cromo["tipo"]
        })

    st.dataframe(pd.DataFrame(filas), use_container_width=True)

with tab3:
    repetidas = listar_repetidas(datos)

    filas = []

    for cromo_id, cromo in repetidas.items():
        filas.append({
            "ID": cromo_id,
            "Sección": cromo["seccion"],
            "Número": cromo["numero"],
            "Nombre": cromo["nombre"],
            "Repetidas": cromo["repetidas"]
        })

    st.dataframe(pd.DataFrame(filas), use_container_width=True)

with tab4:
    movimientos = datos["movimientos"]
    st.dataframe(pd.DataFrame(movimientos), use_container_width=True)

st.divider()

st.subheader("Consulta de entradas por lote")

with st.expander("Ver entradas por fecha, lote y tipo"):
    entradas_lote = obtener_entradas_por_lote(datos)

    if not entradas_lote:
        st.info("Todavía no hay entradas registradas por lote.")
    else:
        df_entradas = pd.DataFrame(entradas_lote)

        fechas_validas = [
            texto_a_fecha(valor)
            for valor in df_entradas["Fecha/Hora"].astype(str).tolist()
            if texto_a_fecha(valor) is not None
        ]

        if fechas_validas:
            fecha_min = min(fechas_validas)
            fecha_max = max(fechas_validas)
        else:
            fecha_min = date.today()
            fecha_max = date.today()

        col_ent_1, col_ent_2, col_ent_3 = st.columns(3)

        with col_ent_1:
            fecha_desde = st.date_input(
                "Desde fecha",
                value=fecha_min,
                key="entrada_fecha_desde"
            )

        with col_ent_2:
            fecha_hasta = st.date_input(
                "Hasta fecha",
                value=fecha_max,
                key="entrada_fecha_hasta"
            )

        with col_ent_3:
            filtro_clasificacion = st.selectbox(
                "Tipo de entrada",
                ["Todas", "nuevo", "repetido", "No disponible"],
                key="entrada_clasificacion"
            )

        lotes_disponibles = sorted(
            df_entradas["Lote entrada"].dropna().astype(str).unique().tolist(),
            reverse=True
        )

        filtro_lote = st.selectbox(
            "Filtrar por lote concreto",
            ["Todos"] + lotes_disponibles,
            key="entrada_lote"
        )

        filtro_texto_entrada = st.text_input(
            "Buscar código, selección o nombre",
            placeholder="Ejemplo: ESP, ARG09, España, Brasil",
            key="entrada_texto"
        )

        df_filtrado = df_entradas.copy()

        df_filtrado["FechaFiltro"] = df_filtrado["Fecha/Hora"].astype(str).apply(texto_a_fecha)

        df_filtrado = df_filtrado[
            (df_filtrado["FechaFiltro"] >= fecha_desde) &
            (df_filtrado["FechaFiltro"] <= fecha_hasta)
        ]

        if filtro_clasificacion != "Todas":
            df_filtrado = df_filtrado[
                df_filtrado["Clasificación"].astype(str) == filtro_clasificacion
            ]

        if filtro_lote != "Todos":
            df_filtrado = df_filtrado[
                df_filtrado["Lote entrada"].astype(str) == filtro_lote
            ]

        if filtro_texto_entrada:
            termino = filtro_texto_entrada.strip().upper()

            def coincide_filtro(row):
                texto = " ".join([
                    str(row.get("ID", "")),
                    str(row.get("Grupo", "")),
                    str(row.get("Sección", "")),
                    str(row.get("Número", "")),
                    str(row.get("Nombre", "")),
                    str(row.get("Comentario", "")),
                ]).upper()

                return termino in texto

            df_filtrado = df_filtrado[
                df_filtrado.apply(coincide_filtro, axis=1)
            ]

        if "FechaFiltro" in df_filtrado.columns:
            df_filtrado = df_filtrado.drop(columns=["FechaFiltro"])

        total_entradas = len(df_filtrado)
        total_nuevos = len(df_filtrado[df_filtrado["Clasificación"] == "nuevo"])
        total_repetidos = len(df_filtrado[df_filtrado["Clasificación"] == "repetido"])

        col_res_1, col_res_2, col_res_3 = st.columns(3)

        col_res_1.metric("Entradas filtradas", total_entradas)
        col_res_2.metric("Nuevos", total_nuevos)
        col_res_3.metric("Repetidos", total_repetidos)

        st.dataframe(
            df_filtrado,
            use_container_width=True,
            hide_index=True
        )

        if not df_filtrado.empty:
            excel_filtrado = convertir_dataframe_a_excel_bytes(df_filtrado)

            st.download_button(
                label="Descargar consulta filtrada Excel",
                data=excel_filtrado,
                file_name="consulta_entradas_filtrada.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

st.divider()

st.subheader("Informes para móvil")

faltantes = listar_faltantes(datos)
repetidas = listar_repetidas(datos)

resumen_txt = generar_resumen_txt(datos, resumen)
faltantes_txt = generar_faltantes_txt(faltantes)
repetidas_txt = generar_repetidas_txt(repetidas)

col_inf1, col_inf2, col_inf3 = st.columns(3)

with col_inf1:
    st.download_button(
        label="Descargar resumen TXT",
        data=resumen_txt,
        file_name="resumen_coleccion.txt",
        mime="text/plain"
    )

with col_inf2:
    st.download_button(
        label="Descargar faltantes TXT",
        data=faltantes_txt,
        file_name="cromos_faltantes.txt",
        mime="text/plain"
    )

with col_inf3:
    st.download_button(
        label="Descargar repetidas TXT",
        data=repetidas_txt,
        file_name="cromos_repetidos.txt",
        mime="text/plain"
    )

if st.button("Guardar informes en carpeta informes"):
    guardar_txt("resumen_coleccion.txt", resumen_txt)
    guardar_txt("cromos_faltantes.txt", faltantes_txt)
    guardar_txt("cromos_repetidos.txt", repetidas_txt)
    st.success("Informes guardados correctamente en la carpeta informes.")

excel_bytes = generar_excel_bytes(datos, resumen)

st.download_button(
    label="Descargar Excel completo",
    data=excel_bytes,
    file_name="coleccion_cromos_mundial_2026.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

if st.button("Guardar Excel en carpeta informes"):
    guardar_excel("coleccion_cromos_mundial_2026.xlsx", excel_bytes)
    st.success("Excel guardado correctamente en la carpeta informes.")


st.markdown("### Informe de entradas por lote")

entradas_lotes_txt = generar_entradas_lotes_txt(datos)
entradas_lotes_excel = generar_entradas_lotes_excel_bytes(datos)

col_lotes_1, col_lotes_2, col_lotes_3 = st.columns(3)

with col_lotes_1:
    st.download_button(
        label="Descargar entradas por lote TXT",
        data=entradas_lotes_txt,
        file_name="entradas_por_lote.txt",
        mime="text/plain"
    )

with col_lotes_2:
    st.download_button(
        label="Descargar entradas por lote Excel",
        data=entradas_lotes_excel,
        file_name="entradas_por_lote.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with col_lotes_3:
    if st.button("Guardar informe entradas por lote"):
        guardar_txt("entradas_por_lote.txt", entradas_lotes_txt)
        guardar_excel("entradas_por_lote.xlsx", entradas_lotes_excel)
        st.success("Informe de entradas por lote guardado en carpeta informes.")
st.divider()

st.subheader("Herramientas de configuración inicial")

st.caption(
    "Estas opciones normalmente solo se usan al principio: marcaje manual inicial "
    "e importación asistida desde imagen. Se dejan al final para no molestar en el uso diario."
)

st.divider()

st.subheader("Marcaje inicial manual con checks")

with st.expander("Ver lista completa con checks"):
    st.warning(
        "Esta pantalla sirve para marcar el estado inicial. "
        "Si desmarcas un cromo que ya tenía cantidad, se pondrá a 0. "
        "Úsalo con cuidado si ya has metido repetidas."
    )

    grupos_disponibles = sorted(
        set(str(cromo.get("grupo", "")) for cromo in datos["cromos"].values())
    )

    secciones_disponibles = sorted(
        set(str(cromo.get("seccion", "")) for cromo in datos["cromos"].values())
    )

    col_filtro_1, col_filtro_2, col_filtro_3 = st.columns(3)

    with col_filtro_1:
        filtro_grupo = st.selectbox(
            "Filtrar por grupo",
            ["Todos"] + grupos_disponibles,
            key="filtro_checks_grupo"
        )

    with col_filtro_2:
        filtro_seccion = st.selectbox(
            "Filtrar por selección/sección",
            ["Todas"] + secciones_disponibles,
            key="filtro_checks_seccion"
        )

    with col_filtro_3:
        filtro_texto = st.text_input(
            "Buscar código o nombre",
            placeholder="Ejemplo: ESP, ESP01, España",
            key="filtro_checks_texto"
        )

    filas_checks = []

    for cromo_id, cromo in datos["cromos"].items():
        grupo = str(cromo.get("grupo", ""))
        seccion = str(cromo.get("seccion", ""))
        nombre = str(cromo.get("nombre", ""))
        tipo = str(cromo.get("tipo", ""))
        numero = str(cromo.get("numero", ""))

        if filtro_grupo != "Todos" and grupo != filtro_grupo:
            continue

        if filtro_seccion != "Todas" and seccion != filtro_seccion:
            continue

        if filtro_texto:
            texto_busqueda = " ".join([
                cromo_id,
                grupo,
                seccion,
                numero,
                nombre,
                tipo
            ]).upper()

            if filtro_texto.strip().upper() not in texto_busqueda:
                continue

        cantidad = cromo["cantidad"]

        filas_checks.append({
            "Tengo": cantidad >= 1,
            "ID": cromo_id,
            "Grupo": grupo,
            "Sección": seccion,
            "Número": numero,
            "Nombre": nombre,
            "Tipo": tipo,
            "Cantidad actual": cantidad,
            "Repetidas": max(0, cantidad - 1),
        })

    df_checks = pd.DataFrame(filas_checks)

    if df_checks.empty:
        st.info("No hay cromos para mostrar con los filtros actuales.")
    else:
        st.caption(
            f"Mostrando {len(df_checks)} cromos. "
            "Marca o desmarca la columna 'Tengo' y guarda los cambios."
        )

        df_editado_checks = st.data_editor(
            df_checks,
            use_container_width=True,
            hide_index=True,
            disabled=[
                "ID",
                "Grupo",
                "Sección",
                "Número",
                "Nombre",
                "Tipo",
                "Cantidad actual",
                "Repetidas"
            ],
            column_config={
                "Tengo": st.column_config.CheckboxColumn(
                    "Tengo",
                    help="Marca este check si tienes el cromo.",
                    default=False
                )
            },
            key="editor_checks_estado"
        )

        col_checks_1, col_checks_2, col_checks_3 = st.columns(3)

        with col_checks_1:
            if st.button("Guardar checks visibles"):
                resultado = aplicar_checks_estado(
                    datos,
                    df_editado_checks.to_dict("records"),
                    "Marcaje manual inicial con checks"
                )

                st.success(
                    f"Cambios guardados. "
                    f"Marcados nuevos: {len(resultado['marcados'])}. "
                    f"Desmarcados: {len(resultado['desmarcados'])}."
                )

                if resultado["errores"]:
                    with st.expander("Errores"):
                        for error in resultado["errores"]:
                            st.warning(error)

                st.rerun()

        with col_checks_2:
            if st.button("Marcar todos los visibles"):
                filas_marcar = df_checks.copy()
                filas_marcar["Tengo"] = True

                resultado = aplicar_checks_estado(
                    datos,
                    filas_marcar.to_dict("records"),
                    "Marcaje masivo manual visible"
                )

                st.success(
                    f"Marcados visibles guardados. "
                    f"Marcados nuevos: {len(resultado['marcados'])}."
                )

                st.rerun()

        with col_checks_3:
            if st.button("Desmarcar todos los visibles"):
                filas_desmarcar = df_checks.copy()
                filas_desmarcar["Tengo"] = False

                resultado = aplicar_checks_estado(
                    datos,
                    filas_desmarcar.to_dict("records"),
                    "Desmarcado masivo manual visible"
                )

                st.success(
                    f"Desmarcados visibles guardados. "
                    f"Desmarcados: {len(resultado['desmarcados'])}."
                )

                st.rerun()

st.divider()

st.subheader("Importar cromos marcados en naranja desde imagen")

with st.expander("Subir imagen marcada"):
    imagen_marcada = st.file_uploader(
        "Sube la imagen de la plantilla marcada en naranja",
        type=["jpg", "jpeg", "png"]
    )

    st.caption(
        "Esta detección es asistida. Revisa la tabla antes de confirmar, "
        "porque una foto con arrugas, sombras o perspectiva puede generar errores."
    )

    col_cfg1, col_cfg2 = st.columns(2)

    with col_cfg1:
        x1_pct = st.slider("Inicio X cuadrícula (%)", 0, 50, 17)
        y1_pct = st.slider("Inicio Y cuadrícula (%)", 0, 50, 13)

    with col_cfg2:
        x2_pct = st.slider("Fin X cuadrícula (%)", 50, 100, 97)
        y2_pct = st.slider("Fin Y cuadrícula (%)", 50, 100, 86)

    umbral_naranja_pct = st.slider(
        "Sensibilidad naranja (%)",
        min_value=1.0,
        max_value=25.0,
        value=4.0,
        step=0.5
    )

    if imagen_marcada is not None:
        st.image(imagen_marcada, caption="Imagen cargada", use_container_width=True)

        if st.button("Detectar cromos naranjas"):
            try:
                detectados = detectar_cromos_naranja_desde_imagen(
                    imagen_marcada.getvalue(),
                    x1_pct=x1_pct,
                    x2_pct=x2_pct,
                    y1_pct=y1_pct,
                    y2_pct=y2_pct,
                    umbral_naranja_pct=umbral_naranja_pct
                )

                st.session_state["detectados_imagen"] = detectados

                if detectados:
                    st.success(f"Cromos detectados: {len(detectados)}")
                else:
                    st.warning("No se detectó ningún cromo marcado en naranja.")

            except Exception as e:
                st.error(f"Error al analizar la imagen: {e}")

    
    detectados_guardados = st.session_state.get("detectados_imagen", [])

    if detectados_guardados:
        st.markdown("### Cromos detectados pendientes de revisar")

        df_detectados = pd.DataFrame(detectados_guardados)

        if "Importar" not in df_detectados.columns:
            df_detectados.insert(0, "Importar", True)

        st.info(
            "Revisa la tabla antes de confirmar. "
            "Desmarca los cromos que estén mal detectados y añade abajo los que falten."
        )

        df_editado = st.data_editor(
            df_detectados,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Importar": st.column_config.CheckboxColumn(
                    "Importar",
                    help="Déjalo marcado si quieres importar este cromo.",
                    default=True
                ),
                "ID": st.column_config.TextColumn("ID", disabled=True),
                "Sección": st.column_config.TextColumn("Sección", disabled=True),
                "Grupo": st.column_config.TextColumn("Grupo", disabled=True),
                "Número": st.column_config.TextColumn("Número", disabled=True),
                "Nombre": st.column_config.TextColumn("Nombre", disabled=True),
                "Porcentaje naranja": st.column_config.NumberColumn(
                    "Porcentaje naranja",
                    disabled=True
                ),
                "Fila": st.column_config.NumberColumn("Fila", disabled=True),
                "Columna": st.column_config.NumberColumn("Columna", disabled=True),
            },
            key="editor_detectados_imagen"
        )

        codigos_seleccionados = (
            df_editado[df_editado["Importar"] == True]["ID"]
            .astype(str)
            .str.upper()
            .tolist()
        )

        st.markdown("### Añadir cromos no detectados")

        codigos_extra_texto = st.text_area(
            "Códigos extra a importar",
            placeholder="Ejemplo: ESP01, ARG05, BRA10\nPuedes separarlos por comas, espacios o saltos de línea.",
            height=100
        )

        codigos_extra = normalizar_codigos_lote(codigos_extra_texto)

        codigos_finales = []

        for codigo in codigos_seleccionados + codigos_extra:
            codigo = codigo.strip().upper().replace("-", "").replace(" ", "")

            if codigo and codigo not in codigos_finales:
                codigos_finales.append(codigo)

        codigos_invalidos = [
            codigo for codigo in codigos_finales
            if codigo not in datos["cromos"]
        ]

        codigos_validos = [
            codigo for codigo in codigos_finales
            if codigo in datos["cromos"]
        ]

        col_rev1, col_rev2, col_rev3 = st.columns(3)

        col_rev1.metric("Detectados inicialmente", len(detectados_guardados))
        col_rev2.metric("Seleccionados para importar", len(codigos_validos))
        col_rev3.metric("Códigos inválidos", len(codigos_invalidos))

        if codigos_invalidos:
            with st.expander("Ver códigos inválidos"):
                for codigo in codigos_invalidos:
                    st.warning(f"{codigo}: no existe en la colección.")

        if codigos_validos:
            with st.expander("Ver lista final que se importará"):
                st.write(", ".join(codigos_validos))

        if st.button("Confirmar solo cromos seleccionados"):
            if not codigos_validos:
                st.error("No hay ningún cromo válido seleccionado para importar.")
            else:
                resultado = marcar_como_tengo_lote(
                    datos,
                    codigos_validos,
                    "Cromos importados desde imagen marcada en naranja"
                )

                st.session_state.pop("detectados_imagen", None)

                st.success(
                    f"Importación aplicada. "
                    f"Nuevos marcados: {len(resultado['procesados'])}. "
                    f"Ya estaban marcados: {len(resultado['ya_estaban'])}."
                )

                if resultado["errores"]:
                    with st.expander("Errores de importación"):
                        for error in resultado["errores"]:
                            st.warning(error)

                st.rerun()

        if st.button("Descartar detección"):
            st.session_state.pop("detectados_imagen", None)
            st.rerun()
