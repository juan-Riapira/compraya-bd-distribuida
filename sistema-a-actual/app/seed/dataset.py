"""Generador determinista del dataset de CompraYa.

El MISMO archivo existe en ambos sistemas: con la misma semilla produce
exactamente los mismos usuarios, productos y existencias, así las pruebas
de carga comparan los dos sistemas sobre datos idénticos.
"""
import random
from dataclasses import dataclass

SEED = 42
N_PRODUCTS = 2000
N_USERS = 5000
N_HOT_PRODUCTS = 20  # productos "Black Friday" que concentran el tráfico
COUNTRIES = ["CO", "MX", "PE", "CL", "AR"]
CATEGORIES = [
    "Celulares", "Portátiles", "Tablets", "Audio", "Monitores",
    "Accesorios", "Gaming", "Smart Home", "Cámaras", "Wearables",
]
SINGULAR = {
    "Celulares": "Celular", "Portátiles": "Portátil", "Tablets": "Tablet", "Audio": "Audífonos",
    "Monitores": "Monitor", "Accesorios": "Accesorio", "Gaming": "Consola", "Smart Home": "Parlante",
    "Cámaras": "Cámara", "Wearables": "Smartwatch",
}
BRANDS = ["Nova", "Orion", "Andes", "Kappa", "Lumen", "Vértice", "Zenit", "Pulsar"]


@dataclass(frozen=True)
class CategoryRow:
    id: int
    name: str


@dataclass(frozen=True)
class ProductRow:
    id: str
    name: str
    description: str
    price: float
    category_id: int
    category: str
    stock: int
    attributes: dict


@dataclass(frozen=True)
class UserRow:
    id: str
    name: str
    email: str
    country: str


def product_id(n: int) -> str:
    return f"P{n:05d}"


def user_id(n: int) -> str:
    return f"U{n:05d}"


def hot_product_ids() -> list[str]:
    return [product_id(i) for i in range(1, N_HOT_PRODUCTS + 1)]


def build_dataset() -> tuple[list[CategoryRow], list[ProductRow], list[UserRow]]:
    rng = random.Random(SEED)
    categories = [CategoryRow(id=i + 1, name=n) for i, n in enumerate(CATEGORIES)]

    products = []
    for n in range(1, N_PRODUCTS + 1):
        cat = rng.choice(categories)
        brand = rng.choice(BRANDS)
        is_hot = n <= N_HOT_PRODUCTS
        products.append(
            ProductRow(
                id=product_id(n),
                name=f"{SINGULAR[cat.name]} {brand} {rng.randint(100, 999)}",
                description=f"Producto {n} de la categoría {cat.name}, marca {brand}.",
                price=round(rng.uniform(15, 2500), 2),
                category_id=cat.id,
                category=cat.name,
                stock=300 if is_hot else rng.randint(50, 500),
                attributes={"marca": brand, "garantia_meses": rng.choice([6, 12, 24])},
            )
        )

    users = []
    for n in range(1, N_USERS + 1):
        users.append(
            UserRow(
                id=user_id(n),
                name=f"Cliente {n}",
                email=f"cliente{n}@compraya.test",
                country=rng.choice(COUNTRIES),
            )
        )
    return categories, products, users
