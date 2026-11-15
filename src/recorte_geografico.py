
from pathlib import Path

import pandas as pd
from shapely import from_wkt, contains_xy, is_valid


RAIZ = Path(__file__).resolve().parents[1]

ARCHIVO_POLIGONO = RAIZ / "data" / "geografia" / "la_rioja.wkt"
ARCHIVO_ENTRADA = RAIZ / "data" / "processed" / "firms_integrado.csv"
ARCHIVO_SALIDA = RAIZ / "data" / "processed" / "firms_la_rioja.csv"


def main():
    # Leer el polígono de La Rioja
    poligono = from_wkt(
        ARCHIVO_POLIGONO.read_text(encoding="utf-8").strip()
    )

    if not is_valid(poligono):
        raise ValueError("El polígono no es válido.")

    # Leer las detecciones NASA FIRMS
    datos = pd.read_csv(ARCHIVO_ENTRADA)

    # Filtrar coordenadas dentro del polígono
    # X = longitud, Y = latitud
    dentro = contains_xy(
        poligono,
        datos["longitude"].to_numpy(),
        datos["latitude"].to_numpy(),
    )

    datos_provincia = datos.loc[dentro].copy()

    # Exportar sin modificar el CSV original
    datos_provincia.to_csv(ARCHIVO_SALIDA, index=False)

    print("\nSATIF HISTÓRICO — RECORTE GEOGRÁFICO")
    print("-------------------------------------")
    print(f"Registros originales: {len(datos):,}")
    print(f"Dentro del polígono: {len(datos_provincia):,}")
    print(f"Fuera del polígono: {(~dentro).sum():,}")
    print(f"Porcentaje dentro: {dentro.mean() * 100:.2f}%")
    print(f"\nArchivo generado: {ARCHIVO_SALIDA}")

    print("\nRegistros por sensor:")
    print(datos_provincia["sensor_origen"].value_counts())


if __name__ == "__main__":
    main()
