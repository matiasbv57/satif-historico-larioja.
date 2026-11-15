
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="SATIF Histórico | Actividad combinada",
    layout="wide"
)

BASE = Path(__file__).resolve().parents[1]

ARCHIVO = (
    BASE / "data/processed/"
    "calendario_dias_actividad_combinada.csv"
)

MESES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
]

INDICADORES = {
    "actividad_combinada": "MODIS + VIIRS",
    "actividad_modis": "MODIS",
    "actividad_viirs": "VIIRS",
    "coincidencia_familias": "Coincidencias MODIS–VIIRS"
}


@st.cache_data
def cargar_datos():
    return pd.read_csv(ARCHIVO)


df = cargar_datos()

st.title("SATIF Histórico")
st.subheader("Calendario combinado de actividad satelital")

st.caption(
    "NASA FIRMS | Días con al menos una detección "
    "satelital. No representa incendios independientes."
)

col1, col2 = st.columns(2)

with col1:
    region = st.selectbox(
        "Territorio",
        ["La Rioja completa"] +
        sorted(df["departamento"].unique().tolist())
    )

with col2:
    indicador = st.selectbox(
        "Indicador",
        list(INDICADORES),
        format_func=lambda x: INDICADORES[x]
    )

if region == "La Rioja completa":
    # Una fecha cuenta una sola vez en la provincia.
    datos = (
        df.groupby(["fecha", "anio", "mes"], as_index=False)
        [indicador]
        .max()
    )
else:
    datos = df[
        df["departamento"] == region
    ][["fecha", "anio", "mes", indicador]].copy()

mensual = (
    datos.groupby(["anio", "mes"], as_index=False)
    [indicador]
    .sum()
)

# El indicador combinado comienza en 2000.
# VIIRS solo está disponible desde 2012.
inicio = {
    "actividad_modis": "2000-11-01",
    "actividad_viirs": "2012-01-01",
    "actividad_combinada": "2000-11-01",
    "coincidencia_familias": "2012-01-01"
}[indicador]

periodos = pd.date_range(
    start=inicio,
    end="2026-11-01",
    freq="MS"
)

calendario = pd.DataFrame({
    "anio": periodos.year,
    "mes": periodos.month,
    "periodo": periodos
})

calendario = calendario.merge(
    mensual,
    on=["anio", "mes"],
    how="left"
)

calendario[indicador] = (
    calendario[indicador].fillna(0).astype(int)
)

# El último mes está incompleto.
calendario["valor_grafico"] = calendario[indicador].where(
    ~(
        (calendario["anio"] == 2026)
        & (calendario["mes"] == 11)
    )
)

st.divider()

c1, c2, c3 = st.columns(3)

c1.metric(
    "Días con actividad",
    f"{int(datos[indicador].sum()):,}"
)

c2.metric(
    "Años representados",
    calendario["anio"].nunique()
)

c3.metric(
    "Meses con actividad",
    int((calendario[indicador] > 0).sum())
)

st.subheader(
    f"Calendario mensual — {region}"
)
st.warning(
    "COMPARABILIDAD HISTÓRICA: la serie combinada "
    "MODIS–VIIRS no es homogénea a lo largo de "
    "2000–2026. La incorporación progresiva de "
    "sensores VIIRS aumenta la capacidad de "
    "detección y puede producir tendencias "
    "artificiales. Este calendario representa "
    "días con actividad satelital detectada, "
    "no una tendencia corregida del número "
    "de incendios."
)

matriz = calendario.pivot(
    index="anio",
    columns="mes",
    values="valor_grafico"
).reindex(columns=range(1, 13))

matriz.columns = MESES

fig = px.imshow(
    matriz,
    aspect="auto",
    color_continuous_scale="YlOrRd",
    labels={
        "x": "Mes",
        "y": "Año",
        "color": "Días"
    },
    title=INDICADORES[indicador]
)

fig.update_layout(
    height=max(500, len(matriz) * 23)
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.subheader("Evolución mensual")

fig_linea = px.line(
    calendario,
    x="periodo",
    y="valor_grafico",
    markers=True,
    labels={
        "periodo": "Fecha",
        "valor_grafico": "Días con actividad"
    }
)

st.plotly_chart(
    fig_linea,
    use_container_width=True
)

st.download_button(
    "Descargar calendario combinado CSV",
    data=calendario.to_csv(index=False).encode("utf-8"),
    file_name="SATIF_calendario_combinado.csv",
    mime="text/csv"
)

with st.expander("Metodología"):
    st.write(
        "Un día se considera con actividad cuando "
        "existe al menos una detección satelital "
        "dentro del territorio seleccionado."
    )
    st.write(
        "La combinación MODIS–VIIRS evita contar "
        "dos veces una misma fecha, pero no corrige "
        "diferencias de sensibilidad, resolución "
        "espacial o frecuencia de observación."
    )
    st.write(
        "Los días sin detecciones no garantizan "
        "ausencia de incendios."
    )
