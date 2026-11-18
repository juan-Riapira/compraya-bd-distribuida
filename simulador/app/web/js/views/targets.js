// Tarjetas de estado de los sistemas A y B (en línea, pedidos, abrir tienda, reiniciar).
import { api } from "../api.js";
import { escapeHtml, fmtInt } from "../format.js";

const container = document.getElementById("targets");
const NAMES = { A: "Sistema A · PostgreSQL único", B: "Sistema B · Distribuido" };

export function initTargets() {
  container.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-reset]");
    if (!btn) return;
    btn.disabled = true;
    btn.textContent = "Reiniciando…";
    try {
      await api.resetTarget(btn.dataset.reset);
    } catch (error) {
      alert(error.message);
    }
    await refreshTargets();
  });
  refreshTargets();
  setInterval(refreshTargets, 5000);
}

export async function refreshTargets() {
  try {
    const data = await api.targets();
    container.innerHTML = ["A", "B"].map((s) => card(data[s])).join("");
  } catch {
    container.innerHTML = `<p class="empty">No se pudo consultar el estado de los sistemas.</p>`;
  }
}

function card(t) {
  const online = t.health.online;
  const stats = t.stats;
  return `<div class="target" data-system="${t.system}">
      <div class="target-head">
        <strong>${NAMES[t.system]}</strong>
        <span class="dot" data-online="${online}">${online ? "En línea" : "Sin respuesta"}</span>
      </div>
      <span class="target-meta">${escapeHtml(t.url)}${t.health.instance ? ` · ${escapeHtml(t.health.instance)}` : ""}</span>
      <span class="target-meta">${stats ? `${fmtInt(stats.orders)} pedidos · ${fmtInt(stats.units_sold)} unidades vendidas` : "—"}</span>
      <div class="target-actions">
        <a class="link-btn" href="${escapeHtml(t.public_url)}" target="_blank" rel="noopener">Abrir tienda</a>
        <button type="button" class="link-btn" data-reset="${t.system}" ${online ? "" : "disabled"}>Reiniciar datos</button>
      </div>
    </div>`;
}
