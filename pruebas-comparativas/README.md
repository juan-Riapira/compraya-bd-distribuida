# Pruebas comparativas A vs B

Cuatro pruebas, **mismo dataset y mismo escenario** para ambos sistemas.

| Script | Qué mide |
|---|---|
| `locustfile.py` + `run_benchmark.py` | Carga general tipo Black Friday (catálogo, producto, carrito, checkout; 80 % del interés en 20 productos) con 50, 150 y 300 usuarios |
| `flash_sale_test.py` | Venta relámpago: 50/100/200 compradores pagan **el mismo producto** al mismo tiempo (aísla el efecto de los bloqueos) |
| `failover_test.py` | Se apaga un nodo de base de datos con tráfico activo; registra compras exitosas por segundo |
| `consistency_check.py` | Tras cada prueba: `stock_actual + vendido == stock_inicial` y ningún stock negativo |
| `plot_results.py` | Genera `graficas/*.png` y `resultados/resumen.md` |

## Ejecución (con ambos sistemas levantados en Docker)

```bash
pip install -r requirements.txt
SA="docker compose -f ../sistema-a-actual/docker-compose.yml"
SB="docker compose -f ../sistema-b-distribuido/docker-compose.yml"

# 1. Carga general (para medir uno, detén la API del otro)
python run_benchmark.py --system A --host http://localhost:8001 --seed-cmd "$SA exec -T api python -m scripts.seed"
python consistency_check.py --system A --tag _300
python run_benchmark.py --system B --host http://localhost:8002 --seed-cmd "$SB exec -T api-1 python -m scripts.seed"
python consistency_check.py --system B --tag _300

# 2. Venta relámpago
python flash_sale_test.py --system A --host http://localhost:8001 --seed-cmd "$SA exec -T api python -m scripts.seed"
python flash_sale_test.py --system B --host http://localhost:8002 --seed-cmd "$SB exec -T api-1 python -m scripts.seed"

# 3. Caída de un nodo
python failover_test.py --system A --host http://localhost:8001 --kill-cmd "$SA stop postgres" --restore-cmd "$SA start postgres"
python failover_test.py --system B --host http://localhost:8002 --kill-cmd "$SB stop shard1-a" --restore-cmd "$SB start shard1-a"

# 4. Gráficas y resumen
python plot_results.py
```

## Resultados incluidos

`resultados/` y `graficas/` ya traen una corrida completa hecha sobre **una sola máquina
de 2 núcleos y 7 GB**, con los dos sistemas corriendo como procesos nativos
(PostgreSQL 16, MongoDB 8 con 2 shards × 3 réplicas + config server + mongos, Redis),
la API de cada uno con 3 workers. Ver [`resultados/resumen.md`](resultados/resumen.md).

Cómo leerlos con honestidad:

- **Con poca carga (50 usuarios) los dos rinden igual.** La arquitectura distribuida no
  hace más rápido lo que ya era rápido; su ventaja aparece con contención y con fallas.
- **La venta relámpago es la prueba más justa**: no depende del hardware. A queda clavado
  en ~10 compras/s (= 1 compra cada 80 ms, el tiempo del cobro con la fila bloqueada) y con
  200 compradores empieza a dar errores 500. B no bloquea; su límite es la CPU.
- **En un solo equipo B corre 9 procesos de MongoDB en 2 núcleos**, así que está en
  desventaja de hardware. En producción cada shard va en su propio servidor y la capacidad
  crece agregando shards; esa escalabilidad horizontal no se puede medir en una sola máquina.
- Tu corrida en Docker dará números distintos (otro hardware); la **forma** de las curvas
  es lo que se debe repetir.
