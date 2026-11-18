"""Convención de nombres de llaves en Redis (un solo lugar para todas)."""


def product(product_id: str) -> str:
    return f"product:{product_id}"


def product_list(category: str | None, limit: int, offset: int) -> str:
    return f"products:list:{category or '*'}:{limit}:{offset}"


def stock(product_id: str) -> str:
    return f"stock:{product_id}"


def cart(user_id: str) -> str:
    return f"cart:{user_id}"


def idempotency(key: str) -> str:
    return f"idem:{key}"
