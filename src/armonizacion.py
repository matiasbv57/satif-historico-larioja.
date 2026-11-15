
from pathlib import Path

import numpy as np
import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "data" / "processed" / "firms_la_rioja.csv"
SALIDA = RAIZ / "data" / "processed" / "correspondencias_modis_viirs.csv"

RADIO_KM = 3.0
VENTANA_MINUTOS = 90.0
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

    return (
        2 * RADIO_TIERRA_KM
        * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    )


def buscar_correspondencias():
    datos = pd.read_csv(ENTRADA)

    datos["fecha_hora_utc"] = pd.to_datetime(
        datos["fecha_hora_utc"],
        utc=True,
    )

    modis = datos[
        datos["sensor_origen"] == "MODIS"
    ].copy()

    viirs = datos[
        datos["sensor_origen"].str.startswith("VIIRS")
    ].copy()

    resultados = []

    for indice_modis, punto_modis in modis.iterrows():

        diferencia_minutos = (
            (
                viirs["fecha_hora_utc"]
                - punto_modis["fecha_hora_utc"]
            )
            .abs()
            .dt.total_seconds()
            / 60
        )

        candidatos = viirs.loc[
            diferencia_minutos <= VENTANA_MINUTOS
        ].copy()

        if candidatos.empty:
            continue

        candidatos["distancia_km"] = distancia_haversine(
            punto_modis["latitude"],
            punto_modis["longitude"],
            candidatos["latitude"].to_numpy(),
            candidatos["longitude"].to_numpy(),
        )

        candidatos = candidatos[
            candidatos["distancia_km"] <= RADIO_KM
        ]

        for indice_viirs, punto_viirs in candidatos.iterrows():

            diferencia = abs(
                (
                    punto_viirs["fecha_hora_utc"]
                    - punto_modis["fecha_hora_utc"]
                ).total_seconds()
            ) / 60

            resultados.append({
                "id_modis": indice_modis,
                "id_viirs": indice_viirs,
                "fecha_modis_utc": punto_modis["fecha_hora_utc"],
                "fecha_viirs_utc": punto_viirs["fecha_hora_utc"],
                "sensor_viirs": punto_viirs["sensor_origen"],
                "lat_modis": punto_modis["latitude"],
                "lon_modis": punto_modis["longitude"],
                "lat_viirs": punto_viirs["latitude"],
                "lon_viirs": punto_viirs["longitude"],
                "distancia_km": round(
                    punto_viirs["distancia_km"], 4
                ),
                "diferencia_minutos": round(diferencia, 2),
                "frp_modis_mw": punto_modis.get("frp"),
                "frp_viirs_mw": punto_viirs.get("frp"),
                "confianza_modis": punto_modis.get("confidence"),
                "confianza_viirs": punto_viirs.get("confidence"),
            })

    columnas = [
        "id_modis",
        "id_viirs",
        "fecha_modis_utc",
        "fecha_viirs_utc",
        "sensor_viirs",
        "lat_modis",
        "lon_modis",
        "lat_viirs",
        "lon_viirs",
        "distancia_km",
        "diferencia_minutos",
        "frp_modis_mw",
        "frp_viirs_mw",
        "confianza_modis",
        "confianza_viirs",
    ]

    correspondencias = pd.DataFrame(
        resultados,
        columns=columnas,
    )

    SALIDA.parent.mkdir(parents=True, exist_ok=True)

    correspondencias.to_csv(
        SALIDA,
        index=False,
    )

    print("\nSATIF HISTÓRICO — CORRESPONDENCIAS MODIS–VIIRS")
    print("----------------------------------------------")
    print(f"Detecciones MODIS: {len(modis):,}")
    print(f"Detecciones VIIRS: {len(viirs):,}")
    print(f"Radio espacial: {RADIO_KM} km")
    print(f"Ventana temporal: ±{VENTANA_MINUTOS} minutos")
    print(f"Pares candidatos: {len(correspondencias):,}")

    if not correspondencias.empty:
        print(
            "Detecciones MODIS con candidatos:",
            correspondencias["id_modis"].nunique(),
        )
        print(
            "Detecciones VIIRS con candidatos:",
            correspondencias["id_viirs"].nunique(),
        )

    print(f"\nArchivo generado: {SALIDA}")


if __name__ == "__main__":
    buscar_correspondencias()
