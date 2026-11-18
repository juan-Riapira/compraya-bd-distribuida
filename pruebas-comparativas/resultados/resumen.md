# Resumen de resultados

## Carga general (Black Friday, 80 % del tráfico en 20 productos)

| Usuarios | Sistema | req/s | p50 (ms) | p95 (ms) | p95 checkout (ms) | Fallas |
|---|---|---|---|---|---|---|
| 50 | A | 132 | 7 | 65 | 180 | 0 |
| 50 | B | 131 | 5 | 82 | 160 | 0 |
| 150 | A | 294 | 75 | 400 | 1700 | 0 |
| 150 | B | 358 | 25 | 170 | 350 | 0 |
| 300 | A | 366 | 280 | 1200 | 3100 | 0 |
| 300 | B | 496 | 180 | 520 | 980 | 0 |

## Venta relámpago (todos compran el producto P00001 a la vez)

| Compradores | Sistema | Compras OK | Errores 5xx | Tiempo total (s) | Compras/s | p95 (ms) |
|---|---|---|---|---|---|---|
| 50 | A | 48 | 0 | 4.8 | 10.0 | 4612 |
| 50 | B | 49 | 0 | 0.69 | 70.7 | 665 |
| 100 | A | 99 | 0 | 9.4 | 10.5 | 8826 |
| 100 | B | 99 | 0 | 2.4 | 41.3 | 2225 |
| 200 | A | 176 | 17 | 17.81 | 9.9 | 16427 |
| 200 | B | 196 | 0 | 5.82 | 33.7 | 5536 |

## Caída de un nodo de base de datos

| Sistema | Nodo apagado | Segundos sin vender | Compras OK | Compras fallidas |
|---|---|---|---|---|
| A | PostgreSQL (único servidor) | 29 | 1572 | 2325 |
| B | primario del shard NORTE | 8 | 2429 | 30 |

## Consistencia (¿se vendió más de lo que había?)

| Prueba | Pedidos | Unidades vendidas | Stock negativo | Violaciones | Redis vs Mongo | Consistente |
|---|---|---|---|---|---|---|
| consistencia_A_300 | 687 | 2660 | 0 | 0 | — | sí |
| consistencia_A_flash | 176 | 176 | 0 | 0 | — | sí |
| consistencia_B_300 | 978 | 3895 | 0 | 0 | 0 | sí |
| consistencia_B_flash | 196 | 196 | 0 | 0 | 0 | sí |
