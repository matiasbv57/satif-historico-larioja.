
from pathlib import Path

import numpy as np
import pandas as pd

from scipy.spatial import cKDTree


RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "data" / "processed"

ENTRADA = CARPETA / "firms_agrupado_v2.csv"

SALIDA_DETECCIONES = (
    CARPETA / "firms_episodios_candidatos.csv"
)

SALIDA_EPISODIOS = (
    CARPETA / "episodios_candidatos.csv"
)

DISTANCIA_MAXIMA_KM = 2.0
SEPARACION_MAXIMA_HORAS = 24.0

RADIO_TIERRA_KM = 6371.0088


class UnionFind:

    def __init__(self, n):
        self.padre = list(range(n))
        self.tamano = [1] * n

    def buscar(self, x):
        while self.padre[x] != x:
            self.padre[x] = self.padre[
                self.padre[x]
            ]
            x = self.padre[x]

        return x

    def unir(self, a, b):
        raiz_a = self.buscar(a)
        raiz_b = self.buscar(b)

        if raiz_a == raiz_b:
            return

        if (
            self.tamano[raiz_a]
            < self.tamano[raiz_b]
        ):
            raiz_a, raiz_b = raiz_b, raiz_a

        self.padre[raiz_b] = raiz_a
        self.tamano[raiz_a] += (
            self.tamano[raiz_b]
        )


def coordenadas_3d(latitudes, longitudes):

    lat = np.radians(latitudes)
    lon = np.radians(longitudes)

    x = np.cos(lat) * np.cos(lon)
    y = np.cos(lat) * np.sin(lon)
    z = np.sin(lat)

    return np.column_stack([x, y, z])


def separacion_horas(
    inicio_a,
    fin_a,
    inicio_b,
    fin_b,
):
    if fin_a < inicio_b:
        return (
            inicio_b - fin_a
        ).total_seconds() / 3600

    if fin_b < inicio_a:
        return (
            inicio_a - fin_b
        ).total_seconds() / 3600

    return 0.0


def ejecutar():

    datos = pd.read_csv(ENTRADA)

    columnas = [
        "latitude",
        "longitude",
        "fecha_hora_utc",
        "sensor_origen",
        "grupo_observacion_v2",
        "frp",
    ]

    faltantes = [
        c for c in columnas
        if c not in datos.columns
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

    datos["frp"] = pd.to_numeric(
        datos["frp"],
        errors="coerce",
    )


    resumen = (
        datos.groupby(
            "grupo_observacion_v2",
            as_index=False,
        )
        .agg(
            inicio=(
                "fecha_hora_utc", "min"
            ),
            fin=(
                "fecha_hora_utc", "max"
            ),
            lat_centro=("latitude", "mean"),
            lon_centro=("longitude", "mean"),
        )
        .sort_values(
            ["inicio", "grupo_observacion_v2"]
        )
        .reset_index(drop=True)
    )

    n = len(resumen)
    uf = UnionFind(n)


    ids_grupos = resumen[
        "grupo_observacion_v2"
    ].tolist()

    indice_grupo = {
        identificador: i
        for i, identificador in enumerate(
            ids_grupos
        )
    }

    indices_detecciones = datos[
        "grupo_observacion_v2"
    ].map(indice_grupo).to_numpy()

    puntos = coordenadas_3d(
        datos["latitude"].to_numpy(),
        datos["longitude"].to_numpy(),
    )

    arbol = cKDTree(puntos)

    # Distancia de cuerda equivalente a 2 km
    radio_angular = (
        DISTANCIA_MAXIMA_KM
        / RADIO_TIERRA_KM
    )

    radio_cuerda = (
        2 * np.sin(radio_angular / 2)
    )

    pares = arbol.query_pairs(
        r=radio_cuerda,
        output_type="ndarray",
    )


    inicios = resumen["inicio"].tolist()
    finales = resumen["fin"].tolist()

    conexiones_validas = 0

    for punto_a, punto_b in pares:

        grupo_a = indices_detecciones[
            punto_a
        ]

        grupo_b = indices_detecciones[
            punto_b
        ]

        if grupo_a == grupo_b:
            continue

        horas = separacion_horas(
            inicios[grupo_a],
            finales[grupo_a],
            inicios[grupo_b],
            finales[grupo_b],
        )

        if horas <= SEPARACION_MAXIMA_HORAS:
            uf.unir(grupo_a, grupo_b)
            conexiones_validas += 1


    raices = [
        uf.buscar(i)
        for i in range(n)
    ]

    identificadores = {}
    numero = 0

    for raiz in raices:
        if raiz not in identificadores:
            numero += 1
            identificadores[raiz] = (
                f"EP-{numero:06d}"
            )

    resumen["episodio_id"] = [
        identificadores[raiz]
        for raiz in raices
    ]

    mapa_episodios = dict(
        zip(
            resumen["grupo_observacion_v2"],
            resumen["episodio_id"],
        )
    )

    datos["episodio_id"] = (
        datos["grupo_observacion_v2"]
        .map(mapa_episodios)
    )

    episodios = (
        datos.groupby(
            "episodio_id",
            as_index=False,
        )
        .agg(
            detecciones=("latitude", "size"),
            grupos_v2=(
                "grupo_observacion_v2",
                "nunique",
            ),
            sensores=(
                "sensor_origen",
                "nunique",
            ),
            inicio_utc=(
                "fecha_hora_utc",
                "min",
            ),
            fin_utc=(
                "fecha_hora_utc",
                "max",
            ),
            lat_centro=("latitude", "mean"),
            lon_centro=("longitude", "mean"),
            lat_min=("latitude", "min"),
            lat_max=("latitude", "max"),
            lon_min=("longitude", "min"),
            lon_max=("longitude", "max"),
            frp_max_mw=("frp", "max"),
        )
    )

    episodios["duracion_horas"] = (
        episodios["fin_utc"]
        - episodios["inicio_utc"]
    ).dt.total_seconds() / 3600


    if datos["episodio_id"].isna().any():
        raise RuntimeError(
            "Hay detecciones sin episodio."
        )

    if (
        episodios["detecciones"].sum()
        != len(datos)
    ):
        raise RuntimeError(
            "No coinciden las detecciones."
        )

    if (
        episodios["grupos_v2"].sum()
        != n
    ):
        raise RuntimeError(
            "No coinciden los grupos V2."
        )



    datos.to_csv(
        SALIDA_DETECCIONES,
        index=False,
    )

    episodios.to_csv(
        SALIDA_EPISODIOS,
        index=False,
    )


    print(
        "\nSATIF HISTÓRICO — EPISODIOS CANDIDATOS"
    )

    print(
        "----------------------------------------"
    )

    print(
        f"Detecciones: {len(datos):,}"
    )

    print(
        f"Grupos V2: {n:,}"
    )

    print(
        f"Episodios candidatos: {len(episodios):,}"
    )

    print(
        f"Conexiones espaciales-temporales: "
        f"{conexiones_validas:,}"
    )

    print(
        "\nEpisodios con más de un grupo V2:",
        (episodios["grupos_v2"] > 1).sum(),
    )

    print(
        "Episodios con más de un sensor:",
        (episodios["sensores"] > 1).sum(),
    )

    print(
        "\nDURACIÓN DE EPISODIOS (HORAS):"
    )

    print(
        episodios["duracion_horas"]
        .describe()
        .round(2)
        .to_string()
    )

    print(
        "\nMAYORES EPISODIOS POR DETECCIONES:"
    )

    print(
        episodios.nlargest(
            10,
            "detecciones",
        )[
            [
                "episodio_id",
                "detecciones",
                "grupos_v2",
                "sensores",
                "duracion_horas",
            ]
        ].to_string(index=False)
    )

    print(
        "\nArchivos generados:"
    )

    print(SALIDA_DETECCIONES)
    print(SALIDA_EPISODIOS)


if __name__ == "__main__":
    ejecutar()
