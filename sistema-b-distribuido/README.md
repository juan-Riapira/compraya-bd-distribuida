# Sistema B — Arquitectura propuesta para CompraYa (distribuida)

Misma API y mismo contrato JSON que el Sistema A, sobre una capa de datos
distribuida: **MongoDB fragmentado (sharding) con réplicas**, **Redis** en
memoria y **3 réplicas de la API** detrás de **Nginx**.

```
                         ┌─► api-1 ─┐
cliente ─► nginx (LB) ───┼─► api-2 ─┼──► mongos-1 / mongos-2 (routers)
                         └─► api-3 ─┤        ├─► shard1rs · zona NORTE (CO, MX, PE) · 3 réplicas
                                    │        ├─► shard2rs · zona SUR (CL, AR)       · 3 réplicas
                                    │        └─► cfgrs (metadatos del clúster)
                                    └──► redis-primary ──► redis-replica
```

## Qué resuelve cada pieza

| Problema de CompraYa | Solución en B | Código |
|---|---|---|
| Bloqueos en checkout | Reserva de stock con **script Lua atómico en Redis**; el cobro ocurre **sin bloqueos** | `repositories/stock_repository.py`, `services/checkout_service.py` |
| Fallas de pago / dobles cobros | **Saga** con compensaciones (devolver reserva, revertir stock, reembolsar) + **Idempotency-Key** | `services/checkout_service.py`, `repositories/idempotency_repository.py` |
| Catálogo lento en picos | **Caché cache-aside** en Redis; el stock se superpone en vivo | `cache/product_cache.py`, `services/catalog_service.py` |
| Pérdida de carritos | Carrito en **Redis (HASH + TTL)** con réplica y AOF | `repositories/cart_repository.py` |
| No escala horizontalmente | **Sharding**: más shards = más capacidad; API sin estado | `scripts/init_cluster.py`, `docker-compose.yml` |
| Latencia por región | **Zonas**: pedidos de cada país viven en el shard de su región | `scripts/init_cluster.py` (`ZONE_RANGES`) |
| Punto único de falla | **Replica sets de 3 nodos** con elección automática; 2 routers mongos; 3 APIs | `docker-compose.yml` |

## Modelo de datos (documental)

| Colección | Shard key | Por qué |
|---|---|---|
| `products` | `{_id: "hashed"}` | reparto uniforme; lecturas por id van a un solo shard |
| `users` | `{_id: "hashed"}` | ídem |
| `orders` | `{country: 1, _id: 1}` + zonas | cada pedido queda en el shard de su región |

Un pedido es **un documento** con ítems y pago embebidos (en A son 3 tablas):

```json
{ "_id": "uuid", "user_id": "U00001", "country": "PE", "status": "PAID",
  "items": [{"product_id": "P00001", "name": "Portátil Nova 859", "quantity": 2, "unit_price_cents": 69845}],
  "total_cents": 139690,
  "payment": {"status": "APPROVED", "provider_ref": "pay_…", "amount_cents": 139690},
  "created_at": "…" }
```

Llaves en Redis (`app/db/keys.py`): `product:{id}` (JSON, TTL 5 min) ·
`products:list:…` (TTL 30 s) · `stock:{id}` · `cart:{user}` (HASH, TTL 7 días) · `idem:{key}`.

## Flujo de checkout (saga)

1. Idempotencia (Redis) → 2. Carrito y precios (Redis) → 3. **Reserva atómica** de todo el carrito (Lua, Redis)
→ 4. Cobro en pasarela (sin bloqueos) → 5. Descuento de stock **en paralelo** en cada shard (`$inc` con guarda `stock >= qty`)
→ 6. Insertar pedido (1 documento, 1 shard) → 7. Vaciar carrito.
Si algo falla después del paso 3, se ejecutan las **compensaciones**.

No se usa una transacción multi-documento porque los productos están en shards
distintos (sería un *two-phase commit* entre shards). La reserva atómica en
Redis ya impide vender de más y cada actualización en MongoDB es atómica.

## Estructura

```
app/
├── main.py                       # fábrica de la app + conexión/cierre de Mongo y Redis
├── core/  config.py · exceptions.py · logging.py
├── db/
│   ├── mongo.py                  # cliente hacia mongos (write concern majority)
│   ├── redis.py                  # cliente Redis
│   ├── keys.py                   # nombres de llaves de Redis
│   └── indexes.py                # índices secundarios
├── repositories/                 # SOLO acceso a datos
│   ├── product_repository.py · user_repository.py · order_repository.py   (MongoDB)
│   ├── admin_repository.py                                                  (MongoDB)
│   └── cart_repository.py · stock_repository.py · idempotency_repository.py (Redis)
├── cache/product_cache.py        # caché del catálogo
├── services/                     # SOLO reglas de negocio
│   ├── catalog_service.py · cart_service.py · checkout_service.py · order_service.py
│   ├── user_service.py · admin_service.py
│   └── mappers.py                # documentos → DTO
├── seed/  dataset.py · loader.py   # datos deterministas (idénticos a A) y su carga
├── web/                          # tienda web: index.html, css/, js/ (api, estado, vistas)
├── integrations/payment_gateway.py
├── schemas/                      # contrato JSON (idéntico a A)
└── api/  deps.py · router.py · routes/ (health · products · carts · orders · users · admin)
scripts/
├── init_cluster.py               # replica sets, shards, zonas y shard keys (idempotente)
├── seed.py                       # carga el mismo dataset que A + precalienta Redis
├── reconcile_stock.py            # sincroniza stock Redis ← MongoDB
└── etl_from_postgres.py          # ETL PostgreSQL (Sistema A) → MongoDB + Redis
etl/                              # extract · transform · load · validate · pipeline
tests/test_etl_transform.py       # pruebas de las transformaciones
infra/nginx/nginx.conf            # balanceador least_conn con reintento en otra réplica
```

## Cómo correrlo

Requiere Docker Desktop con ~4 GB de RAM libres (son 17 contenedores; 2 solo inicializan y terminan).

```bash
cp .env.example .env
docker compose up -d --build        # el clúster se inicializa solo (cluster-init-*)
docker compose exec api-1 python -m scripts.seed
```

- API (vía Nginx): <http://localhost:8002> · Docs: <http://localhost:8002/docs>
- `curl -i localhost:8002/health` → el encabezado `X-Served-By` muestra qué réplica respondió.
- MongoDB (mongos): `mongodb://localhost:27017`

Ver el reparto de datos entre shards:

```bash
docker compose exec mongos-1 mongosh compraya --eval 'db.products.getShardDistribution(); db.orders.getShardDistribution()'
```

Simular la caída del primario del shard NORTE (la tienda sigue vendiendo):

```bash
docker compose stop shard1-a     # se elige un nuevo primario en ~10 s
docker compose start shard1-a
```

## ETL: migrar los datos del Sistema A (PostgreSQL) al Sistema B

`etl/` es un paquete aparte de la API, con un módulo por etapa:

| Módulo | Tarea |
|---|---|
| `etl/extract.py` | Lee PostgreSQL en **una instantánea `REPEATABLE READ READ ONLY`** con cursores por lotes (no bloquea la tienda) |
| `etl/transform.py` | Funciones puras: `NUMERIC` → centavos, categoría embebida en el producto, `orders + order_items + payments` → 1 documento, `country` del usuario como shard key, marca → `attributes` |
| `etl/load.py` | MongoDB con `ReplaceOne(upsert=True)` (idempotente: se puede repetir) · Redis: `stock:{id}` y `cart:{usuario}` con TTL |
| `etl/validate.py` | Compara conteos y sumas de control (productos, usuarios, pedidos, unidades en stock, ingresos en centavos, carritos) |
| `etl/pipeline.py` | Orquesta E → T → L → V y arma el reporte |

```bash
# con el Sistema A corriendo y con datos
ETL_SOURCE_DSN=postgresql://compraya:compraya@localhost:5432/compraya \
ETL_TRUNCATE_TARGET=true python -m scripts.etl_from_postgres
```

Salida de una corrida real (237 pedidos hechos en el Sistema A):

```
Control            PostgreSQL   MongoDB/Redis  Estado
products                2,000           2,000  OK
users                   5,000           5,000  OK
orders                    237             237  OK
stock_units           551,909         551,909  OK
revenue_cents      91,696,642      91,696,642  OK
carts                      61              61  OK
```

Los pedidos migrados quedan en el shard de su región (CO/MX/PE → `shard1rs`, CL/AR → `shard2rs`).
Pruebas de las transformaciones: `python -m pytest tests`.

## Despliegue parcial en la nube (opcional)

1. Crear un clúster gratuito en **MongoDB Atlas** (M0: replica set de 3 nodos; no admite sharding)
   y una base gratuita en **Redis Cloud**.
2. En `.env`: `MONGO_URI=mongodb+srv://…` y `REDIS_URL=redis://default:…@…`.
3. Correr `python -m scripts.seed` y levantar solo la API (`uvicorn app.main:app`), por ejemplo en Render.
   La nube demuestra la alta disponibilidad (réplicas gestionadas); el sharding se demuestra con Docker.

Los endpoints son los mismos del Sistema A (ver su README). Extra: `POST /api/v1/orders/checkout`
acepta el encabezado `Idempotency-Key`.

## Tienda web

Abre <http://localhost:8002>: catálogo con filtros y ofertas del día, detalle con stock en
vivo, carrito, pago y "Mis pedidos". Cambia de cliente escribiendo otro id (`U00001`…`U05000`).
La barra inferior muestra cuánto tardó el servidor en cada acción, así se nota la diferencia
entre A y B usando la misma tienda.

El código del navegador está en `app/web/` y es el mismo en A y B: `js/api.js` (única capa que
llama a la API), `js/state.js` (cliente y carrito), `js/views/` (catálogo, producto, carrito,
pedidos) y `js/ui/` (avisos, medidor de stock, barra de latencia).

## Panel "Redis en vivo"

Abre <http://localhost:8002/redis.html> (o el enlace **Redis en vivo** de la tienda). Muestra cada llave
de Redis con su tipo, su valor y una barra con el tiempo de vida restante (TTL), y se actualiza cada segundo:

- **Productos** (`product:*`, 5 min): pulsa *Vaciar caché del catálogo*, consulta `P00001` y mira cómo
  aparece la llave, baja el contador y desaparece sola (queda registrada en *Expiradas o borradas*).
- **Stock** (`stock:*`, no vence), **Carritos** (`cart:*`, 7 días) e **Idempotencia** (`idem:*`, 24 h).

Para verlo expirar en la exposición, levanta B con `PRODUCT_CACHE_TTL_S=30` en `.env`.
Código: `repositories/redis_inspector_repository.py` (SCAN + TTL), `services/redis_inspector_service.py`,
`api/routes/redis_panel.py` (`GET /admin/redis`, `DELETE /admin/redis/cache`) y `web/redis.html`.
Se desactiva junto con `ADMIN_ENABLED=false`.

## Administración (la usa el simulador)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/admin/reset` | Borra todo y recarga el dataset inicial |
| GET | `/admin/stats` | Pedidos, ingresos, unidades vendidas y stock de las ofertas |
| GET | `/admin/consistency` | Verifica `stock + vendido == inicial` y que no haya stock negativo |

Se desactivan con `ADMIN_ENABLED=false` en `.env` (no deben exponerse en producción).
