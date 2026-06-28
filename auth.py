import hmac
import streamlit as st


def credenciales_correctas(usuario, password):
    usuario_configurado = st.secrets.get("APP_USER", "admin")
    password_configurada = st.secrets.get("APP_PASSWORD", "")

    return (
        hmac.compare_digest(str(usuario), str(usuario_configurado))
        and hmac.compare_digest(str(password), str(password_configurada))
    )


def exigir_login():
    if "auth_ok" not in st.session_state:
        st.session_state["auth_ok"] = False

    if st.session_state["auth_ok"]:
        with st.sidebar:
            st.caption("Sesión iniciada")

            if st.button("Cerrar sesión"):
                st.session_state["auth_ok"] = False
                st.rerun()

        return

    st.title("Acceso protegido")
    st.warning("Introduce usuario y contraseña para acceder al agente.")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        if credenciales_correctas(usuario, password):
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

    st.stop()