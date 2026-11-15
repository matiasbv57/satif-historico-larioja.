
from pathlib import Path
import pandas as pd

# Directorios del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"

# Campos comunes de los registros NASA FIRMS
COLUMNAS_REQUERIDAS = [
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
]


def cargar_firms(ruta_archivo):
    """Carga y valida un archivo CSV de detecciones FIRMS."""

    ruta = Path(ruta_archivo)

    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")

    datos = pd.read_csv(ruta)

    faltantes = [
        columna
        for columna in COLUMNAS_REQUERIDAS
        if columna not in datos.columns
    ]

    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}")

    datos["acq_date"] = pd.to_datetime(
        datos["acq_date"], errors="coerce", utc=True
    )

    datos["latitude"] = pd.to_numeric(
        datos["latitude"], errors="coerce"
    )
    datos["longitude"] = pd.to_numeric(
        datos["longitude"], errors="coerce"
    )

    datos = datos.dropna(
        subset=["latitude", "longitude", "acq_date"]
    )

    datos = datos[
        datos["latitude"].between(-90, 90)
        & datos["longitude"].between(-180, 180)
    ].copy()

    return datos


if __name__ == "__main__":
    print("SATIF HISTÓRICO — Módulo de lectura FIRMS")
    print(f"Directorio de datos: {DATA_RAW}")
    print("Estado: preparado para importar archivos CSV")
