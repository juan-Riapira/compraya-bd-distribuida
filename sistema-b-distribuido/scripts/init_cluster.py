"""Inicializa el clúster MongoDB distribuido (idempotente: se puede correr varias veces).

Pasos:
  1. Inicia el replica set de config servers y el de cada shard.
  2. Registra los shards en el router `mongos`.
  3. Define zonas geográficas: NORTE (CO, MX, PE) y SUR (CL, AR).
  4. Fragmenta (shard) las colecciones:
       users    -> {_id: "hashed"}           reparto uniforme
       products -> {_id: "hashed"}           reparto uniforme
       orders   -> {country: 1, _id: 1}      por país, anclado a su zona

Toda la topología llega por variables de entorno (ver valores por defecto,
que coinciden con infra/docker-compose.yml).

Uso:
    python -m scripts.init_cluster                     # todo
    python -m scripts.init_cluster --step replicasets  # solo pasos 1 (antes de levantar mongos)
    python -m scripts.init_cluster --step sharding     # pasos 2-4 (con mongos arriba)
"""
import argparse
import os
import time

from bson import MaxKey, MinKey
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

DB = os.getenv("MONGO_DB", "compraya")
CONFIG_RS = os.getenv("CONFIG_RS", "cfgrs/cfg1:27017")
SHARDS = os.getenv(
    "SHARDS",
    "shard1rs/shard1-a:27017,shard1-b:27017,shard1-c:27017;"
    "shard2rs/shard2-a:27017,shard2-b:27017,shard2-c:27017",
)
MONGOS_URI = os.getenv("MONGOS_URI", "mongodb://mongos-1:27017")
SHARD_ZONES = os.getenv("SHARD_ZONES", "shard1rs:NORTE,shard2rs:SUR")

# Rangos de shard key de `orders` por zona (orden alfabético de país: AR < CL < CO < MX < PE)
ZONE_RANGES = {
    "SUR": ({"country": "AR", "_id": MinKey()}, {"country": "CO", "_id": MinKey()}),
    "NORTE": ({"country": "CO", "_id": MinKey()}, {"country": MaxKey(), "_id": MaxKey()}),
}


def parse_rs(spec: str) -> tuple[str, list[str]]:
    name, hosts = spec.split("/", 1)
    return name, hosts.split(",")


def wait_for(host: str, timeout_s: int = 120) -> MongoClient:
    deadline = time.time() + timeout_s
    while True:
        client = MongoClient(f"mongodb://{host}/?directConnection=true", serverSelectionTimeoutMS=2000)
        try:
            client.admin.command("ping")
            return client
        except ServerSelectionTimeoutError:
            if time.time() > deadline:
                raise
            print(f"  esperando a {host}...")
            time.sleep(2)


def init_replica_set(spec: str, configsvr: bool = False) -> None:
    name, hosts = parse_rs(spec)
    for h in hosts:
        wait_for(h)
    client = wait_for(hosts[0])
    try:
        client.admin.command("replSetGetStatus")
        print(f"[ok] replica set {name} ya estaba iniciado")
    except OperationFailure:
        config = {
            "_id": name,
            "members": [{"_id": i, "host": h, "priority": 2 if i == 0 else 1} for i, h in enumerate(hosts)],
        }
        if configsvr:
            config["configsvr"] = True
        client.admin.command("replSetInitiate", config)
        print(f"[+] replica set {name} iniciado con {len(hosts)} miembro(s)")

    deadline = time.time() + 120
    while not client.admin.command("hello").get("isWritablePrimary"):
        if time.time() > deadline:
            raise TimeoutError(f"{name} no eligió primario")
        time.sleep(1)
    print(f"[ok] {name}: primario elegido en {hosts[0]}")


def configure_sharding() -> None:
    mongos = MongoClient(MONGOS_URI, serverSelectionTimeoutMS=60000)
    mongos.admin.command("ping")

    existing = {s["_id"] for s in mongos.admin.command("listShards")["shards"]}
    for spec in SHARDS.split(";"):
        name, _ = parse_rs(spec)
        if name not in existing:
            mongos.admin.command("addShard", spec, name=name)
            print(f"[+] shard {name} agregado")

    zones = dict(z.split(":") for z in SHARD_ZONES.split(","))
    for shard, zone in zones.items():
        mongos.admin.command("addShardToZone", shard, zone=zone)

    mongos.admin.command("enableSharding", DB)
    sharded = {c["_id"] for c in mongos.config.collections.find({"_id": {"$regex": f"^{DB}\\."}})}
    for coll, key in (
        ("users", {"_id": "hashed"}),
        ("products", {"_id": "hashed"}),
        ("orders", {"country": 1, "_id": 1}),
    ):
        ns = f"{DB}.{coll}"
        if ns not in sharded:
            mongos.admin.command("shardCollection", ns, key=key)
            print(f"[+] {ns} fragmentada con shard key {key}")

    for zone, (lo, hi) in ZONE_RANGES.items():
        mongos.admin.command("updateZoneKeyRange", f"{DB}.orders", min=lo, max=hi, zone=zone)
    print("[ok] zonas NORTE/SUR asignadas a orders")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["all", "replicasets", "sharding"], default="all")
    step = parser.parse_args().step

    print(f"== Inicializando clúster MongoDB de CompraYa (paso: {step}) ==")
    if step in ("all", "replicasets"):
        init_replica_set(CONFIG_RS, configsvr=True)
        for spec in SHARDS.split(";"):
            init_replica_set(spec)
    if step in ("all", "sharding"):
        configure_sharding()
    print("== Listo ==")


if __name__ == "__main__":
    main()
