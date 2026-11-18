"""Escenario de carga "Black Friday" para CompraYa.

El MISMO escenario se lanza contra el Sistema A y el Sistema B (solo cambia
--host). Cada usuario virtual navega como un comprador real:

    ver catálogo (6)  ·  ver producto (5)  ·  agregar al carrito (2)  ·  pagar (1)

El 80 % del interés se concentra en 20 productos "calientes" (las ofertas del
día), que es justo lo que provoca bloqueos en el sistema actual.

Resultados de negocio que NO cuentan como falla técnica:
    402 pago rechazado por la pasarela · 409 producto agotado · 400 carrito vacío
Falla técnica = 5xx, timeouts o errores de conexión.
"""
import random
import uuid

from locust import FastHttpUser, between, task

N_USERS = 5000
N_PRODUCTS = 2000
HOT_PRODUCTS = [f"P{i:05d}" for i in range(1, 21)]
CATEGORIES = ["Celulares", "Portátiles", "Tablets", "Audio", "Monitores", "Accesorios", "Gaming"]
BUSINESS_OUTCOMES = {400, 402, 409}


def pick_product() -> str:
    if random.random() < 0.8:
        return random.choice(HOT_PRODUCTS)
    return f"P{random.randint(21, N_PRODUCTS):05d}"


class Shopper(FastHttpUser):
    wait_time = between(0.1, 0.6)

    def on_start(self) -> None:
        self.user_id = f"U{random.randint(1, N_USERS):05d}"

    def _expect(self, resp, ok=(200, 201)) -> None:
        if resp.status_code in ok or resp.status_code in BUSINESS_OUTCOMES:
            resp.success()
        else:
            resp.failure(f"HTTP {resp.status_code}")

    @task(6)
    def browse_catalog(self) -> None:
        params = {"limit": 20, "offset": random.choice([0, 20, 40, 60])}
        if random.random() < 0.5:
            params["category"] = random.choice(CATEGORIES)
        with self.client.get("/api/v1/products", params=params, name="GET /products", catch_response=True) as r:
            self._expect(r)

    @task(5)
    def view_product(self) -> None:
        with self.client.get(f"/api/v1/products/{pick_product()}", name="GET /products/{id}", catch_response=True) as r:
            self._expect(r)

    @task(2)
    def add_to_cart(self) -> None:
        body = {"product_id": pick_product(), "quantity": random.randint(1, 2)}
        with self.client.post(
            f"/api/v1/carts/{self.user_id}/items", json=body, name="POST /carts/{id}/items", catch_response=True
        ) as r:
            self._expect(r)

    @task(1)
    def checkout(self) -> None:
        headers = {"Idempotency-Key": uuid.uuid4().hex}
        with self.client.post(
            "/api/v1/orders/checkout", json={"user_id": self.user_id}, headers=headers,
            name="POST /orders/checkout", catch_response=True,
        ) as r:
            self._expect(r)
