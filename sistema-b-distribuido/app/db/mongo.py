"""Conexión a MongoDB a través del router `mongos`.

La aplicación no sabe cuántos shards hay ni dónde vive cada documento:
`mongos` enruta cada operación al shard correcto usando la shard key.
"""
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from app.core.config import Settings

# Colecciones del modelo documental
USERS = "users"
PRODUCTS = "products"
ORDERS = "orders"


class MongoConnection:
    def __init__(self, settings: Settings):
        self._client: AsyncMongoClient = AsyncMongoClient(
            settings.mongo_uri,
            maxPoolSize=settings.mongo_max_pool_size,
            retryWrites=True,
            retryReads=True,
            # Escrituras confirmadas por la mayoría de cada réplica: sobreviven
            # a la caída del nodo primario de un shard.
            w="majority",
            serverSelectionTimeoutMS=5000,
        )
        self._db_name = settings.mongo_db

    @property
    def client(self) -> AsyncMongoClient:
        return self._client

    @property
    def db(self) -> AsyncDatabase:
        return self._client.get_database(
            self._db_name,
            write_concern=WriteConcern("majority"),
            read_concern=ReadConcern("local"),
        )

    async def ping(self) -> None:
        await self._client.admin.command("ping")

    async def close(self) -> None:
        await self._client.close()
