
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ==========================================
# CONFIGURACIÓN
# ==========================================

st.set_page_config(
    page_title="SATIF - Evolución temporal",
    page_icon="🛰️",
    layout="wide",
)

RAIZ = Path(__file__).resolve().parents[1]

ARCHIVO = (
    RAIZ
    / "data"
    / "processed"
    / "episodios_principales_cartografia.csv"
)


# ==========================================
# DATOS
# ==========================================

@st.cache_data
def cargar_datos():
    datos = pd.read_csv(ARCHIVO)

    datos["fecha_hora_utc"] = pd.to_datetime(
        datos["fecha_hora_utc"],
        utc=True,
    )

    datos["dia_utc"] = (
        datos["fecha_hora_utc"]
        .dt.strftime("%Y-%m-%d")
    )

    return datos


datos = cargar_datos()


# ==========================================
# ENCABEZADO
# ==========================================

st.title("🛰️ SATIF HISTÓRICO")
st.subheader("Evolución espacial y temporal")

st.caption(
    "Visualización exploratoria de detecciones "
    "térmicas NASA FIRMS. Los episodios son "
    "agrupaciones candidatas, no incendios "
    "individuales confirmados."
)


# ==========================================
# SELECCIÓN DE EPISODIO
# ==========================================

episodios = sorted(
    datos["episodio_id"].unique()
)

episodio = st.selectbox(
    "Seleccionar episodio",
    episodios,
)

filtrado = datos[
    datos["episodio_id"] == episodio
].copy()

dias = sorted(
    filtrado["dia_utc"].unique()
)

dia = st.select_slider(
    "Fecha de observación (UTC)",
    options=dias,
    value=dias[0],
)

acumulado = st.checkbox(
    "Mostrar detecciones acumuladas "
    "hasta la fecha seleccionada",
    value=False,
)

if acumulado:
    mapa_datos = filtrado[
        filtrado["dia_utc"] <= dia
    ].copy()
else:
    mapa_datos = filtrado[
        filtrado["dia_utc"] == dia
    ].copy()


# ==========================================
# INDICADORES
# ==========================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Detecciones visibles",
    len(mapa_datos),
)

c2.metric(
    "Grupos V2",
    mapa_datos[
        "grupo_observacion_v2"
    ].nunique(),
)

c3.metric(
    "Sensores",
    mapa_datos[
        "sensor_origen"
    ].nunique(),
)

c4.metric(
    "Días del episodio",
    len(dias),
)


# ==========================================
# MAPA
# ==========================================

st.subheader("Distribución espacial")

tipo_mapa = st.radio(
    "Base cartográfica",
    [
        "Imagen satelital",
        "Mapa topográfico",
        "Mapa de calles",
        "Mapa oscuro",
    ],
    horizontal=True,
    key="base_mapa_temporal",
)



centro = {
    "lat": float(
        filtrado["latitude"].mean()
    ),
    "lon": float(
        filtrado["longitude"].mean()
    ),
}

figura = px.scatter_map(
    mapa_datos,
    lat="latitude",
    lon="longitude",
    color="dia_utc",
    hover_data=[
        "sensor_origen",
        "fecha_hora_utc",
        "frp",
        "grupo_observacion_v2",
    ],
    center=centro,
    zoom=10,
    height=650,
    opacity=0.8,
    title=f"{episodio} — {dia}",
)

figura.update_traces(
    marker={"size": 9}
)


# ==========================================
# CONFIGURACION DE MAPAS BASE
# ==========================================

if tipo_mapa == "Imagen satelital":
    figura.update_layout(
        map_style="white-bg",
        map_layers=[
            dict(
                below="traces",
                sourcetype="raster",
                source=[
                    "https://server.arcgisonline.com/"
                    "ArcGIS/rest/services/World_Imagery/"
                    "MapServer/tile/{z}/{y}/{x}"
                ],
                opacity=1.0,
            )
        ],
    )

elif tipo_mapa == "Mapa topográfico":
    figura.update_layout(
        map_style="white-bg",
        map_layers=[
            dict(
                below="traces",
                sourcetype="raster",
                source=[
                    "https://server.arcgisonline.com/"
                    "ArcGIS/rest/services/World_Topo_Map/"
                    "MapServer/tile/{z}/{y}/{x}"
                ],
                opacity=1.0,
            )
        ],
    )

elif tipo_mapa == "Mapa oscuro":
    figura.update_layout(
        map_style="carto-darkmatter",
        map_layers=[],
    )

else:
    figura.update_layout(
        map_style="open-street-map",
        map_layers=[],
    )




figura.update_layout(
    margin=dict(l=0, r=0, t=50, b=0),
    legend_title_text="Día UTC",
)

st.plotly_chart(
    figura,
    use_container_width=True,
)



st.subheader("Detecciones por día")

diario = (
    filtrado.groupby(
        "dia_utc",
        as_index=False,
    )
    .agg(
        detecciones=("latitude", "size"),
        grupos_v2=(
            "grupo_observacion_v2",
            "nunique",
        ),
    )
)

grafico = px.bar(
    diario,
    x="dia_utc",
    y="detecciones",
    title="Actividad térmica detectada por día",
    labels={
        "dia_utc": "Fecha UTC",
        "detecciones": "Detecciones",
    },
)

st.plotly_chart(
    grafico,
    use_container_width=True,
)




with st.expander("Ver detecciones"):

    st.dataframe(
        mapa_datos[
            [
                "fecha_hora_utc",
                "latitude",
                "longitude",
                "sensor_origen",
                "frp",
                "grupo_observacion_v2",
            ]
        ],
        use_container_width=True,
    )

st.download_button(
    "Descargar detecciones visibles (CSV)",
    data=mapa_datos.to_csv(
        index=False
    ).encode("utf-8"),
    file_name=(
        f"{episodio}_{dia}_detecciones.csv"
    ),
    mime="text/csv",
)
