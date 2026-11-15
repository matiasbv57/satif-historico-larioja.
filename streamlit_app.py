
import streamlit as st
from pathlib import Path

# ==========================================
# CONFIGURACION GENERAL
# ==========================================

st.set_page_config(
    page_title="SATIF | Monitoreo de Incendios",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# IDENTIDAD VISUAL NASA SPACE APPS
# ==========================================

ruta_css = (
    Path(__file__).resolve().parent
    / "assets"
    / "satif.css"
)

if ruta_css.exists():
    css = ruta_css.read_text(encoding="utf-8-sig")

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True
    )

# ==========================================
# NAVEGACION SATIF HISTORICO
# ==========================================

paginas = {
    "SATIF Histórico": [
        st.Page(
            "app/calendario_historico.py",
            title="Calendario histórico",
            icon="📅"
        ),
        st.Page(
            "app/calendario_combinado.py",
            title="Calendario combinado",
            icon="🛰️"
        ),
        st.Page(
            "app/main.py",
            title="Análisis MODIS-VIIRS",
            icon="📊"
        ),
        st.Page(
            "app/visor_temporal_estable_v1.py",
            title="Visor temporal",
            icon="🗺️"
        )
    ]
}

pagina = st.navigation(paginas)
pagina.run()
