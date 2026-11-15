
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="SATIF Histórico | Calendario territorial",
    layout="wide"
)

BASE = Path(__file__).resolve().parents[1]
ARCHIVO = (
    BASE / "data/processed/"
    "firms_historico_departamentos_completo.csv"
)

SENSORES = {
    "MODIS": "MODIS",
    "VIIRS_S_NPP": "VIIRS S-NPP",
    "VIIRS_NOAA20": "VIIRS NOAA-20",
    "VIIRS_NOAA21": "VIIRS NOAA-21",
}

INICIO_SENSORES = {
    "MODIS": "2000-11-01",
    "VIIRS_S_NPP": "2012-01-01",
    "VIIRS_NOAA20": "2018-04-01",
    "VIIRS_NOAA21": "2023-03-01",
}

MESES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
]


@st.cache_data
def cargar_datos():
    df = pd.read_csv(
        ARCHIVO,
        usecols=[
            "fecha_hora_utc",
            "sensor_origen",
            "departamento",
            "latitude",
            "longitude"
        ]
    )

    df["fecha"] = pd.to_datetime(
        df["fecha_hora_utc"],
        utc=True,
        errors="coerce"
    )

    if df["fecha"].isna().any():
        raise ValueError("Fechas invalidas en la base")

    return df


df = cargar_datos()

st.title("SATIF Histórico")
st.subheader("Calendario territorial de actividad satelital")

st.caption(
    "NASA FIRMS | La Rioja, Argentina | 2000–2026. "
    "Las detecciones no equivalen a incendios individuales."
)

col1, col2 = st.columns(2)

with col1:
    opciones = ["La Rioja completa"] + sorted(
        df["departamento"].dropna().unique().tolist()
    )

    region = st.selectbox(
        "Seleccionar territorio",
        opciones
    )

with col2:
    sensor = st.selectbox(
        "Seleccionar satélite / sensor",
        list(SENSORES),
        format_func=lambda x: SENSORES[x]
    )

filtrado = df[df["sensor_origen"] == sensor].copy()

if region != "La Rioja completa":
    filtrado = filtrado[
        filtrado["departamento"] == region
    ].copy()

filtrado["anio"] = filtrado["fecha"].dt.year
filtrado["mes"] = filtrado["fecha"].dt.month

conteos = (
    filtrado.groupby(["anio", "mes"])
    .size()
    .reset_index(name="detecciones")
)

inicio = pd.Timestamp(INICIO_SENSORES[sensor])
fin = pd.Timestamp("2026-11-01")

periodos = pd.date_range(
    start=inicio,
    end=fin,
    freq="MS"
)

calendario = pd.DataFrame({
    "anio": periodos.year,
    "mes": periodos.month,
    "periodo": periodos
})

calendario = calendario.merge(
    conteos,
    on=["anio", "mes"],
    how="left"
)

calendario["detecciones"] = (
    calendario["detecciones"].fillna(0).astype(int)
)

# Noviembre 2026 es un mes incompleto.
calendario["mes_parcial"] = (
    (calendario["anio"] == 2026)
    & (calendario["mes"] == 11)
)

calendario["detecciones_grafico"] = (
    calendario["detecciones"].where(
        ~calendario["mes_parcial"]
    )
)

st.divider()

c1, c2, c3 = st.columns(3)

c1.metric(
    "Detecciones históricas",
    f"{len(filtrado):,}"
)

c2.metric(
    "Años del período",
    calendario["anio"].nunique()
)

c3.metric(
    "Meses con detecciones",
    int((calendario["detecciones"] > 0).sum())
)

st.subheader(f"Calendario mensual — {region}")

matriz = calendario.pivot(
    index="anio",
    columns="mes",
    values="detecciones_grafico"
).reindex(columns=range(1, 13))

matriz.columns = MESES

fig = px.imshow(
    matriz,
    color_continuous_scale="YlOrRd",
    aspect="auto",
    labels={
        "x": "Mes",
        "y": "Año",
        "color": "Detecciones"
    }
)

fig.update_layout(
    height=max(500, len(matriz) * 23),
    margin=dict(l=20, r=20, t=20, b=20)
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Celdas vacías: período sin datos disponibles "
    "o noviembre de 2026, todavía incompleto. "
    "Cero detecciones no garantiza ausencia de incendios."
)

st.subheader("Evolución mensual")

fig_linea = px.line(
    calendario,
    x="periodo",
    y="detecciones_grafico",
    markers=True,
    labels={
        "periodo": "Fecha",
        "detecciones_grafico": "Detecciones"
    }
)

fig_linea.update_layout(
    hovermode="x unified"
)

st.plotly_chart(
    fig_linea,
    use_container_width=True
)



st.divider()
st.subheader("Anomalías históricas de detecciones")

st.caption(
    "Comparación de cada mes con la mediana histórica "
    "del mismo mes, para el territorio y sensor elegidos."
)

# Excluir el mes parcial de noviembre de 2026
referencia = calendario.loc[
    ~calendario["mes_parcial"]
].copy()

medianas = (
    referencia.groupby("mes")["detecciones"]
    .median()
    .rename("mediana_historica")
)

calendario = calendario.merge(
    medianas,
    on="mes",
    how="left"
)

calendario["anomalia"] = (
    calendario["detecciones"]
    - calendario["mediana_historica"]
)

calendario.loc[
    calendario["mes_parcial"], "anomalia"
] = float("nan")

matriz_anomalias = calendario.pivot(
    index="anio",
    columns="mes",
    values="anomalia"
).reindex(columns=range(1, 13))

matriz_anomalias.columns = MESES

limite = matriz_anomalias.abs().max().max()

if pd.isna(limite) or limite == 0:
    limite = 1

fig_anomalias = px.imshow(
    matriz_anomalias,
    color_continuous_scale="RdBu_r",
    zmin=-limite,
    zmax=limite,
    aspect="auto",
    labels={
        "x": "Mes",
        "y": "Año",
        "color": "Anomalía"
    },
    title=f"Anomalías mensuales — {region} — {SENSORES[sensor]}"
)

fig_anomalias.update_layout(
    height=max(500, len(matriz_anomalias) * 23),
    margin=dict(l=20, r=20, t=40, b=20)
)

st.plotly_chart(
    fig_anomalias,
    use_container_width=True
)

st.caption(
    "Rojo: más detecciones que la mediana histórica. "
    "Azul: menos detecciones. "
    "Las anomalías se calculan por sensor y no "
    "son directamente comparables entre sensores."
)

st.download_button(
    "Descargar calendario territorial CSV",
    data=calendario.to_csv(index=False).encode("utf-8"),
    file_name=f"SATIF_calendario_{sensor}.csv",
    mime="text/csv"
)

with st.expander("Consultar datos mensuales"):
    st.dataframe(
        calendario,
        use_container_width=True
    )

with st.expander("Información metodológica"):
    st.write(
        "Los conteos corresponden a detecciones de "
        "focos activos registradas por NASA FIRMS. "
        "No representan incendios independientes."
    )
    st.write(
        "Los sensores tienen diferentes fechas de inicio, "
        "resoluciones espaciales y sensibilidades. "
        "Las comparaciones directas entre sensores "
        "no constituyen una armonización validada."
    )
    st.write(
        "La delimitación territorial utiliza "
        "FAO GAUL 2015, nivel administrativo 2."
    )
