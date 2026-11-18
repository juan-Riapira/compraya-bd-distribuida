"""Pruebas de las transformaciones del ETL (funciones puras, no necesitan bases de datos)."""
from datetime import UTC, datetime
from decimal import Decimal

from etl import transform as T

NOW = datetime(2026, 11, 27, tzinfo=UTC)


def test_to_cents_redondea_sin_coma_flotante():
    assert T.to_cents(Decimal("698.45")) == 69845
    assert T.to_cents("0.005") == 1
    assert T.to_cents(None) == 0


def test_producto_embebe_categoria_stock_y_marca():
    doc = T.product_doc({
        "id": "P00001", "name": "Portátil Nova 859", "description": "Producto 1 de la categoría Portátiles, marca Nova.",
        "price": Decimal("698.45"), "created_at": NOW, "category_id": 2, "category_name": "Portátiles", "stock": 300,
    })
    assert doc["_id"] == "P00001"
    assert doc["price_cents"] == 69845
    assert doc["category"] == {"id": 2, "name": "Portátiles"}
    assert doc["stock"] == 300
    assert doc["attributes"] == {"marca": "Nova"}


def test_pedido_de_tres_tablas_queda_en_un_documento_con_shard_key():
    doc = T.order_doc({
        "id": "o-1", "user_id": "U00001", "country": "pe", "status": "PAID", "total": Decimal("1396.90"),
        "created_at": NOW, "payment_status": "APPROVED", "provider_ref": "pay_x", "payment_amount": Decimal("1396.90"),
        "items": '[{"product_id": "P00001", "name": "Portátil Nova 859", "quantity": 2, "unit_price": 698.45}]',
    })
    assert doc["country"] == "PE"
    assert doc["items"] == [{"product_id": "P00001", "name": "Portátil Nova 859", "quantity": 2, "unit_price_cents": 69845}]
    assert doc["total_cents"] == doc["payment"]["amount_cents"] == 139690


def test_pedido_sin_pago_queda_con_payment_nulo():
    doc = T.order_doc({
        "id": "o-2", "user_id": "U00002", "country": "CL", "status": "PENDING", "total": 10, "created_at": NOW,
        "payment_status": None, "provider_ref": None, "payment_amount": None, "items": [],
    })
    assert doc["payment"] is None


def test_carritos_se_agrupan_por_usuario():
    rows = [
        {"user_id": "U1", "product_id": "P1", "quantity": 2},
        {"user_id": "U1", "product_id": "P2", "quantity": 1},
        {"user_id": "U2", "product_id": "P1", "quantity": 3},
    ]
    assert T.cart_hashes(rows) == {"U1": {"P1": 2, "P2": 1}, "U2": {"P1": 3}}
