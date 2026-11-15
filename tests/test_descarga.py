
import sys
import tempfile
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.descarga import cargar_firms


def probar_lectura():
    datos = pd.DataFrame([
        {
            "latitude": -29.16,
            "longitude": -67.49,
            "acq_date": "2026-10-20",
            "acq_time": 1530,
            "satellite": "N",
            "instrument": "VIIRS",
        },
        {
            "latitude": -95.0,
            "longitude": -67.50,
            "acq_date": "2026-10-20",
            "acq_time": 1540,
            "satellite": "N",
            "instrument": "VIIRS",
        },
    ])

    with tempfile.TemporaryDirectory() as carpeta:
        archivo = Path(carpeta) / "prueba_firms.csv"
        datos.to_csv(archivo, index=False)

        resultado = cargar_firms(archivo)

        assert len(resultado) == 1
        assert resultado.iloc[0]["latitude"] == -29.16

    print("PRUEBA EXITOSA: lectura y validación FIRMS")


if __name__ == "__main__":
    probar_lectura()
