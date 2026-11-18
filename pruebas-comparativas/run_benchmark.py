"""Ejecuta la prueba de carga contra un sistema en varios niveles de usuarios.

Antes de cada nivel vuelve a sembrar la base, para que A y B arranquen
siempre desde el mismo estado. Los CSV de Locust quedan en resultados/.

Ejemplos (con Docker, desde esta carpeta):
    python run_benchmark.py --system A --host http://localhost:8001 \
        --seed-cmd "docker compose -f ../sistema-a-actual/docker-compose.yml exec -T api python -m scripts.seed"
    python run_benchmark.py --system B --host http://localhost:8002 \
        --seed-cmd "docker compose -f ../sistema-b-distribuido/docker-compose.yml exec -T api-1 python -m scripts.seed"
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
RESULTS = HERE / "resultados"


def wait_healthy(host: str, timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if requests.get(f"{host}/health", timeout=2).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    sys.exit(f"{host} no responde /health")


def run_level(system: str, host: str, users: int, duration: str, seed_cmd: str | None) -> None:
    if seed_cmd:
        time.sleep(10)  # deja terminar las peticiones en vuelo del nivel anterior
        print(f"[{system}] sembrando datos...")
        subprocess.run(seed_cmd, shell=True, check=True)
    wait_healthy(host)
    prefix = RESULTS / f"{system}_{users}"
    print(f"[{system}] {users} usuarios durante {duration}...")
    subprocess.run(
        [
            sys.executable, "-m", "locust", "-f", str(HERE / "locustfile.py"), "--headless",
            "-u", str(users), "-r", str(max(users // 5, 1)), "-t", duration,
            "--host", host, "--csv", str(prefix), "--only-summary", "--loglevel", "WARNING",
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["A", "B"], required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--users", default="50,150,300", help="niveles separados por coma")
    parser.add_argument("--duration", default="60s")
    parser.add_argument("--seed-cmd", default=None, help="comando que re-siembra la base antes de cada nivel")
    args = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    for users in (int(u) for u in args.users.split(",")):
        run_level(args.system, args.host.rstrip("/"), users, args.duration, args.seed_cmd)
    print(f"Listo. CSV en {RESULTS}")


if __name__ == "__main__":
    main()
