// Formato de números y textos para la interfaz.

const money = new Intl.NumberFormat("es-CO", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const dateTime = new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" });

export const formatMoney = (value) => money.format(value);
export const formatDate = (iso) => dateTime.format(new Date(iso));
export const formatMs = (ms) => (ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`);

export function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
