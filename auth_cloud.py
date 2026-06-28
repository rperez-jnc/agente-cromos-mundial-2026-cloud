import streamlit as st

from db_cloud import autenticar_usuario


def exigir_login_cloud():
    if "usuario_cloud" not in st.session_state:
        st.session_state["usuario_cloud"] = None

    if st.session_state["usuario_cloud"]:
        usuario = st.session_state["usuario_cloud"]

        with st.sidebar:
            st.markdown(f"**Usuario:** {usuario['nombre']}")
            st.caption(f"Login: {usuario['usuario']}")

            if usuario["es_admin"]:
                st.success("Administrador")

            if st.button("Cerrar sesión"):
                st.session_state["usuario_cloud"] = None
                st.rerun()

        return usuario

    st.title("Acceso privado")
    st.caption("Introduce tu usuario y contraseña para acceder a tu colección.")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar", use_container_width=True):
        usuario_validado = autenticar_usuario(usuario, password)

        if usuario_validado:
            st.session_state["usuario_cloud"] = usuario_validado
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

    st.stop()