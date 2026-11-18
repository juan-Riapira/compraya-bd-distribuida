// Arranque de la tienda: detecta el sistema (A/B), el cliente y la navegación.
import { api } from "./api.js";
import { setState, state, subscribe } from "./state.js";
import { initLatencyBar } from "./ui/latency.js";
import { toastError } from "./ui/toast.js";
import { initCart, refreshCart } from "./views/cart.js";
import { initCatalog } from "./views/catalog.js";
import { loadOrders } from "./views/orders.js";

const SYSTEM_LABEL = {
  A: "Sistema A · PostgreSQL único",
  B: "Sistema B · MongoDB distribuido + Redis",
};

async function detectSystem() {
  const badge = document.getElementById("system-badge");
  try {
    const health = await api.health();
    document.documentElement.dataset.system = health.system;
    badge.textContent = SYSTEM_LABEL[health.system] + (health.instance ? ` (${health.instance})` : "");
    document.title = `CompraYa — Sistema ${health.system}`;
  } catch {
    badge.textContent = "Servidor sin respuesta";
  }
}

function initUserPicker() {
  const form = document.getElementById("user-form");
  const input = document.getElementById("user-id");
  const nameEl = document.getElementById("user-name");
  input.value = state.userId;

  const apply = async () => {
    const id = input.value.trim().toUpperCase();
    try {
      const user = await api.user(id);
      setState({ userId: id, user });
      await refreshCart();
      if (location.hash === "#pedidos") loadOrders();
    } catch (error) {
      toastError(error);
    }
  };
  form.addEventListener("submit", (e) => { e.preventDefault(); apply(); });
  input.addEventListener("change", apply);
  subscribe(({ user }) => { nameEl.textContent = user ? `${user.name} (${user.country})` : ""; });
  return apply;
}

function route() {
  const tab = location.hash === "#pedidos" ? "pedidos" : "catalogo";
  document.getElementById("view-catalogo").hidden = tab !== "catalogo";
  document.getElementById("view-pedidos").hidden = tab !== "pedidos";
  document.querySelectorAll(".tabs a").forEach((a) => {
    if (a.dataset.tab === tab) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  if (tab === "pedidos") loadOrders();
}

async function main() {
  initLatencyBar();
  initCart();
  await detectSystem();
  const loadUser = initUserPicker();
  window.addEventListener("hashchange", route);
  route();
  await Promise.all([loadUser(), initCatalog()]);
}

main();
