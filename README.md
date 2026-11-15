
SATIF Histórico
Sistema de Análisis Territorial de Incendios Forestales
NASA Space Apps Challenge 2026

 1. Descripción

SATIF Histórico es un prototipo de análisis geoespacial desarrollado para integrar, explorar y comparar detecciones térmicas históricas de los sensores MODIS y VIIRS mediante datos NASA FIRMS.

El proyecto está orientado al análisis territorial y al apoyo a la investigación de incendios forestales, con un caso de estudio en la provincia de La Rioja, Argentina.

Las detecciones térmicas no deben interpretarse automáticamente como incendios forestales confirmados.

 2. Objetivos

- Integrar registros históricos de diferentes sensores.
- Normalizar fechas, coordenadas y atributos.
- Agrupar observaciones térmicas próximas.
- Identificar correspondencias espaciotemporales MODIS–VIIRS.
- Visualizar los resultados en mapas interactivos.
- Evaluar limitaciones y sensibilidad de los métodos.

3. Fuentes de datos

NASA Fire Information for Resource Management System (FIRMS).

Productos utilizados:

- MODIS Collection 6.1
- VIIRS S-NPP Collection 2
- VIIRS NOAA-20 Collection 2
- VIIRS NOAA-21 Collection 2

Período procesado: enero de 2025 a octubre de 2026.

4. Resultados

| Indicador | Resultado |
|---|---:|
| Registros integrados | 19.761 |
| Detecciones en el área de estudio | 7.494 |
| Grupos de observación V2 | 3.179 |
| Correspondencias MODIS–VIIRS | 133 |
| Grupos MODIS relacionados | 49 |
| Grupos VIIRS relacionados | 86 |
| Asociaciones exclusivas uno a uno | 15 |

Parámetros exploratorios de correspondencia:

- Distancia mínima entre detecciones: hasta 2 km.
- Separación temporal entre intervalos: hasta 60 minutos.

Las 133 correspondencias no representan necesariamente 133 eventos independientes.

5. Metodología

1. Importación de archivos históricos NASA FIRMS.
2. Normalización de atributos y fechas UTC.
3. Recorte territorial del área de estudio.
4. Agrupamiento espacial y temporal por sensor.
5. Identificación de correspondencias entre grupos MODIS y VIIRS.
6. Auditorías de integridad, multiplicidad y sensibilidad.
7. Visualización interactiva mediante Streamlit y Plotly.

El agrupamiento V2 utiliza enlace completo para controlar el diámetro espacial de los grupos.

6. Instalación

Requisitos:

- Python 3.12
- Entorno virtual recomendado
- Dependencias indicadas en requirements.txt

Desde la carpeta principal del proyecto:

    powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt


7. Ejecución

powershell
python -m streamlit run app\main.py


Abrir en el navegador:

http://localhost:8501

8. Funcionalidades principales

**Explorador histórico**

- Filtros por fecha y sensor.
- Evolución mensual de detecciones.
- Distribución por sensor.
- Visualización geográfica.
- Consulta de registros.

**Correspondencias MODIS–VIIRS**

- Filtros espaciales y temporales.
- Estadísticas de correspondencias.
- Selección de grupos relacionados.
- Visualización sobre cartografía interactiva.
- Inspección de distancias entre detecciones.
- Exportación de resultados.

9. Limitaciones científicas

- Las detecciones FIRMS no equivalen necesariamente a incendios confirmados.
- Los sensores MODIS y VIIRS tienen diferentes características instrumentales.
- Las correspondencias son asociaciones espaciotemporales exploratorias.
- Existen relaciones múltiples entre grupos de observación.
- No se ha validado una calibración radiométrica de FRP entre sensores.
- Los umbrales de 2 km y 60 minutos no constituyen parámetros óptimos demostrados.
- Las imágenes satelitales de fondo proporcionan contexto geográfico y no necesariamente corresponden a la fecha de las detecciones.
- El recorte territorial debe validarse contra un límite administrativo oficial antes de utilizarlo para estadísticas jurisdiccionales definitivas.

10. Estado del desarrollo

Prototipo funcional con auditorías de integridad y análisis exploratorios realizados.

La validación científica adicional, la armonización radiométrica y la evaluación con eventos de referencia permanecen como líneas de trabajo futuras.

11. Alcance

SATIF Histórico es un proyecto de investigación y desarrollo.
