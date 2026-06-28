import streamlit as st


def aplicar_estilo():
    st.markdown(
        """
        <style>
        :root {
            --rojo-espana: #AA151B;
            --rojo-oscuro: #7F1015;
            --amarillo-espana: #F1BF00;
            --amarillo-suave: #FFF4BF;
            --fondo: #FFF9EA;
            --texto: #1F1F1F;
            --borde: #E4C766;
        }

        .stApp {
            background: linear-gradient(180deg, #FFF9EA 0%, #FFFDF4 45%, #FFFFFF 100%);
            color: var(--texto);
        }

        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        .app-hero {
            background: linear-gradient(135deg, var(--rojo-espana) 0%, #C61B22 48%, var(--amarillo-espana) 48%, #FFD84A 100%);
            padding: 22px 24px;
            border-radius: 22px;
            color: white;
            box-shadow: 0 8px 24px rgba(127, 16, 21, 0.24);
            margin-bottom: 18px;
            border: 1px solid rgba(255,255,255,0.4);
        }

        .app-hero h1 {
            margin: 0;
            font-size: 2.1rem;
            font-weight: 850;
            letter-spacing: -0.03em;
        }

        .app-hero p {
            margin: 6px 0 0 0;
            font-size: 1rem;
            color: rgba(255,255,255,0.95);
        }

        h1, h2, h3 {
            color: var(--rojo-oscuro);
            letter-spacing: -0.02em;
        }

        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid var(--borde);
            border-left: 7px solid var(--rojo-espana);
            padding: 14px 16px;
            border-radius: 16px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.06);
        }

        div[data-testid="stMetricLabel"] {
            color: #6C4B00;
            font-weight: 700;
        }

        div[data-testid="stMetricValue"] {
            color: var(--rojo-oscuro);
            font-weight: 850;
        }

        div[data-testid="stExpander"] {
            background: #FFFFFF;
            border: 1px solid rgba(170, 21, 27, 0.18);
            border-radius: 16px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
            overflow: hidden;
        }

        div[data-testid="stExpander"] summary {
            background: linear-gradient(90deg, #FFF4BF 0%, #FFFFFF 100%);
            color: var(--rojo-oscuro);
            font-weight: 750;
        }

        .stButton > button {
            border-radius: 14px;
            border: 1px solid var(--rojo-espana);
            background: linear-gradient(180deg, var(--rojo-espana) 0%, var(--rojo-oscuro) 100%);
            color: white;
            font-weight: 750;
            min-height: 42px;
            box-shadow: 0 4px 10px rgba(170, 21, 27, 0.18);
        }

        .stButton > button:hover {
            border-color: var(--amarillo-espana);
            background: linear-gradient(180deg, #C61B22 0%, var(--rojo-espana) 100%);
            color: #FFFFFF;
            transform: translateY(-1px);
        }

        .stDownloadButton > button {
            border-radius: 14px;
            border: 1px solid #B38B00;
            background: linear-gradient(180deg, var(--amarillo-espana) 0%, #DFA900 100%);
            color: #3A2600;
            font-weight: 800;
            min-height: 42px;
            box-shadow: 0 4px 10px rgba(177, 139, 0, 0.18);
        }

        .stDownloadButton > button:hover {
            border-color: var(--rojo-espana);
            background: linear-gradient(180deg, #FFD84A 0%, var(--amarillo-espana) 100%);
            color: #2A1A00;
        }

        input, textarea {
            border-radius: 14px !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus {
            border-color: var(--rojo-espana) !important;
            box-shadow: 0 0 0 1px var(--rojo-espana) !important;
        }

        div[data-testid="stAlert"] {
            border-radius: 14px;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid rgba(170, 21, 27, 0.12);
        }

        hr {
            border: none;
            border-top: 1px solid rgba(170, 21, 27, 0.18);
            margin: 1.8rem 0;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }

            .app-hero {
                padding: 18px 16px;
                border-radius: 18px;
            }

            .app-hero h1 {
                font-size: 1.55rem;
            }

            .app-hero p {
                font-size: 0.9rem;
            }

            .stButton > button,
            .stDownloadButton > button {
                width: 100%;
                min-height: 48px;
                font-size: 0.95rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_header():
    st.markdown(
        """
        <div class="app-hero">
            <h1>Agente Cromos Mundial 2026</h1>
            <p>Control de colección, repetidas, intercambios e informes desde móvil.</p>
        </div>
        """,
        unsafe_allow_html=True
    )