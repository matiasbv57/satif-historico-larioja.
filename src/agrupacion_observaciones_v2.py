
from pathlib import Path

import numpy as np
import pandas as pd

from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform


RAIZ = Path(__file__).resolve().parents[1]

ENTRADA = RAIZ / "data" / "processed" / "firms_la_rioja.csv"

SALIDA_DETECCIONES = (
    RAIZ / "data" / "processed" / "firms_agrupado_v2.csv"
)

SALIDA_GRUPOS = (
    RAIZ / "data" / "processed" / "grupos_observacion_v2.csv"
)

RADIO_MAXIMO_KM = 2.0
VENTANA_MINUTOS = 5

RADIO_TIERRA_KM = 6371.0088



def haversine_vector(u, v):
    lat1, lon1 = np.radians(u)
    lat2, lon2 = np.radians(v)

    diferencia_lat = lat2 - lat1
    diferencia_lon = lon2 - lon1

    a = (
        np.sin(diferencia_lat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(diferencia_lon / 2) ** 2
    )

    return (
        2
        * RADIO_TIERRA_KM
        * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    )


def calcular_diametro(datos):
    if len(datos) <= 1:
        return 0.0

    coordenadas = datos[
        ["latitude", "longitude"]
    ].to_numpy(dtype=float)

    distancias = pdist(
        coordenadas,
        metric=haversine_vector,
    )

    return float(distancias.max())


def crear_bloques_temporales(datos):
    datos = datos.sort_values(
        "fecha_hora_utc"
    ).copy()

    bloques = []
    numero_bloque = 0
    inicio_bloque = None

    for fecha in datos["fecha_hora_utc"]:
        if (
            inicio_bloque is None
            or (
                fecha - inicio_bloque
            ).total_seconds() / 60 > VENTANA_MINUTOS
        ):
            numero_bloque += 1
            inicio_bloque = fecha

        bloques.append(numero_bloque)

    datos["bloque_temporal_v2"] = bloques

    return datos


def agrupar_espacialmente(datos):
    if len(datos) == 1:
        return [datos.index.to_list()]

    coordenadas = datos[
        ["latitude", "longitude"]
    ].to_numpy(dtype=float)

    distancias = pdist(
        coordenadas,
        metric=haversine_vector,
    )

    arbol = linkage(
        distancias,
        method="complete",
    )

    etiquetas = fcluster(
        arbol,
        t=RADIO_MAXIMO_KM,
        criterion="distance",
    )

    grupos = []

    for etiqueta in np.unique(etiquetas):
        indices = datos.index[
            etiquetas == etiqueta
        ].to_list()

        grupos.append(indices)

    return grupos


def ejecutar_agrupacion_v2():
    datos = pd.read_csv(ENTRADA)

    columnas_necesarias = [
        "latitude",
        "longitude",
        "fecha_hora_utc",
        "sensor_origen",
        "scan",
        "track",
        "frp",
    ]

    faltantes = [
        columna
        for columna in columnas_necesarias
        if columna not in datos.columns
    ]

    if faltantes:
        raise ValueError(
            f"Faltan columnas: {faltantes}"
        )

    datos["fecha_hora_utc"] = pd.to_datetime(
        datos["fecha_hora_utc"],
        utc=True,
        errors="coerce",
    )

    if datos["fecha_hora_utc"].isna().any():
        raise ValueError(
            "Existen fechas inválidas."
        )

    if datos[
        ["latitude", "longitude"]
    ].isna().any().any():
        raise ValueError(
            "Existen coordenadas nulas."
        )

    datos["grupo_observacion_v2"] = ""
    datos["bloque_temporal_v2"] = pd.NA

    datos["area_pixel_nominal_km2"] = (
        datos["scan"] * datos["track"]
    )

    numero_grupo = 0

    for sensor, datos_sensor in datos.groupby(
        "sensor_origen"
    ):
        bloques = crear_bloques_temporales(
            datos_sensor
        )

        datos.loc[
            bloques.index,
            "bloque_temporal_v2"
        ] = bloques["bloque_temporal_v2"]

        for _, bloque in bloques.groupby(
            "bloque_temporal_v2"
        ):
            grupos = agrupar_espacialmente(
                bloque
            )

            for indices in grupos:
                numero_grupo += 1

                identificador = (
                    f"GOV2-{numero_grupo:06d}"
                )

                datos.loc[
                    indices,
                    "grupo_observacion_v2"
                ] = identificador


    resumen = (
        datos.groupby(
            [
                "grupo_observacion_v2",
                "sensor_origen",
            ],
            as_index=False,
        )
        .agg(
            detecciones=("latitude", "size"),
            inicio_utc=(
                "fecha_hora_utc", "min"
            ),
            fin_utc=(
                "fecha_hora_utc", "max"
            ),
            lat_centro=("latitude", "mean"),
            lon_centro=("longitude", "mean"),
            area_pixel_mediana_km2=(
                "area_pixel_nominal_km2",
                "median",
            ),
            frp_suma_mw=("frp", "sum"),
            frp_max_mw=("frp", "max"),
        )
    )

    # Diámetro geográfico de cada grupo
    diametros = (
        datos.groupby("grupo_observacion_v2")
        .apply(
            calcular_diametro,
            include_groups=False,
        )
    )

    resumen["diametro_km"] = (
        resumen["grupo_observacion_v2"]
        .map(diametros)
    )



    if datos[
        "grupo_observacion_v2"
    ].eq("").any():
        raise RuntimeError(
            "Hay detecciones sin grupo."
        )

    if resumen["detecciones"].sum() != len(datos):
        raise RuntimeError(
            "La cantidad de detecciones no coincide."
        )

    tolerancia = 1e-6

    if (
        resumen["diametro_km"]
        > RADIO_MAXIMO_KM + tolerancia
    ).any():
        raise RuntimeError(
            "Existen grupos que superan "
            "el diámetro permitido."
        )

    duracion = (
        resumen["fin_utc"]
        - resumen["inicio_utc"]
    ).dt.total_seconds() / 60

    if (duracion > VENTANA_MINUTOS).any():
        raise RuntimeError(
            "Existen grupos fuera de "
            "la ventana temporal."
        )


    SALIDA_DETECCIONES.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    datos.to_csv(
        SALIDA_DETECCIONES,
        index=False,
    )

    resumen.to_csv(
        SALIDA_GRUPOS,
        index=False,
    )



    print(
        "\nSATIF HISTÓRICO — AGRUPACIÓN V2"
    )
    print(
        "--------------------------------"
    )

    print(
        f"Detecciones: {len(datos):,}"
    )
    print(
        f"Grupos V2: {len(resumen):,}"
    )

    print(
        f"Diámetro permitido: "
        f"{RADIO_MAXIMO_KM} km"
    )

    print(
        f"Diámetro máximo observado: "
        f"{resumen['diametro_km'].max():.3f} km"
    )

    print(
        f"Duración máxima observada: "
        f"{duracion.max():.1f} min"
    )

    print("\nGRUPOS POR SENSOR:")
    print(
        resumen.groupby("sensor_origen")
        .size()
        .to_string()
    )

    print("\nTAMAÑO DE GRUPOS:")
    print(
        resumen["detecciones"]
        .describe()
        .round(2)
        .to_string()
    )

    print(
        "\nGrupos con más de una detección:",
        (resumen["detecciones"] > 1).sum(),
    )

    print(
        "\nGrupos con diámetro mayor a 2 km:",
        (resumen["diametro_km"] > 2.000001).sum(),
    )

    print(
        "\nArchivo de detecciones:",
        SALIDA_DETECCIONES,
    )

    print(
        "Archivo de grupos:",
        SALIDA_GRUPOS,
    )


if __name__ == "__main__":
    ejecutar_agrupacion_v2()
