// Aviso breve en la parte inferior de la pantalla.

const el = document.getElementById("toast");
let timer;

export function toast(message, kind = "info") {
  el.textContent = message;
  el.dataset.kind = kind;
  el.hidden = false;
  clearTimeout(timer);
  timer = setTimeout(() => { el.hidden = true; }, 3500);
}

// Traduce los errores de la API a instrucciones claras para el comprador.
export function toastError(error) {
  const messages = {
    insufficient_stock: "Ese producto se agotó. Quítalo del carrito para continuar.",
    payment_declined: "La pasarela rechazó el pago. No se cobró nada; intenta de nuevo.",
    empty_cart: "Tu carrito está vacío. Agrega un producto primero.",
    not_found: error.message,
    duplicate_request: "Ya hay un pago en curso. Espera a que termine.",
  };
  const text = messages[error.code] || `El servidor no respondió bien (${error.status || "sin conexión"}). Intenta de nuevo.`;
  toast(text, "error");
}
