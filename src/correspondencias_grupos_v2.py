
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist


RAIZ = Path(__file__).resolve().parents[1]

ENTRADA = (
    RAIZ / "data" / "processed" / "firms_agrupado_v2.csv"
)

SALIDA = (
    RAIZ
    / "data"
    / "processed"
    / "correspondencias_grupos_v2.csv"
)

DISTANCIA_MAXIMA_KM = 2.0
VENTANA_MINUTOS = 60.0
RADIO_TIERRA_KM = 6371.0088

def haversine(u, v):
    lat1, lon1 = np.radians(u)
    lat2, lon2 = np.radians(v)

    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin((lon2 - lon1) / 2) ** 2
    )

    return (
        2
        * RADIO_TIERRA_KM
        * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    )


def preparar_grupos(datos):
    grupos = {}

    for identificador, grupo in datos.groupby(
        "grupo_observacion_v2"
    ):
        coordenadas = grupo[
            ["latitude", "longitude"]
        ].to_numpy(dtype=float)

        grupos[identificador] = {
            "sensor": grupo["sensor_origen"].iloc[0],
            "inicio": grupo["fecha_hora_utc"].min(),
            "fin": grupo["fecha_hora_utc"].max(),
            "coordenadas": coordenadas,
            "detecciones": len(grupo),
            "frp_suma": grupo["frp"].sum(),
            "frp_max": grupo["frp"].max(),
        }

    return grupos


def diferencia_temporal_minutos(grupo_a, grupo_b):
    inicio_a = grupo_a["inicio"]
    fin_a = grupo_a["fin"]

    inicio_b = grupo_b["inicio"]
    fin_b = grupo_b["fin"]

    if fin_a < inicio_b:
        diferencia = inicio_b - fin_a

    elif fin_b < inicio_a:
        diferencia = inicio_a - fin_b

    else:
        diferencia = pd.Timedelta(0)

    return diferencia.total_seconds() / 60


def distancia_minima_grupos(grupo_a, grupo_b):
    distancias = cdist(
        grupo_a["coordenadas"],
        grupo_b["coordenadas"],
        metric=haversine,
    )

    return float(distancias.min())


def ejecutar_correspondencias():
    datos = pd.read_csv(ENTRADA)

    datos["fecha_hora_utc"] = pd.to_datetime(
        datos["fecha_hora_utc"],
        utc=True,
        errors="coerce",
    )

    if datos["fecha_hora_utc"].isna().any():
        raise ValueError(
            "Existen fechas inválidas."
        )

    grupos = preparar_grupos(datos)

    modis = {
        identificador: grupo
        for identificador, grupo in grupos.items()
        if grupo["sensor"] == "MODIS"
    }

    viirs = {
        identificador: grupo
        for identificador, grupo in grupos.items()
        if grupo["sensor"].startswith("VIIRS")
    }

    resultados = []

    for id_modis, grupo_modis in modis.items():
        for id_viirs, grupo_viirs in viirs.items():

            diferencia_minutos = (
                diferencia_temporal_minutos(
                    grupo_modis,
                    grupo_viirs,
                )
            )

            if diferencia_minutos > VENTANA_MINUTOS:
                continue

            distancia_km = distancia_minima_grupos(
                grupo_modis,
                grupo_viirs,
            )

            if distancia_km > DISTANCIA_MAXIMA_KM:
                continue

            resultados.append({
                "grupo_modis": id_modis,
                "grupo_viirs": id_viirs,
                "sensor_viirs": grupo_viirs["sensor"],
                "inicio_modis_utc": grupo_modis["inicio"],
                "inicio_viirs_utc": grupo_viirs["inicio"],
                "distancia_minima_km": round(
                    distancia_km, 4
                ),
                "diferencia_minutos": round(
                    diferencia_minutos, 2
                ),
                "detecciones_modis": (
                    grupo_modis["detecciones"]
                ),
                "detecciones_viirs": (
                    grupo_viirs["detecciones"]
                ),
                "frp_suma_modis_mw": (
                    grupo_modis["frp_suma"]
                ),
                "frp_suma_viirs_mw": (
                    grupo_viirs["frp_suma"]
                ),
                "frp_max_modis_mw": (
                    grupo_modis["frp_max"]
                ),
                "frp_max_viirs_mw": (
                    grupo_viirs["frp_max"]
                ),
            })

    columnas = [
        "grupo_modis",
        "grupo_viirs",
        "sensor_viirs",
        "inicio_modis_utc",
        "inicio_viirs_utc",
        "distancia_minima_km",
        "diferencia_minutos",
        "detecciones_modis",
        "detecciones_viirs",
        "frp_suma_modis_mw",
        "frp_suma_viirs_mw",
        "frp_max_modis_mw",
        "frp_max_viirs_mw",
    ]

    correspondencias = pd.DataFrame(
        resultados,
        columns=columnas,
    )

    SALIDA.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    correspondencias.to_csv(
        SALIDA,
        index=False,
    )

    print(
        "\nSATIF HISTÓRICO — "
        "CORRESPONDENCIAS ENTRE GRUPOS V2"
    )

    print(
        "--------------------------------------------"
    )

    print(
        f"Grupos MODIS disponibles: {len(modis):,}"
    )

    print(
        f"Grupos VIIRS disponibles: {len(viirs):,}"
    )

    print(
        f"Distancia máxima: {DISTANCIA_MAXIMA_KM} km"
    )

    print(
        f"Ventana temporal: ±{VENTANA_MINUTOS} min"
    )

    print(
        f"Correspondencias entre grupos: "
        f"{len(correspondencias):,}"
    )

    if not correspondencias.empty:
        print(
            "Grupos MODIS con correspondencias:",
            correspondencias["grupo_modis"].nunique(),
        )

        print(
            "Grupos VIIRS con correspondencias:",
            correspondencias["grupo_viirs"].nunique(),
        )

        print("\nCORRESPONDENCIAS POR SENSOR VIIRS:")
        print(
            correspondencias[
                "sensor_viirs"
            ].value_counts().to_string()
        )

        print("\nDISTANCIA MÍNIMA ENTRE GRUPOS:")
        print(
            correspondencias[
                "distancia_minima_km"
            ].describe().round(3).to_string()
        )

        print("\nDIFERENCIA TEMPORAL:")
        print(
            correspondencias[
                "diferencia_minutos"
            ].describe().round(2).to_string()
        )

    print(
        f"\nArchivo generado: {SALIDA}"
    )


if __name__ == "__main__":
    ejecutar_correspondencias()
