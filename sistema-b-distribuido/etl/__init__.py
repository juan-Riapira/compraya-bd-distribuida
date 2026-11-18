"""ETL de migración: PostgreSQL (Sistema A) -> MongoDB fragmentado + Redis (Sistema B).

Cada módulo tiene una sola tarea:

- ``settings``  : de dónde se lee y cómo (cadena de conexión, tamaño de lote).
- ``extract``   : lee PostgreSQL en una instantánea de solo lectura, por lotes.
- ``transform`` : funciones puras fila -> documento (sin E/S, fáciles de probar).
- ``load``      : escribe en MongoDB (upsert idempotente) y en Redis.
- ``validate``  : compara conteos y sumas de control entre origen y destino.
- ``pipeline``  : orquesta E -> T -> L -> V y arma el reporte.

Se ejecuta con ``python -m scripts.etl_from_postgres``.
"""
