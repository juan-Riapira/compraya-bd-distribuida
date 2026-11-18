"""Prueba "venta relámpago": N compradores pagan EL MISMO producto al mismo tiempo.

Es el momento crítico de un Black Friday (la oferta estrella sale a las 00:00).
Aísla el efecto de la arquitectura de datos y no del hardware:

  * Sistema A: cada checkout bloquea la fila del producto (SELECT ... FOR UPDATE)
    mientras cobra (~80 ms). Las compras se atienden de a una, en fila.
  * Sistema B: la reserva es un script atómico en Redis (microsegundos) y el
    cobro ocurre sin bloqueos. Las compras avanzan en paralelo.

Antes de disparar, cada comprador agrega 1 unidad al carrito (no se mide).
Luego TODOS hacen checkout a la vez y se mide cuánto tarda cada uno.

Uso:
    python flash_sale_test.py --system A --host http://localhost:8001 --buyers 50,100,200 \
        --seed-cmd "docker compose -f ../sistema-a-actual/docker-compose.yml exec -T api python -m scripts.seed"
"""
import argparse
import asyncio
import json
import statistics
import subprocess
import time
from pathlib import Path

import httpx

HERE = Path(__file__).parent
PRODUCT = "P00001"  # producto estrella (300 unidades en el dataset)


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))]


async def run_round(host: str, buyers: int) -> dict:
    users = [f"U{i:05d}" for i in range(1, buyers + 1)]
    limits = httpx.Limits(max_connections=buyers + 10, max_keepalive_connections=buyers + 10)
    async with httpx.AsyncClient(base_url=host, timeout=60, limits=limits) as client:
        await asyncio.gather(
            *(client.post(f"/api/v1/carts/{u}/items", json={"product_id": PRODUCT, "quantity": 1}) for u in users)
        )

        async def buy(user: str) -> tuple[int, float]:
            t = time.perf_counter()
            try:
                r = await client.post("/api/v1/orders/checkout", json={"user_id": user})
                return r.status_code, (time.perf_counter() - t) * 1000
            except httpx.HTTPError:
                return 599, (time.perf_counter() - t) * 1000

        start = time.perf_counter()
        results = await asyncio.gather(*(buy(u) for u in users))
        wall = time.perf_counter() - start

    ok = [ms for code, ms in results if code == 201]
    return {
        "buyers": buyers,
        "orders_ok": len(ok),
        "payment_declined": sum(1 for c, _ in results if c == 402),
        "sold_out": sum(1 for c, _ in results if c == 409),
        "errors_5xx": sum(1 for c, _ in results if c >= 500),
        "wall_time_s": round(wall, 2),
        "checkouts_per_s": round(len(ok) / wall, 1) if wall else 0,
        "latency_p50_ms": round(pct([ms for _, ms in results], 50)),
        "latency_p95_ms": round(pct([ms for _, ms in results], 95)),
        "latency_max_ms": round(max(ms for _, ms in results)),
        "latency_mean_ok_ms": round(statistics.mean(ok)) if ok else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["A", "B"], required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--buyers", default="50,100,200")
    parser.add_argument("--seed-cmd", default=None)
    args = parser.parse_args()

    rounds = []
    for n in (int(b) for b in args.buyers.split(",")):
        if args.seed_cmd:
            subprocess.run(args.seed_cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
        result = asyncio.run(run_round(args.host.rstrip("/"), n))
        print(json.dumps(result))
        rounds.append(result)

    out = HERE / "resultados" / f"flash_sale_{args.system}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"system": args.system, "product": PRODUCT, "rounds": rounds}, indent=2))
    print(f"Guardado en {out}")


if __name__ == "__main__":
    main()
