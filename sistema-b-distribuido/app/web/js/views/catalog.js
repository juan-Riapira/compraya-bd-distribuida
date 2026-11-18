// Vista del catálogo: filtros por categoría, grilla de productos y paginación.
import { api } from "../api.js";
import { escapeHtml, formatMoney } from "../format.js";
import { toastError } from "../ui/toast.js";
import { addToCart } from "./cart.js";
import { openProduct } from "./product-dialog.js";
import { stockMarkup } from "../ui/stock.js";

const PAGE_SIZE = 24;
const HOT_LIMIT = 20;     // P00001..P00020 son las ofertas del día

const grid = document.getElementById("product-grid");
const filters = document.getElementById("category-filters");
const pageLabel = document.getElementById("page-label");
const prev = document.getElementById("prev-page");
const next = document.getElementById("next-page");
const pager = document.querySelector(".pager");

const DEALS = "__deals__";
const view = { page: 0, category: DEALS };

export async function initCatalog() {
  prev.addEventListener("click", () => goTo(view.page - 1));
  next.addEventListener("click", () => goTo(view.page + 1));
  grid.addEventListener("click", onGridClick);
  window.addEventListener("catalog:refresh", () => load());
  await renderFilters();
  await load();
}

async function renderFilters() {
  try {
    const categories = await api.categories();
    const chips = [[DEALS, "Ofertas del día"], ["", "Todo"], ...categories.map((c) => [c, c])];
    filters.innerHTML = chips
      .map(([value, label]) => `<button type="button" class="chip" data-category="${escapeHtml(value)}" aria-pressed="${value === view.category}">${escapeHtml(label)}</button>`)
      .join("");
    filters.addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (!chip) return;
      filters.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
      view.category = chip.dataset.category || null;
      goTo(0);
    });
  } catch (error) {
    toastError(error);
  }
}

function goTo(page) {
  view.page = Math.max(0, page);
  load();
}

async function load() {
  try {
    if (view.category === DEALS) return renderPage(await api.deals(), false);
    const data = await api.products({ limit: PAGE_SIZE, offset: view.page * PAGE_SIZE, category: view.category });
    renderPage(data.items, true);
  } catch (error) {
    toastError(error);
  }
}

function renderPage(items, paginated) {
  grid.innerHTML = items.length
    ? items.map(productTile).join("")
    : `<p class="empty">No hay productos en esta categoría.</p>`;
  pager.hidden = !paginated;
  pageLabel.textContent = `Página ${view.page + 1}`;
  prev.disabled = view.page === 0;
  next.disabled = items.length < PAGE_SIZE;
}

function productTile(p) {
  const isDeal = Number(p.id.slice(1)) <= HOT_LIMIT;
  return `<article class="product">
      <div class="product-top">
        <span class="product-cat">${escapeHtml(p.category)}</span>
        <span class="product-id">${p.id}</span>
      </div>
      ${isDeal ? `<span class="deal">Oferta del día</span>` : ""}
      <button type="button" class="product-name" data-open="${p.id}">${escapeHtml(p.name)}</button>
      <div class="price">${formatMoney(p.price)}</div>
      ${stockMarkup(p.stock)}
      <button type="button" class="add" data-add="${p.id}" ${p.stock === 0 ? "disabled" : ""}>Agregar al carrito</button>
    </article>`;
}

async function onGridClick(event) {
  const add = event.target.closest("[data-add]");
  const open = event.target.closest("[data-open]");
  if (add) await addToCart(add.dataset.add);
  if (open) await openProduct(open.dataset.open);
}
