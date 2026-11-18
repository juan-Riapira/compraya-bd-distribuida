// Formato de números y textos.

const n0 = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const n1 = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 });
const dt = new Intl.DateTimeFormat("es-CO", { dateStyle: "short", timeStyle: "short" });

export const fmtInt = (v) => (v == null ? "—" : n0.format(v));
export const fmtDec = (v) => (v == null ? "—" : n1.format(v));
export const fmtMs = (v) => (v == null ? "—" : v < 1000 ? `${n0.format(v)} ms` : `${n1.format(v / 1000)} s`);
export const fmtDate = (iso) => dt.format(new Date(iso));

export function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export const SCENARIO_NAMES = { black_friday: "Black Friday", flash_sale: "Venta relámpago", failover: "Caída de un nodo" };
