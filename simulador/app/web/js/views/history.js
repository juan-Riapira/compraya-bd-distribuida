// Historial de corridas guardadas; al hacer clic se vuelven a mostrar sus gráficas.
import { api } from "../api.js";
import { SCENARIO_NAMES, escapeHtml, fmtDate, fmtDec, fmtMs } from "../format.js";

const table = document.getElementById("history");
let onOpen = () => {};

const STATUS = { done: "Terminada", running: "En curso", failed: "Falló", cancelled: "Detenida", pending: "En cola" };

export function initHistory(openRun) {
  onOpen = openRun;
  table.addEventListener("click", async (e) => {
    const del = e.target.closest("[data-delete]");
    if (del) {
      e.stopPropagation();
      if (confirm("¿Borrar esta corrida del historial?")) {
        await api.deleteRun(del.dataset.delete);
        refreshHistory();
      }
      return;
    }
    const row = e.target.closest("tr[data-id]");
    if (row) onOpen(row.dataset.id);
  });
  refreshHistory();
}

export async function refreshHistory() {
  const { runs } = await api.runs();
  if (!runs.length) {
    table.innerHTML = `<tr><td class="empty">Aún no hay corridas. Elige un escenario y presiona «Iniciar simulación».</td></tr>`;
    return;
  }
  table.innerHTML = `<thead><tr><th>Fecha</th><th>Escenario</th><th>Estado</th><th>Dato clave A</th><th>Dato clave B</th><th></th></tr></thead>
    <tbody>${runs.map(row).join("")}</tbody>`;
}

function keyFigure(scenario, s) {
  if (!s) return "—";
  if (scenario === "flash_sale") return `${fmtDec(s.checkouts_per_s)} compras/s`;
  if (scenario === "failover") return `${s.seconds_without_sales ?? "—"} s sin vender`;
  return `${fmtDec(s.rps)} req/s · p95 ${fmtMs(s.p95_ms)}`;
}

function row(r) {
  return `<tr data-id="${r.id}" title="Ver esta corrida">
      <td>${fmtDate(r.created_at)}</td>
      <td>${escapeHtml(SCENARIO_NAMES[r.scenario] || r.scenario)}</td>
      <td>${STATUS[r.status] || r.status}</td>
      <td class="num-a">${keyFigure(r.scenario, r.summary.A)}</td>
      <td class="num-b">${keyFigure(r.scenario, r.summary.B)}</td>
      <td><button type="button" class="link-btn" data-delete="${r.id}">Borrar</button></td>
    </tr>`;
}
