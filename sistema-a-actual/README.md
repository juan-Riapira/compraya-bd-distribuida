# Sistema A — Arquitectura actual de CompraYa (PostgreSQL monolítico)

Reproduce el sistema que describe el enunciado: una API y **un solo servidor
PostgreSQL** que atiende catálogo, carritos, pedidos y pagos. Está construido
con buenas prácticas de código, pero conserva las decisiones de diseño que
causan los problemas de CompraYa en Black Friday.

```
cliente ──► API FastAPI (3 workers) ──► PostgreSQL (único servidor)
```

## Problemas que reproduce (a propósito)

| Problema del enunciado | Dónde ocurre en el código |
|---|---|
| Bloqueos en la base de datos | `repositories/inventory_repository.py` → `SELECT … FOR UPDATE` sobre el inventario |
| Fallas en el proceso de pago | `services/checkout_service.py` → la pasarela se llama **con los bloqueos tomados**; con muchas compras el pool de conexiones se agota (HTTP 500) |
| Pérdida de carritos / lentitud | `repositories/cart_repository.py` → el carrito vive en la misma base que los pagos |
| No escala horizontalmente | `db/session.py` → un único motor hacia un único servidor |
| Punto único de falla | si PostgreSQL cae, la tienda entera cae |

## Estructura

```
app/
├── main.py                  # crea la app FastAPI (fábrica + ciclo de vida)
├── core/
│   ├── config.py            # variables de entorno (única fuente de configuración)
│   ├── exceptions.py        # errores de dominio → respuestas HTTP
│   └── logging.py           # formato de logs
├── db/
│   ├── base.py              # Base declarativa de SQLAlchemy
│   └── session.py           # motor, pool y sesión por petición
├── models/                  # tablas (una por agregado)
│   ├── user.py · catalog.py · inventory.py · cart.py · order.py
├── schemas/                 # contrato JSON público (idéntico en A y B)
├── repositories/            # SOLO acceso a datos (SQL); sin reglas de negocio
│   ├── product_repository.py · inventory_repository.py
│   ├── cart_repository.py · order_repository.py · user_repository.py
│   └── admin_repository.py  # consultas agregadas (stats y consistencia)
├── services/                # SOLO reglas de negocio; sin HTTP ni SQL
│   ├── catalog_service.py · cart_service.py
│   ├── checkout_service.py · order_service.py
│   ├── user_service.py · admin_service.py
│   └── mappers.py           # entidades ORM → DTO
├── seed/
│   ├── dataset.py           # datos deterministas (idénticos en A y B)
│   └── loader.py            # carga del dataset (script y /admin/reset)
├── web/                     # tienda web: index.html, css/, js/ (api, estado, vistas)
├── integrations/
│   └── payment_gateway.py   # pasarela de pago simulada (igual en A y B)
└── api/
    ├── deps.py              # inyección de dependencias (cableado)
    ├── router.py            # agrupa rutas bajo /api/v1
    └── routes/              # SOLO HTTP: health · products · carts · orders · users · admin
scripts/
└── seed.py                  # crea esquema y carga datos
sql/schema.sql               # DDL generado (documentación del modelo relacional)
```

Regla de dependencias: `routes → services → repositories → db`. Ninguna capa
conoce a la de arriba.

## Modelo relacional

`categories` 1─N `products` 1─1 `inventory` · `users` 1─1 `carts` 1─N `cart_items` ·
`users` 1─N `orders` 1─N `order_items` · `orders` 1─1 `payments`. DDL completo en
[`sql/schema.sql`](sql/schema.sql).

## Cómo correrlo

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api python -m scripts.seed      # 2000 productos, 5000 usuarios
```

- API: <http://localhost:8001> · Documentación interactiva: <http://localhost:8001/docs>
- PostgreSQL: `localhost:5432` (usuario/clave/base: `compraya`)

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado de la API y de PostgreSQL |
| GET | `/api/v1/products?limit&offset&category` | Catálogo paginado |
| GET | `/api/v1/products/{id}` | Detalle de producto |
| GET | `/api/v1/carts/{user_id}` | Ver carrito |
| POST | `/api/v1/carts/{user_id}/items` | Agregar `{product_id, quantity}` |
| DELETE | `/api/v1/carts/{user_id}/items/{product_id}` | Quitar del carrito |
| POST | `/api/v1/orders/checkout` | Pagar `{user_id}` |
| GET | `/api/v1/orders/{order_id}` | Ver pedido |
| GET | `/api/v1/users/{user_id}/orders` | Pedidos del usuario |

Prueba rápida:

```bash
curl -X POST localhost:8001/api/v1/carts/U00001/items -H 'content-type: application/json' -d '{"product_id":"P00001","quantity":2}'
curl -X POST localhost:8001/api/v1/orders/checkout   -H 'content-type: application/json' -d '{"user_id":"U00001"}'
```

Códigos de negocio: `400` carrito vacío · `402` pago rechazado · `404` no existe · `409` sin existencias.

## Tienda web

Abre <http://localhost:8001>: catálogo con filtros y ofertas del día, detalle con stock en
vivo, carrito, pago y "Mis pedidos". Cambia de cliente escribiendo otro id (`U00001`…`U05000`).
La barra inferior muestra cuánto tardó el servidor en cada acción, así se nota la diferencia
entre A y B usando la misma tienda.

El código del navegador está en `app/web/` y es el mismo en A y B: `js/api.js` (única capa que
llama a la API), `js/state.js` (cliente y carrito), `js/views/` (catálogo, producto, carrito,
pedidos) y `js/ui/` (avisos, medidor de stock, barra de latencia).

## Administración (la usa el simulador)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/admin/reset` | Borra todo y recarga el dataset inicial |
| GET | `/admin/stats` | Pedidos, ingresos, unidades vendidas y stock de las ofertas |
| GET | `/admin/consistency` | Verifica `stock + vendido == inicial` y que no haya stock negativo |

Se desactivan con `ADMIN_ENABLED=false` en `.env` (no deben exponerse en producción).
