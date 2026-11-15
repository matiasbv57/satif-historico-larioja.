
"""Importación reproducible de ZIP NASA FIRMS para SATIF Histórico.

No realiza armonización científica ni interpreta detecciones como incendios.
Uso: python src/importar_firms_historico.py
"""

from pathlib import Path
from zipfile import ZipFile
import json

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "data" / "raw"
DESTINO = RAIZ / "data" / "processed"

PRODUCTOS = {
    "M-C61": "MODIS",
    "SV-C2": "VIIRS_S_NPP",
    "J1V-C2": "VIIRS_NOAA20",
    "J2V-C2": "VIIRS_NOAA21",
}

OBLIGATORIAS = {
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
}


def importar():
    DESTINO.mkdir(parents=True, exist_ok=True)

    archivos = sorted(ORIGEN.glob("DL_FIRE_*.zip"))

    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron ZIP de NASA FIRMS en {ORIGEN}"
        )

    tablas = []
    detalles = []

    for ruta in archivos:
        coincidencias = [
            (codigo, nombre)
            for codigo, nombre in PRODUCTOS.items()
            if f"_{codigo}_" in ruta.name
        ]

        if len(coincidencias) != 1:
            raise ValueError(
                f"No se puede identificar el producto: {ruta.name}"
            )

        codigo, sensor = coincidencias[0]

        with ZipFile(ruta) as paquete:
            csvs = [
                nombre
                for nombre in paquete.namelist()
                if nombre.lower().endswith(".csv")
            ]

            if not csvs:
                raise ValueError(f"ZIP sin CSV: {ruta.name}")

            for nombre_csv in csvs:
                nombre_archivo = Path(nombre_csv).name

                if nombre_archivo.startswith("fire_nrt_"):
                    fuente = "nrt"
                elif nombre_archivo.startswith("fire_archive_"):
                    fuente = "archive"
                else:
                    raise ValueError(
                        f"CSV no reconocido: {nombre_csv}"
                    )

                with paquete.open(nombre_csv) as archivo:
                    df = pd.read_csv(
                        archivo,
                        dtype={
                            "acq_time": "string",
                            "confidence": "string",
                        },
                    )

                faltantes = OBLIGATORIAS - set(df.columns)

                if faltantes:
                    raise ValueError(
                        f"{nombre_csv}: faltan {sorted(faltantes)}"
                    )

                iniciales = len(df)

                df["acq_time"] = df["acq_time"].str.zfill(4)

                df["fecha_hora_utc"] = pd.to_datetime(
                    df["acq_date"].astype(str)
                    + " "
                    + df["acq_time"],
                    format="%Y-%m-%d %H%M",
                    errors="coerce",
                    utc=True,
                )

                for columna in (
                    "latitude",
                    "longitude",
                    "frp",
                ):
                    if columna in df.columns:
                        df[columna] = pd.to_numeric(
                            df[columna],
                            errors="coerce",
                        )

                invalidos = (
                    df["fecha_hora_utc"].isna()
                    | ~df["latitude"].between(-90, 90)
                    | ~df["longitude"].between(-180, 180)
                )

                df["sensor_origen"] = sensor
                df["producto_firms"] = codigo
                df["fuente_firms"] = fuente
                df["archivo_origen"] = nombre_archivo

                detalles.append(
                    {
                        "zip": ruta.name,
                        "csv": nombre_csv,
                        "sensor": sensor,
                        "fuente": fuente,
                        "filas_originales": iniciales,
                        "filas_invalidas": int(
                            invalidos.sum()
                        ),
                        "filas_validas": int(
                            (~invalidos).sum()
                        ),
                    }
                )

                tablas.append(
                    df.loc[~invalidos].copy()
                )

    base = pd.concat(
        tablas,
        ignore_index=True,
        sort=False,
    )

    # Las detecciones de distintos satélites se
    # conservan como observaciones independientes.
    # No se eliminan posibles coincidencias entre
    # archive y NRT sin una revisión específica.

    base = base.sort_values(
        ["fecha_hora_utc", "sensor_origen"]
    ).reset_index(drop=True)

    salida = DESTINO / "firms_integrado.csv"

    base.to_csv(
        salida,
        index=False,
        date_format="%Y-%m-%dT%H:%M:%SZ",
    )

    informe = {
        "advertencia": (
            "Integración y control básico; "
            "NO es armonización MODIS-VIIRS."
        ),
        "total_filas_validas": len(base),
        "fecha_min_utc": (
            base["fecha_hora_utc"].min().isoformat()
        ),
        "fecha_max_utc": (
            base["fecha_hora_utc"].max().isoformat()
        ),
        "por_sensor": {
            str(sensor): int(cantidad)
            for sensor, cantidad
            in base["sensor_origen"].value_counts().items()
        },
        "archivos": detalles,
    }

    auditoria = DESTINO / "auditoria_firms.json"

    auditoria.write_text(
        json.dumps(
            informe,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"Integración terminada: {len(base):,} registros"
    )
    print(f"Base: {salida}")
    print(f"Auditoría: {auditoria}")

    for sensor, cantidad in informe["por_sensor"].items():
        print(f"  {sensor}: {cantidad:,}")


if __name__ == "__main__":
    importar()
