
import pandas as pd


def preparar_datos(datos):
    """
    Prepara detecciones FIRMS para el análisis temporal.
    No realiza armonización entre sensores.
    """
    df = datos.copy()

    columnas = ["latitude", "longitude", "acq_date"]
    faltantes = [c for c in columnas if c not in df.columns]

    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}")

    df["acq_date"] = pd.to_datetime(
        df["acq_date"], errors="coerce", utc=True
    )

    df["latitude"] = pd.to_numeric(
        df["latitude"], errors="coerce"
    )
    df["longitude"] = pd.to_numeric(
        df["longitude"], errors="coerce"
    )

    df = df.dropna(subset=columnas).copy()

    df = df[
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
    ].copy()

    df["anio"] = df["acq_date"].dt.year
    df["mes"] = df["acq_date"].dt.month
    df["periodo"] = df["acq_date"].dt.strftime("%Y-%m")

    return df


def resumen_mensual(datos):
    """Cuenta detecciones por mes."""
    df = preparar_datos(datos)

    return (
        df.groupby("periodo")
        .size()
        .reset_index(name="detecciones")
        .sort_values("periodo")
    )


def resumen_por_sensor(datos):
    """Cuenta detecciones según el sensor de origen."""
    df = preparar_datos(datos)

    if "sensor_origen" not in df.columns:
        raise ValueError("Falta la columna sensor_origen")

    return (
        df.groupby("sensor_origen")
        .size()
        .reset_index(name="detecciones")
        .sort_values("detecciones", ascending=False)
    )


def comparar_periodos_equivalentes(datos):
    """
    Compara enero–29 de octubre de 2025 y 2026.
    No corrige diferencias de cobertura satelital.
    """
    df = preparar_datos(datos)

    df = df[
        df["anio"].isin([2025, 2026])
        & (
            (df["mes"] < 10)
            | ((df["mes"] == 10) & (df["acq_date"].dt.day <= 29))
        )
    ]

    return (
        df.groupby("anio")
        .size()
        .reset_index(name="detecciones")
    )


if __name__ == "__main__":
    print("SATIF HISTÓRICO — Motor de análisis")
    print("Módulo cargado correctamente")
