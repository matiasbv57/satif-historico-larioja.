
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESADOS = BASE_DIR / "data" / "processed"

ARCHIVO_DATOS = PROCESADOS / "firms_la_rioja.csv"
ARCHIVO_GRUPOS = PROCESADOS / "grupos_observacion_v2.csv"
ARCHIVO_DETECCIONES_V2 = PROCESADOS / "firms_agrupado_v2.csv"
ARCHIVO_CORRESPONDENCIAS = (
    PROCESADOS / "correspondencias_grupos_v2.csv"
)

st.set_page_config(
    page_title="SATIF Histórico",
    page_icon="🔥",
    layout="wide",
)

st.title("🔥 SATIF HISTÓRICO")
st.subheader("Plataforma de análisis satelital de anomalías térmicas")

st.caption(
    "Área de estudio: La Rioja, Argentina | "
    "Fuente: NASA FIRMS | "
    "MODIS C6.1 y VIIRS C2"
)

st.info(
    "Los registros NASA FIRMS representan detecciones de "
    "anomalías térmicas. Una detección o un grupo de "
    "observaciones no equivale necesariamente a un incendio "
    "confirmado. Las correspondencias entre sensores son "
    "exploratorias y no constituyen una armonización "
    "radiométrica validada."
)


@st.cache_data
def cargar_csv(ruta):
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {ruta}"
        )

    return pd.read_csv(ruta)


@st.cache_data
def cargar_datos_historicos():
    datos = cargar_csv(ARCHIVO_DATOS).copy()

    columnas = {
        "latitude",
        "longitude",
        "fecha_hora_utc",
        "sensor_origen",
    }

    faltantes = columnas - set(datos.columns)

    if faltantes:
        raise ValueError(
            f"Faltan columnas: {sorted(faltantes)}"
        )

    datos["fecha_hora_utc"] = pd.to_datetime(
        datos["fecha_hora_utc"],
        utc=True,
        errors="coerce",
    )

    for columna in ["latitude", "longitude"]:
        datos[columna] = pd.to_numeric(
            datos[columna],
            errors="coerce",
        )

    datos = datos.dropna(
        subset=[
            "fecha_hora_utc",
            "latitude",
            "longitude",
            "sensor_origen",
        ]
    ).copy()

    datos["periodo"] = (
        datos["fecha_hora_utc"].dt.strftime("%Y-%m")
    )

    return datos


@st.cache_data
def cargar_correspondencias():
    correspondencias = cargar_csv(
        ARCHIVO_CORRESPONDENCIAS
    ).copy()

    fechas = [
        "inicio_modis_utc",
        "inicio_viirs_utc",
    ]

    for columna in fechas:
        correspondencias[columna] = pd.to_datetime(
            correspondencias[columna],
            utc=True,
            errors="coerce",
        )

    correspondencias = correspondencias.dropna(
        subset=fechas
    ).copy()

    return correspondencias


@st.cache_data
def cargar_detecciones_v2():
    datos = cargar_csv(
        ARCHIVO_DETECCIONES_V2
    ).copy()

    datos["fecha_hora_utc"] = pd.to_datetime(
        datos["fecha_hora_utc"],
        utc=True,
        errors="coerce",
    )

    return datos


try:
    datos = cargar_datos_historicos()
except (FileNotFoundError, ValueError) as error:
    st.error(str(error))
    st.stop()

if datos.empty:
    st.warning(
        "La base histórica no contiene registros válidos."
    )
    st.stop()




tab_historico, tab_correspondencias = st.tabs(
    [
        "📊 Explorador histórico",
        "🛰️ Correspondencias MODIS–VIIRS",
    ]
)



with tab_historico:

    st.header("Explorador histórico NASA FIRMS")

    col_filtro_1, col_filtro_2 = st.columns(2)

    sensores = sorted(
        datos["sensor_origen"].unique().tolist()
    )

    with col_filtro_1:
        seleccion = st.multiselect(
            "Seleccionar sensores",
            sensores,
            default=sensores,
            key="sensores_historicos",
        )

    fecha_inicio = (
        datos["fecha_hora_utc"].min().date()
    )

    fecha_fin = (
        datos["fecha_hora_utc"].max().date()
    )

    with col_filtro_2:
        rango_fechas = st.date_input(
            "Período de análisis",
            value=(fecha_inicio, fecha_fin),
            min_value=fecha_inicio,
            max_value=fecha_fin,
            key="fechas_historicas",
        )

    datos_filtrados = datos[
        datos["sensor_origen"].isin(seleccion)
    ].copy()

    if len(rango_fechas) == 2:
        inicio, fin = rango_fechas

        datos_filtrados = datos_filtrados[
            datos_filtrados["fecha_hora_utc"]
            .dt.date.between(inicio, fin)
        ]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Detecciones satelitales",
        f"{len(datos_filtrados):,}",
    )

    col2.metric(
        "Sensores seleccionados",
        len(seleccion),
    )

    col3.metric(
        "Meses con registros",
        datos_filtrados["periodo"].nunique(),
    )

    st.divider()

    if datos_filtrados.empty:
        st.info(
            "No hay detecciones para los filtros seleccionados."
        )

    else:

        # EVOLUCIÓN MENSUAL
        st.subheader("Evolución mensual por sensor")

        mensual_sensor = (
            datos_filtrados
            .groupby(["periodo", "sensor_origen"])
            .size()
            .reset_index(name="detecciones")
            .sort_values("periodo")
        )

        mensual_sensor["fecha_mes"] = pd.to_datetime(
            mensual_sensor["periodo"] + "-01"
        )

        figura_mensual = px.line(
            mensual_sensor,
            x="fecha_mes",
            y="detecciones",
            color="sensor_origen",
            markers=True,
            labels={
                "fecha_mes": "Mes",
                "detecciones": "Detecciones satelitales",
                "sensor_origen": "Sensor",
            },
        )

        figura_mensual.update_layout(
            hovermode="x unified",
            legend_title_text="Satélite / sensor",
            xaxis_title="Mes de adquisición (UTC)",
            yaxis_title="Cantidad de detecciones",
        )

        figura_mensual.update_xaxes(
            tickformat="%b %Y",
            dtick="M2",
            hoverformat="%B %Y",
        )

        st.plotly_chart(
            figura_mensual,
            width="stretch",
        )

        # DISTRIBUCIÓN POR SENSOR
        st.subheader("Distribución por sensor")

        por_sensor = (
            datos_filtrados
            .groupby("sensor_origen")
            .size()
            .reset_index(name="detecciones")
            .sort_values(
                "detecciones",
                ascending=False,
            )
        )

        figura_sensores = px.bar(
            por_sensor,
            x="sensor_origen",
            y="detecciones",
            color="sensor_origen",
            labels={
                "sensor_origen": "Sensor",
                "detecciones": "Detecciones satelitales",
            },
        )

        st.plotly_chart(
            figura_sensores,
            width="stretch",
        )

        # MAPA HISTÓRICO
        st.subheader(
            "Distribución espacial de detecciones"
        )

        st.map(
            datos_filtrados,
            latitude="latitude",
            longitude="longitude",
        )

        with st.expander(
            "Ver registros NASA FIRMS"
        ):
            st.dataframe(
                datos_filtrados,
                width="stretch",
            )


with tab_correspondencias:

    st.header(
        "Correspondencias entre grupos MODIS–VIIRS"
    )

    st.caption(
        "Método V2: agrupación espacial de enlace completo "
        "con diámetro máximo de 2 km, ventana temporal de "
        "agrupación de 5 minutos y búsqueda de correspondencias "
        "entre grupos con distancia mínima de 2 km y "
        "separación temporal máxima de 60 minutos."
    )

    try:
        correspondencias = cargar_correspondencias()
        detecciones_v2 = cargar_detecciones_v2()
        grupos_v2 = cargar_csv(ARCHIVO_GRUPOS)

    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))
        st.stop()

    if correspondencias.empty:
        st.warning(
            "No hay correspondencias entre grupos disponibles."
        )

    else:

        # INDICADORES GENERALES
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Correspondencias entre grupos",
            f"{len(correspondencias):,}",
        )

        col2.metric(
            "Grupos MODIS vinculados",
            correspondencias["grupo_modis"].nunique(),
        )

        col3.metric(
            "Grupos VIIRS vinculados",
            correspondencias["grupo_viirs"].nunique(),
        )

        st.caption(
            f"Grupos V2 disponibles: {len(grupos_v2):,} | "
            f"Detecciones V2: {len(detecciones_v2):,}"
        )

        st.divider()

        # FILTROS
        st.subheader("Filtros de correspondencias")

        f1, f2 = st.columns(2)

        sensores_viirs = sorted(
            correspondencias[
                "sensor_viirs"
            ].unique().tolist()
        )

        with f1:
            sensores_seleccionados = st.multiselect(
                "Satélites VIIRS",
                sensores_viirs,
                default=sensores_viirs,
                key="sensores_correspondencias",
            )

        with f2:
            distancia_maxima = st.slider(
                "Distancia máxima entre grupos (km)",
                min_value=0.1,
                max_value=2.0,
                value=2.0,
                step=0.1,
                key="distancia_correspondencias",
            )

        f3, f4 = st.columns(2)

        with f3:
            tiempo_maximo = st.slider(
                "Diferencia temporal máxima (min)",
                min_value=0,
                max_value=60,
                value=60,
                step=5,
                key="tiempo_correspondencias",
            )

        fecha_minima = (
            correspondencias[
                "inicio_modis_utc"
            ].min().date()
        )

        fecha_maxima = (
            correspondencias[
                "inicio_modis_utc"
            ].max().date()
        )

        with f4:
            fechas_correspondencias = st.date_input(
                "Período de correspondencias (UTC)",
                value=(fecha_minima, fecha_maxima),
                min_value=fecha_minima,
                max_value=fecha_maxima,
                key="fechas_correspondencias",
            )

        filtradas = correspondencias[
            correspondencias[
                "sensor_viirs"
            ].isin(sensores_seleccionados)
        ].copy()

        filtradas = filtradas[
            (
                filtradas["distancia_minima_km"]
                <= distancia_maxima
            )
            &
            (
                filtradas["diferencia_minutos"]
                <= tiempo_maximo
            )
        ]

        if len(fechas_correspondencias) == 2:
            inicio, fin = fechas_correspondencias

            filtradas = filtradas[
                filtradas["inicio_modis_utc"]
                .dt.date.between(inicio, fin)
            ]

        st.divider()

        if filtradas.empty:
            st.info(
                "No existen correspondencias para "
                "los filtros seleccionados."
            )

        else:

            # INDICADORES FILTRADOS
            a, b, c = st.columns(3)

            a.metric(
                "Correspondencias filtradas",
                len(filtradas),
            )

            b.metric(
                "Distancia mediana",
                f"{filtradas['distancia_minima_km'].median():.3f} km",
            )

            c.metric(
                "Diferencia temporal mediana",
                f"{filtradas['diferencia_minutos'].median():.1f} min",
            )

            # GRÁFICO POR SATÉLITE
            st.subheader(
                "Correspondencias por satélite VIIRS"
            )

            resumen_sensores = (
                filtradas.groupby("sensor_viirs")
                .size()
                .reset_index(name="correspondencias")
            )

            figura = px.bar(
                resumen_sensores,
                x="sensor_viirs",
                y="correspondencias",
                color="sensor_viirs",
                labels={
                    "sensor_viirs": "Satélite VIIRS",
                    "correspondencias": "Correspondencias",
                },
            )

            st.plotly_chart(
                figura,
                width="stretch",
            )

            # DISTANCIA VS TIEMPO
            st.subheader(
                "Distancia y diferencia temporal"
            )

            figura_dispersion = px.scatter(
                filtradas,
                x="diferencia_minutos",
                y="distancia_minima_km",
                color="sensor_viirs",
                hover_data=[
                    "grupo_modis",
                    "grupo_viirs",
                    "detecciones_modis",
                    "detecciones_viirs",
                ],
                labels={
                    "diferencia_minutos": (
                        "Separación temporal (min)"
                    ),
                    "distancia_minima_km": (
                        "Distancia mínima (km)"
                    ),
                    "sensor_viirs": "Satélite VIIRS",
                },
            )

            st.plotly_chart(
                figura_dispersion,
                width="stretch",
            )

            # TABLA DE CORRESPONDENCIAS
            st.subheader(
                "Tabla de correspondencias"
            )

            tabla = filtradas.sort_values(
                [
                    "inicio_modis_utc",
                    "distancia_minima_km",
                ]
            ).copy()

            st.dataframe(
                tabla,
                width="stretch",
                hide_index=True,
            )

            st.download_button(
                "Descargar correspondencias filtradas (CSV)",
                data=tabla.to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name=(
                    "SATIF_correspondencias_grupos_v2.csv"
                ),
                mime="text/csv",
            )

            # MAPA DE UNA CORRESPONDENCIA
            st.divider()

            st.subheader(
                "Inspección geográfica de una correspondencia"
            )

            opciones = tabla.reset_index(drop=True)

            opciones["etiqueta"] = (
                opciones["grupo_modis"]
                + " ↔ "
                + opciones["grupo_viirs"]
                + " | "
                + opciones["sensor_viirs"]
                + " | "
                + opciones["distancia_minima_km"]
                .round(2)
                .astype(str)
                + " km"
            )

            indice_seleccionado = st.selectbox(
                "Seleccionar correspondencia",
                options=opciones.index.tolist(),
                format_func=lambda i: opciones.loc[
                    i, "etiqueta"
                ],
                key="seleccion_correspondencia",
            )

            seleccion_actual = opciones.loc[
                indice_seleccionado
            ]

            id_modis = seleccion_actual["grupo_modis"]
            id_viirs = seleccion_actual["grupo_viirs"]

            puntos_modis = detecciones_v2[
                detecciones_v2[
                    "grupo_observacion_v2"
                ] == id_modis
            ].copy()

            puntos_viirs = detecciones_v2[
                detecciones_v2[
                    "grupo_observacion_v2"
                ] == id_viirs
            ].copy()

            puntos_mapa = pd.concat(
                [puntos_modis, puntos_viirs],
                ignore_index=True,
            )

            st.write(
                f"**Grupo MODIS:** {id_modis} "
                f"({len(puntos_modis)} detecciones)"
            )

            st.write(
                f"**Grupo VIIRS:** {id_viirs} "
                f"({len(puntos_viirs)} detecciones)"
            )

            st.write(
                "**Distancia mínima entre grupos:** "
                f"{seleccion_actual['distancia_minima_km']:.3f} km"
            )

            st.write(
                "**Diferencia temporal:** "
                f"{seleccion_actual['diferencia_minutos']:.1f} min"
            )


            if not puntos_mapa.empty:

                # Centro geográfico de las detecciones
                lat_centro = puntos_mapa["latitude"].mean()
                lon_centro = puntos_mapa["longitude"].mean()
                tipo_mapa = st.radio(
                    "Base cartográfica",
                    options=[
                        "Mapa de calles",
                        "Imagen satelital",
                    ],
                    horizontal=True,
                    key="tipo_mapa_correspondencias",
                )

                estilos_mapa = {
                    "Mapa de calles": "open-street-map",
                    "Imagen satelital": "white-bg",
                }

                # Simbología diferenciada
                colores = {
                    "MODIS": "#FF3B30",
                    "VIIRS_NOAA20": "#00BFFF",
                    "VIIRS_NOAA21": "#00BFFF",
                    "VIIRS_S_NPP": "#00BFFF",
                }

                figura_mapa = px.scatter_map(
                    puntos_mapa,
                    lat="latitude",
                    lon="longitude",
                    color="sensor_origen",
                    color_discrete_map=colores,
                    hover_name="grupo_observacion_v2",
                    hover_data={
                        "fecha_hora_utc": True,
                        "frp": True,
                        "latitude": ":.6f",
                        "longitude": ":.6f",
                    },
                    center={
                        "lat": lat_centro,
                        "lon": lon_centro,
                    },
                    zoom=13,
                    height=600,
                    labels={
                        "sensor_origen": "Sensor",
                    },
                )

                figura_mapa.update_traces(
                    marker={"size": 17, "opacity": 0.9}
                )



                import numpy as np
                import plotly.graph_objects as go

                if (
                    not puntos_modis.empty
                    and not puntos_viirs.empty
                ):

                    coords_modis = puntos_modis[
                        ["latitude", "longitude"]
                    ].to_numpy(dtype=float)

                    coords_viirs = puntos_viirs[
                        ["latitude", "longitude"]
                    ].to_numpy(dtype=float)

                    lat_m = np.radians(
                        coords_modis[:, 0]
                    )[:, None]

                    lon_m = np.radians(
                        coords_modis[:, 1]
                    )[:, None]

                    lat_v = np.radians(
                        coords_viirs[:, 0]
                    )[None, :]

                    lon_v = np.radians(
                        coords_viirs[:, 1]
                    )[None, :]

                    a = (
                        np.sin((lat_v - lat_m) / 2) ** 2
                        + np.cos(lat_m)
                        * np.cos(lat_v)
                        * np.sin((lon_v - lon_m) / 2) ** 2
                    )

                    distancias = (
                        2
                        * 6371.0088
                        * np.arcsin(
                            np.sqrt(np.clip(a, 0, 1))
                        )
                    )

                    indice_modis, indice_viirs = (
                        np.unravel_index(
                            np.argmin(distancias),
                            distancias.shape,
                        )
                    )

                    punto_modis = coords_modis[
                        indice_modis
                    ]

                    punto_viirs = coords_viirs[
                        indice_viirs
                    ]

                    distancia_real = float(
                        distancias[
                            indice_modis,
                            indice_viirs,
                        ]
                    )

                    figura_mapa.add_trace(
                        go.Scattermap(
                            lat=[
                                punto_modis[0],
                                punto_viirs[0],
                            ],
                            lon=[
                                punto_modis[1],
                                punto_viirs[1],
                            ],
                            mode="lines",
                            line=dict(
                                width=4,
                                color="#FFD700",
                            ),
                            name="Distancia mínima",
                            hovertemplate=(
                                "Distancia entre centros: "
                                f"{distancia_real:.3f} km"
                                "<extra></extra>"
                            ),
                        )
                    )

                    st.caption(
                        "Línea amarilla: une los dos "
                        "centros de detección más próximos. "
                        f"Distancia calculada: "
                        f"{distancia_real:.3f} km."
                    )


                figura_mapa.update_layout(
                    map_style=estilos_mapa[tipo_mapa],
                    margin=dict(
                        l=0,
                        r=0,
                        t=0,
                        b=0,
                    ),
                    legend=dict(
                        title="Sensor satelital",
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="left",
                        x=0,
                    ),
                )
                if tipo_mapa == "Imagen satelital":
                    figura_mapa.update_layout(
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
                        ]
                    )

                st.plotly_chart(
                    figura_mapa,
                    width="stretch",
                )


            with st.expander(
                "Ver detecciones originales de ambos grupos"
            ):
                st.dataframe(
                    puntos_mapa,
                    width="stretch",
                    hide_index=True,
                )

            st.warning(
                "La correspondencia se establece por "
                "proximidad espacial y temporal. "
                "No confirma un incendio individual "
                "ni permite equiparar directamente "
                "los valores FRP de MODIS y VIIRS."
            )


st.divider()

st.caption(
    "SATIF Histórico | NASA FIRMS | "
    "MODIS C6.1 y VIIRS C2 | "
    "Recorte mediante polígono operativo de La Rioja | "
    "Agrupación espacial V2 | "
    "Correspondencias exploratorias entre sensores | "
    "Sin armonización radiométrica validada."
)
