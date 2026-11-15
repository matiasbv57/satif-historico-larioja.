
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]

ENTRADA = RAIZ / "data" / "processed" / "firms_la_rioja.csv"
SALIDA = RAIZ / "data" / "processed" / "firms_agrupado.csv"
RESUMEN = RAIZ / "data" / "processed" / "grupos_observacion.csv"

RADIO_KM = 2.0
VENTANA_MINUTOS = 5
RADIO_TIERRA_KM = 6371.0088


def distancia_haversine(lat1, lon1, lat2, lon2):
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin((lon2 - lon1) / 2) ** 2
    )

    return 2 * RADIO_TIERRA_KM * np.arcsin(
        np.sqrt(np.clip(a, 0, 1))
    )


def crear_bloques_temporales(datos):
    datos = datos.sort_values("fecha_hora_utc").copy()

    bloques = []
    bloque_actual = 0
    inicio_bloque = None

    for fecha in datos["fecha_hora_utc"]:
        if (
            inicio_bloque is None
            or (fecha - inicio_bloque).total_seconds() / 60
            > VENTANA_MINUTOS
        ):
            bloque_actual += 1
            inicio_bloque = fecha

        bloques.append(bloque_actual)

    datos["bloque_temporal"] = bloques
    return datos


def componentes_espaciales(datos):
    indices = datos.index.to_list()
    n = len(indices)

    padres = list(range(n))

    def encontrar(i):
        while padres[i] != i:
            padres[i] = padres[padres[i]]
            i = padres[i]
        return i

    def unir(i, j):
        raiz_i = encontrar(i)
        raiz_j = encontrar(j)

        if raiz_i != raiz_j:
            padres[raiz_j] = raiz_i

    latitudes = datos["latitude"].to_numpy()
    longitudes = datos["longitude"].to_numpy()

    for i in range(n):
        if i + 1 >= n:
            continue

        distancias = distancia_haversine(
            latitudes[i],
            longitudes[i],
            latitudes[i + 1:],
            longitudes[i + 1:],
        )

        vecinos = np.where(distancias <= RADIO_KM)[0]

        for vecino in vecinos:
            unir(i, i + 1 + int(vecino))

    componentes = {}

    for i, indice_original in enumerate(indices):
        raiz = encontrar(i)
        componentes.setdefault(raiz, []).append(indice_original)

    return list(componentes.values())


def agrupar_observaciones():
    datos = pd.read_csv(ENTRADA)

    datos["fecha_hora_utc"] = pd.to_datetime(
        datos["fecha_hora_utc"],
        utc=True,
        errors="coerce",
    )

    if datos["fecha_hora_utc"].isna().any():
        raise ValueError("Existen fechas inválidas en el archivo.")

    columnas_obligatorias = [
        "latitude",
        "longitude",
        "sensor_origen",
        "scan",
        "track",
    ]

    faltantes = [
        columna
        for columna in columnas_obligatorias
        if columna not in datos.columns
    ]

    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}")

    datos["grupo_observacion_id"] = ""
    datos["bloque_temporal"] = pd.NA

    numero_grupo = 0

    for sensor, datos_sensor in datos.groupby("sensor_origen"):
        bloques = crear_bloques_temporales(datos_sensor)

        datos.loc[
            bloques.index, "bloque_temporal"
        ] = bloques["bloque_temporal"]

        for _, bloque in bloques.groupby("bloque_temporal"):
            componentes = componentes_espaciales(bloque)

            for componente in componentes:
                numero_grupo += 1

                identificador = f"GO-{numero_grupo:06d}"

                datos.loc[
                    componente, "grupo_observacion_id"
                ] = identificador

    datos["area_pixel_nominal_km2"] = (
        datos["scan"] * datos["track"]
    )

    resumen = (
        datos.groupby(
            ["grupo_observacion_id", "sensor_origen"],
            as_index=False,
        )
        .agg(
            detecciones=("latitude", "size"),
            inicio_utc=("fecha_hora_utc", "min"),
            fin_utc=("fecha_hora_utc", "max"),
            lat_centro=("latitude", "mean"),
            lon_centro=("longitude", "mean"),
            area_pixel_mediana_km2=(
                "area_pixel_nominal_km2", "median"
            ),
            frp_suma_mw=("frp", "sum"),
            frp_max_mw=("frp", "max"),
        )
    )

    SALIDA.parent.mkdir(parents=True, exist_ok=True)

    datos.to_csv(SALIDA, index=False)
    resumen.to_csv(RESUMEN, index=False)

    print("\nSATIF HISTÓRICO — AGRUPACIÓN DE OBSERVACIONES")
    print("----------------------------------------------")
    print(f"Detecciones procesadas: {len(datos):,}")
    print(f"Grupos generados: {len(resumen):,}")
    print(f"Radio espacial: {RADIO_KM} km")
    print(f"Ventana temporal máxima: {VENTANA_MINUTOS} min")

    print("\nGRUPOS POR SENSOR:")
    print(
        resumen.groupby("sensor_origen")
        .size()
        .to_string()
    )

    print("\nTAMAÑO DE LOS GRUPOS:")
    print(
        resumen["detecciones"]
        .describe()
        .round(2)
        .to_string()
    )

    print(f"\nArchivo de detecciones: {SALIDA}")
    print(f"Archivo de grupos: {RESUMEN}")


if __name__ == "__main__":
    agrupar_observaciones()
