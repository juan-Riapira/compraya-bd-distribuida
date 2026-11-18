"""Prueba de caída: ¿la tienda sigue vendiendo si se cae un nodo de base de datos?

Genera tráfico de compra constante (ver producto -> agregar -> pagar) y, a los
`--kill-at` segundos, ejecuta `--kill-cmd` (por ejemplo, apagar PostgreSQL en A
o el nodo primario de un shard en B). Registra por segundo cuántas compras
salieron bien y cuántas fallaron, y guarda resultados/failover_<sistema>.csv.

Ejemplos con Docker:
    # A: se apaga el ÚNICO servidor de base de datos
    python failover_test.py --system A --host http://localhost:8001 \
        --kill-cmd "docker compose -f ../sistema-a-actual/docker-compose.yml stop postgres" \
        --restore-cmd "docker compose -f ../sistema-a-actual/docker-compose.yml start postgres"
    # B: se apaga el PRIMARIO del shard NORTE; sus réplicas eligen uno nuevo
    python failover_test.py --system B --host http://localhost:8002 \
        --kill-cmd "docker compose -f ../sistema-b-distribuido/docker-compose.yml stop shard1-a" \
        --restore-cmd "docker compose -f ../sistema-b-distribuido/docker-compose.yml start shard1-a"
"""
import argparse
import csv
import random
import subprocess
import threading
import time
from collections import defaultdict
from pathlib import Path

import requests

HERE = Path(__file__).parent
BUSINESS_OUTCOMES = {400, 402, 409}


def shopper_loop(host: str, stop: threading.Event, t0: float, stats: dict, lock: threading.Lock) -> None:
    session = requests.Session()
    while not stop.is_set():
        user = f"U{random.randint(1, 5000):05d}"
        product = f"P{random.randint(1, 2000):05d}"
        ok = True
        try:
            for method, path, body in (
                ("GET", f"/api/v1/products/{product}", None),
                ("POST", f"/api/v1/carts/{user}/items", {"product_id": product, "quantity": 1}),
                ("POST", "/api/v1/orders/checkout", {"user_id": user}),
            ):
                r = session.request(method, host + path, json=body, timeout=5)
                if r.status_code >= 500 or (r.status_code >= 400 and r.status_code not in BUSINESS_OUTCOMES):
                    ok = False
                    break
        except requests.RequestException:
            ok = False
        second = int(time.time() - t0)
        with lock:
            stats[second]["ok" if ok else "fail"] += 1
        if not ok:
            time.sleep(0.2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["A", "B"], required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--kill-cmd", required=True)
    parser.add_argument("--restore-cmd", default=None)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--kill-at", type=int, default=15)
    parser.add_argument("--restore-at", type=int, default=45)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    stats: dict[int, dict[str, int]] = defaultdict(lambda: {"ok": 0, "fail": 0})
    lock, stop = threading.Lock(), threading.Event()
    t0 = time.time()
    threads = [
        threading.Thread(target=shopper_loop, args=(args.host.rstrip("/"), stop, t0, stats, lock), daemon=True)
        for _ in range(args.workers)
    ]
    for t in threads:
        t.start()

    events = []
    killed = restored = False
    while (elapsed := time.time() - t0) < args.duration:
        if not killed and elapsed >= args.kill_at:
            print(f"t={elapsed:4.1f}s  >>> FALLA: {args.kill_cmd}")
            subprocess.run(args.kill_cmd, shell=True)
            events.append(("kill", int(elapsed)))
            killed = True
        if args.restore_cmd and not restored and elapsed >= args.restore_at:
            print(f"t={elapsed:4.1f}s  >>> RECUPERACIÓN: {args.restore_cmd}")
            subprocess.run(args.restore_cmd, shell=True)
            events.append(("restore", int(elapsed)))
            restored = True
        time.sleep(0.2)
    stop.set()
    for t in threads:
        t.join(timeout=6)

    out = HERE / "resultados" / f"failover_{args.system}.csv"
    out.parent.mkdir(exist_ok=True)
    seconds = range(args.duration)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["second", "ok", "fail", "event"])
        ev = {s: e for e, s in events}
        for s in seconds:
            w.writerow([s, stats[s]["ok"], stats[s]["fail"], ev.get(s, "")])

    after = [s for s in seconds if s >= args.kill_at and (not args.restore_cmd or s < args.restore_at)]
    down = [s for s in after if stats[s]["ok"] == 0]
    total_ok = sum(stats[s]["ok"] for s in seconds)
    total_fail = sum(stats[s]["fail"] for s in seconds)
    print(f"\nSistema {args.system}: compras OK={total_ok}  fallidas={total_fail}")
    print(f"Segundos SIN ninguna compra exitosa tras la falla: {len(down)} de {len(after)}")
    print(f"CSV: {out}")


if __name__ == "__main__":
    main()
