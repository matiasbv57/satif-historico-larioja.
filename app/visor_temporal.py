
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
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

COLORES = [
    "#00BFFF",
    "#FFD700",
    "#FF6B35",
    "#E63946",
    "#B388FF",
    "#00E5A0",
    "#FF99C8",
    "#FFFFFF",
    "#9ACD32",
    "#FF8C00",
    "#7FDBFF",
    "#C77DFF",
]


# ==========================================
# CARGA DE DATOS
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

st.subheader(
    "Evolución espacial y temporal"
)

st.caption(
    "Análisis exploratorio de detecciones "
    "térmicas NASA FIRMS. Los episodios "
    "candidatos no representan incendios "
    "individuales confirmados."
)


# ==========================================
# CONTROLES
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

modo = st.radio(
    "Modalidad de visualización",
    ["Diaria", "Acumulada"],
    horizontal=True,
)

tipo_mapa = st.radio(
    "Base cartográfica",
    ["Imagen satelital", "Mapa de calles"],
    horizontal=True,
)

st.caption(
    "Utilizá los controles del mapa para "
    "reproducir, pausar o avanzar por día."
)


# ==========================================
# INDICADORES
# ==========================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Detecciones del episodio",
    len(filtrado),
)

c2.metric(
    "Grupos V2",
    filtrado[
        "grupo_observacion_v2"
    ].nunique(),
)

c3.metric(
    "Sensores",
    filtrado[
        "sensor_origen"
    ].nunique(),
)

c4.metric(
    "Días con detecciones",
    len(dias),
)


# ==========================================
# CENTRO Y ENCUADRE FIJO
# ==========================================

centro = dict(
    lat=float(
        (
            filtrado["latitude"].min()
            + filtrado["latitude"].max()
        ) / 2
    ),
    lon=float(
        (
            filtrado["longitude"].min()
            + filtrado["longitude"].max()
        ) / 2
    ),
)


# ==========================================
# CREACIÓN DE TRAZAS
# ==========================================


# ==========================================
# CREACIÓN DE TRAZAS
# ==========================================

def crear_traza_dia(fecha, indice):

    puntos = filtrado[
        filtrado["dia_utc"] == fecha
    ]

    color = COLORES[
        indice % len(COLORES)
    ]

    textos = [
        (
            f"Fecha UTC: {fila.dia_utc}"
            f"<br>Sensor: {fila.sensor_origen}"
            f"<br>Hora UTC: {fila.fecha_hora_utc}"
            f"<br>FRP: {fila.frp} MW"
            f"<br>Grupo V2: "
            f"{fila.grupo_observacion_v2}"
        )
        for fila in puntos.itertuples()
    ]

    return go.Scattermap(
        lat=puntos["latitude"],
        lon=puntos["longitude"],
        mode="markers",
        marker=dict(
            size=12,
            color=color,
            opacity=0.85,
        ),
        name=fecha,
        text=textos,
        hovertemplate="%{text}<extra></extra>",
        showlegend=True,
    )


# ==========================================
# MAPA ANIMADO
# ==========================================

st.subheader(
    "Evolución temporal de las detecciones"
)

figura = go.Figure()

# Una traza permanente por cada día
for indice, fecha in enumerate(dias):

    traza = crear_traza_dia(
        fecha,
        indice,
    )

    traza.visible = (
        indice == 0
    )

    figura.add_trace(traza)
    figura.update_layout(
    map=dict(
        style="open-street-map",
        center=centro,
        zoom=10,
    ),
    height=750,
)




fotogramas = []

for indice_actual, fecha in enumerate(dias):

    visibilidad = []

    for indice in range(len(dias)):

        if modo == "Diaria":
            visible = (
                indice == indice_actual
            )

        else:
            visible = (
                indice <= indice_actual
            )

        visibilidad.append(visible)

    fotogramas.append(
        go.Frame(
            name=fecha,
            data=[
                go.Scattermap(
                    visible=visible
                )
                for visible in visibilidad
            ],
            traces=list(range(len(dias))),
            layout=go.Layout(
                title_text=(
                    f"{episodio} — {fecha} "
                    f"({modo})"
                )
            ),
        )
    )

figura.frames = fotogramas




st.subheader(
    "Evolución temporal de las detecciones"
)

figura = go.Figure()




pasos = []

for fecha in dias:

    pasos.append(
        dict(
            method="animate",
            label=fecha,
            args=[
                [fecha],
                dict(
                    mode="immediate",
                    frame=dict(
                        duration=0,
                        redraw=True,
                    ),
                    transition=dict(
                        duration=0
                    ),
                ),
            ],
        )
    )

figura.update_layout(
    title=f"{episodio} — {dias[0]} ({modo})",
    height=750,
    margin=dict(
        l=0,
        r=0,
        t=55,
        b=90,
    ),
    map=dict(
        center=centro,
        zoom=10,
    ),
    legend=dict(
        title="Día UTC",
        orientation="v",
    ),
    updatemenus=[
        dict(
            type="buttons",
            showactive=False,
            direction="left",
            x=0.02,
            y=-0.08,
            buttons=[
                dict(
                    label="▶ Reproducir",
                    method="animate",
                    args=[
                        None,
                        dict(
                            fromcurrent=True,
                            mode="immediate",
                            frame=dict(
                                duration=1200,
                                redraw=True,
                            ),
                            transition=dict(
                                duration=0
                            ),
                        ),
                    ],
                ),
                dict(
                    label="⏸ Pausar",
                    method="animate",
                    args=[
                        [None],
                        dict(
                            mode="immediate",
                            frame=dict(
                                duration=0,
                                redraw=True,
                            ),
                            transition=dict(
                                duration=0
                            ),
                        ),
                    ],
                ),
            ],
        )
    ],
    sliders=[
        dict(
            active=0,
            currentvalue=dict(
                prefix="Fecha UTC: "
            ),
            pad=dict(t=45),
            steps=pasos,
        )
    ],
)



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

else:

    figura.update_layout(
        map_style="open-street-map"
    )



st.plotly_chart(
    figura,
    use_container_width=True,
    config={
        "scrollZoom": True,
        "displaylogo": False,
    },
)



st.subheader(
    "Actividad térmica detectada por día"
)

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

import plotly.express as px

grafico = px.bar(
    diario,
    x="dia_utc",
    y="detecciones",
    labels={
        "dia_utc": "Fecha UTC",
        "detecciones": "Detecciones",
    },
)

st.plotly_chart(
    grafico,
    use_container_width=True,
)


with st.expander(
    "Consultar detecciones del episodio"
):

    st.dataframe(
        filtrado,
        use_container_width=True,
    )

st.download_button(
    "Descargar episodio completo (CSV)",
    data=filtrado.to_csv(
        index=False
    ).encode("utf-8"),
    file_name=f"{episodio}_completo.csv",
    mime="text/csv",
)

st.caption(
    "La visualización acumulada representa "
    "detecciones registradas hasta cada fecha, "
    "no superficie quemada. La base satelital "
    "Esri no necesariamente corresponde a la "
    "fecha histórica de las observaciones."
)
