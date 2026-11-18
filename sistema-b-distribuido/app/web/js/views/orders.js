// Vista "Mis pedidos" del cliente actual.
import { api } from "../api.js";
import { escapeHtml, formatDate, formatMoney } from "../format.js";
import { state } from "../state.js";
import { toastError } from "../ui/toast.js";

const list = document.getElementById("orders-list");

export async function loadOrders() {
  try {
    const orders = await api.orders(state.userId);
    list.innerHTML = orders.length
      ? orders.map(orderCard).join("")
      : `<p class="empty">Este cliente aún no tiene pedidos. Compra algo desde el catálogo.</p>`;
  } catch (error) {
    list.innerHTML = "";
    toastError(error);
  }
}

function orderCard(o) {
  const lines = o.items
    .map((i) => `<li>${escapeHtml(i.product_id)} × ${i.quantity} — ${formatMoney(i.unit_price)}</li>`)
    .join("");
  return `<article class="order">
      <div class="order-head">
        <strong>${formatMoney(o.total)}</strong>
        <span class="order-meta">${formatDate(o.created_at)} · ${o.status === "PAID" ? "Pagado" : escapeHtml(o.status)}</span>
      </div>
      <div class="order-meta">Pedido ${o.id}${o.payment ? ` · referencia de pago ${escapeHtml(o.payment.provider_ref)}` : ""}</div>
      <ul>${lines}</ul>
    </article>`;
}
