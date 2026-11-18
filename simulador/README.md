# Simulador de pruebas A vs B

Panel web para lanzar pruebas contra el **Sistema A** (PostgreSQL único) y el
**Sistema B** (distribuido) y verlas **en vivo**: peticiones por segundo,
latencia, compras completadas, fallas y la caída de nodos, todo superpuesto
en las mismas gráficas (naranja = A, azul = B).

<http://localhost:8010>

## Escenarios

| Escenario | Qué hace | Qué demuestra |
|---|---|---|
| **Black Friday** | N compradores navegan, agregan al carrito y pagan; el 80 % mira las ofertas del día | Rendimiento con carga mixta y alta |
| **Venta relámpago** | N compradores pagan el **mismo producto** al mismo tiempo | Los bloqueos de fila de A frente a la reserva sin bloqueos de B |
| **Caída de un nodo** | Con tráfico activo apaga un nodo de BD (A: PostgreSQL; B: primario del shard NORTE) y luego lo enciende | Disponibilidad y recuperación automática |

Todos los parámetros se ajustan en el panel: compradores, duración, rampa,
pausas entre clics, producto, segundo de caída y de reparación. Antes de cada
sistema se **reinician los datos** (opcional) y al final se **verifica la
consistencia** del inventario (que nunca se haya vendido de más).

Cada corrida queda en el **historial** (`data/runs/*.json`); al hacer clic se
vuelven a ver sus gráficas y su tabla comparativa.

## Cómo levantarlo

Primero levanta A y B (ver sus README). Luego:

```bash
cd simulador
cp .env.example .env
docker compose up -d --build
```

Abre <http://localhost:8010>.

Sin Docker (Python 3.12+):

```bash
pip install -r requirements.txt
cp .env.example .env     # cambia TARGET_*_URL a http://localhost:8001 y :8002
uvicorn app.main:app --port 8010
```

Para el escenario de caída fuera de Docker usa `FAILOVER_*_MODE=shell` con los
comandos que apagan y encienden el nodo (hay ejemplos en `.env.example`).

## Estructura

```
app/
├── main.py                 # crea la app, el administrador de corridas y sirve el panel
├── core/config.py          # URLs de A y B, inyección de fallas, límites de seguridad
├── engine/                 # motor de carga (independiente de la web)
│   ├── shopper.py          # comportamiento de un comprador virtual
│   ├── load_runner.py      # lanza N compradores y publica métricas cada segundo
│   └── metrics.py          # métricas por segundo, percentiles y resumen
├── scenarios/              # un archivo por escenario, todos con la misma interfaz
│   ├── base.py · black_friday.py · flash_sale.py · failover.py
├── infra/
│   ├── target_client.py    # /health y /admin/* de cada sistema
│   └── chaos.py            # apagar/encender nodos (Docker, comando o deshabilitado)
├── runs/                   # ciclo de vida de una corrida
│   ├── models.py · context.py · manager.py · repository.py · broadcaster.py (SSE)
├── api/routes/             # catalog.py (escenarios y sistemas) · runs.py (corridas y streaming)
└── web/                    # panel: HTML + CSS + módulos JS (Chart.js incluido, funciona sin internet)
```

## API

| Método | Ruta | Para qué |
|---|---|---|
| GET | `/api/scenarios` | Escenarios y sus parámetros |
| GET | `/api/targets` | Estado y estadísticas de A y B |
| POST | `/api/targets/{A\|B}/reset` | Reiniciar datos de un sistema |
| POST | `/api/runs` | Iniciar `{scenario, systems, params}` |
| GET | `/api/runs` · `/api/runs/{id}` | Historial · detalle |
| GET | `/api/runs/{id}/stream` | Eventos en vivo (Server-Sent Events) |
| POST | `/api/runs/{id}/cancel` | Detener (si había un nodo apagado, lo vuelve a encender) |

## Notas para interpretar

- Las pruebas a A y B se hacen **una después de la otra** para que no compitan por la CPU del mismo equipo.
- La latencia se mide solo sobre peticiones **respondidas**; las fallas se cuentan aparte.
- 400/402/409 (carrito vacío, pago rechazado, agotado) son resultados de negocio, no fallas técnicas.
- En el escenario de caída, B puede seguir respondiendo el catálogo desde Redis aunque un shard esté
  caído (por eso «segundos sin ninguna respuesta» suele ser 0): eso es disponibilidad parcial real.
