// Carrito: cajón lateral, agregar/quitar productos y pagar.
import { api } from "../api.js";
import { escapeHtml, formatMoney, formatMs } from "../format.js";
import { setState, state, subscribe } from "../state.js";
import { toast, toastError } from "../ui/toast.js";

const drawer = document.getElementById("cart-drawer");
const scrim = document.getElementById("scrim");
const itemsEl = document.getElementById("cart-items");
const totalEl = document.getElementById("cart-total");
const countEl = document.getElementById("cart-count");
const checkoutBtn = document.getElementById("checkout");

export function initCart() {
  document.getElementById("cart-open").addEventListener("click", openDrawer);
  document.getElementById("cart-close").addEventListener("click", closeDrawer);
  scrim.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => e.key === "Escape" && closeDrawer());
  itemsEl.addEventListener("click", onRemove);
  checkoutBtn.addEventListener("click", checkout);
  subscribe(render);
}

export async function refreshCart() {
  try {
    setState({ cart: await api.cart(state.userId) });
  } catch (error) {
    setState({ cart: { items: [], total: 0 } });
    toastError(error);
  }
}

export async function addToCart(productId) {
  try {
    setState({ cart: await api.addToCart(state.userId, productId, 1) });
    toast(`Agregado al carrito: ${productId}`, "ok");
  } catch (error) {
    toastError(error);
  }
}

async function onRemove(event) {
  const btn = event.target.closest("[data-remove]");
  if (!btn) return;
  try {
    setState({ cart: await api.removeFromCart(state.userId, btn.dataset.remove) });
  } catch (error) {
    toastError(error);
  }
}

async function checkout() {
  checkoutBtn.disabled = true;
  checkoutBtn.textContent = "Procesando pago…";
  const started = performance.now();
  try {
    const order = await api.checkout(state.userId);
    toast(`Pedido pagado por ${formatMoney(order.total)} en ${formatMs(performance.now() - started)}.`, "ok");
    await refreshCart();
    closeDrawer();
    window.dispatchEvent(new Event("catalog:refresh"));
  } catch (error) {
    toastError(error);
  } finally {
    checkoutBtn.disabled = false;
    checkoutBtn.textContent = "Pagar ahora";
  }
}

function render({ cart }) {
  const units = cart.items.reduce((n, i) => n + i.quantity, 0);
  countEl.textContent = units;
  totalEl.textContent = formatMoney(cart.total);
  checkoutBtn.hidden = cart.items.length === 0;
  itemsEl.innerHTML = cart.items.length
    ? cart.items.map((i) => `
        <div class="cart-line">
          <strong>${escapeHtml(i.product_id)} × ${i.quantity}</strong>
          <button type="button" class="remove" data-remove="${i.product_id}">Quitar</button>
          <small>${formatMoney(i.unit_price)} c/u · ${formatMoney(i.subtotal)}</small>
        </div>`).join("")
    : `<p class="empty">Tu carrito está vacío. Agrega productos desde el catálogo.</p>`;
}

function openDrawer() {
  drawer.setAttribute("aria-hidden", "false");
  scrim.hidden = false;
  refreshCart();
}

function closeDrawer() {
  drawer.setAttribute("aria-hidden", "true");
  scrim.hidden = true;
}
