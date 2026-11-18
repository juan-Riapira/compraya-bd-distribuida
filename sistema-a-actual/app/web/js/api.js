// Cliente HTTP de la tienda. Única capa que conoce las rutas de la API.
// Cada llamada mide su tiempo y lo anuncia con el evento "api:timing".

export class ApiError extends Error {
  constructor(status, code, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
    this.code = code;
  }
}

async function request(method, path, { body, label, headers } = {}) {
  const started = performance.now();
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json", ...headers },
      body: body ? JSON.stringify(body) : undefined,
    });
  } finally {
    const ms = performance.now() - started;
    window.dispatchEvent(new CustomEvent("api:timing", { detail: { label: label || path, ms } }));
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data?.error, data?.detail);
  return data;
}

export const api = {
  health: () => request("GET", "/health", { label: "Salud" }),
  categories: () => request("GET", "/api/v1/products/categories", { label: "Categorías" }),
  products: ({ limit, offset, category }) => {
    const q = new URLSearchParams({ limit, offset });
    if (category) q.set("category", category);
    return request("GET", `/api/v1/products?${q}`, { label: "Catálogo" });
  },
  deals: () => request("GET", "/api/v1/products/deals", { label: "Ofertas" }),
  product: (id) => request("GET", `/api/v1/products/${id}`, { label: "Producto" }),
  user: (id) => request("GET", `/api/v1/users/${id}`, { label: "Cliente" }),
  cart: (userId) => request("GET", `/api/v1/carts/${userId}`, { label: "Carrito" }),
  addToCart: (userId, productId, quantity = 1) =>
    request("POST", `/api/v1/carts/${userId}/items`, {
      body: { product_id: productId, quantity }, label: "Agregar al carrito",
    }),
  removeFromCart: (userId, productId) =>
    request("DELETE", `/api/v1/carts/${userId}/items/${productId}`, { label: "Quitar del carrito" }),
  checkout: (userId) =>
    request("POST", "/api/v1/orders/checkout", {
      body: { user_id: userId }, label: "Pago",
      headers: { "Idempotency-Key": crypto.randomUUID() },
    }),
  orders: (userId) => request("GET", `/api/v1/users/${userId}/orders`, { label: "Pedidos" }),
};
