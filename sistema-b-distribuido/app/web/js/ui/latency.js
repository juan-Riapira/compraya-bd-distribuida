// Barra inferior: muestra el tiempo de respuesta de las últimas llamadas a la API.
import { escapeHtml, formatMs } from "../format.js";

const MAX_ENTRIES = 6;
const SLOW_MS = 500;
const log = document.getElementById("latency-log");

export function initLatencyBar() {
  window.addEventListener("api:timing", ({ detail }) => {
    const li = document.createElement("li");
    if (detail.ms >= SLOW_MS) li.dataset.slow = "";
    li.innerHTML = `${escapeHtml(detail.label)} <b>${formatMs(detail.ms)}</b>`;
    log.prepend(li);
    while (log.children.length > MAX_ENTRIES) log.lastElementChild.remove();
  });
}
