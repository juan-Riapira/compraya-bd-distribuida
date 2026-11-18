// Ventana de detalle de un producto (consulta el stock actual al abrirse).
import { api } from "../api.js";
import { escapeHtml, formatMoney } from "../format.js";
import { toastError } from "../ui/toast.js";
import { addToCart } from "./cart.js";
import { stockMarkup } from "../ui/stock.js";

const dialog = document.getElementById("product-dialog");

export async function openProduct(productId) {
  try {
    const p = await api.product(productId);
    dialog.innerHTML = `
      <span class="product-cat">${escapeHtml(p.category)} · ${p.id}</span>
      <h2>${escapeHtml(p.name)}</h2>
      <p>${escapeHtml(p.description)}</p>
      <div class="price">${formatMoney(p.price)}</div>
      ${stockMarkup(p.stock)}
      <div class="dialog-actions">
        <button type="button" class="primary" data-add ${p.stock === 0 ? "disabled" : ""}>Agregar al carrito</button>
        <button type="button" class="ghost" data-close>Cerrar</button>
      </div>`;
    dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());
    dialog.querySelector("[data-add]").addEventListener("click", async () => {
      await addToCart(p.id);
      dialog.close();
    });
    dialog.showModal();
  } catch (error) {
    toastError(error);
  }
}
