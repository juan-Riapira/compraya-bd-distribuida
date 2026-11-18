// Tabla comparativa A vs B y una frase con la conclusión de la corrida.
import { escapeHtml, fmtDec, fmtInt, fmtMs } from "../format.js";

const box = document.getElementById("results");
const table = document.getElementById("compare-table");
const verdictEl = document.getElementById("verdict");

// [etiqueta, cómo leer el valor, formato, qué es mejor]
const COMMON = [
  ["Peticiones respondidas", (r) => r.summary.served ?? r.summary.requests, fmtInt, "high"],
  ["Respondidas por segundo", (r) => r.summary.rps, fmtDec, "high"],
  ["Latencia p50", (r) => r.summary.p50_ms, fmtMs, "low"],
  ["Latencia p95", (r) => r.summary.p95_ms, fmtMs, "low"],
  ["Latencia p99", (r) => r.summary.p99_ms, fmtMs, "low"],
  ["Compras completadas", (r) => r.summary.checkouts_ok, fmtInt, "high"],
  ["Peticiones enviadas", (r) => r.summary.requests, fmtInt, null],
  ["Fallas técnicas (5xx / timeouts)", (r) => r.summary.failures, fmtInt, "low"],
  ["Checkout p95", (r) => r.summary.endpoints?.checkout?.p95_ms, fmtMs, "low"],
];
const BY_SCENARIO = {
  flash_sale: [
    ["Compras por segundo", (r) => r.extra.checkouts_per_s, fmtDec, "high"],
    ["Tiempo para atender a todos", (r) => r.extra.wall_time_s * 1000, fmtMs, "low"],
    ["Pagos rechazados por la pasarela", (r) => r.extra.payment_declined, fmtInt, null],
    ["Agotados (409)", (r) => r.extra.sold_out, fmtInt, null],
  ],
  failover: [
    ["Segundos sin vender (nodo caído)", (r) => r.extra.seconds_without_sales, fmtInt, "low"],
    ["Segundos sin ninguna respuesta", (r) => r.extra.seconds_without_any_response, fmtInt, "low"],
    ["Se recuperó sin intervención", (r) => r.extra.self_recovered, yesNo, null],
    ["Volvió a vender a los", (r) => (r.extra.recovered_after_s == null ? null : r.extra.recovered_after_s * 1000), fmtMs, "low"],
  ],
};

function yesNo(v) {
  if (v == null) return "—";
  return `<span class="badge ${v ? "yes" : "no"}">${v ? "Sí" : "No"}</span>`;
}

function consistencyCell(r) {
  const c = r.consistency;
  if (!c) return "—";
  const detail = c.consistent ? "" : ` (${c.invariant_violations} errores, ${c.negative_stock} negativos)`;
  return `${yesNo(c.consistent)}${detail}`;
}

export function showResults(run) {
  const systems = Object.keys(run.results).sort();
  if (!systems.length || !systems.some((s) => run.results[s].summary?.requests)) {
    box.hidden = true;
    return;
  }
  const rows = [...(BY_SCENARIO[run.scenario] || []), ...COMMON];
  const head = `<thead><tr><th>Métrica</th>${systems.map((s) => `<th data-system="${s}">Sistema ${s}</th>`).join("")}</tr></thead>`;
  const body = rows.map(([label, get, fmt, better]) => {
    const values = systems.map((s) => safe(() => get(run.results[s])));
    const best = bestIndex(values, better);
    const cells = values.map((v, i) => `<td class="${i === best ? "best" : ""}">${fmt(v)}</td>`).join("");
    return `<tr><td>${escapeHtml(label)}</td>${cells}</tr>`;
  }).join("");
  const consistency = `<tr><td>Inventario consistente (nunca se vendió de más)</td>${systems.map((s) => `<td>${consistencyCell(run.results[s])}</td>`).join("")}</tr>`;
  table.innerHTML = `${head}<tbody>${body}${consistency}</tbody>`;
  verdictEl.textContent = verdict(run);
  box.hidden = false;
}

function safe(fn) {
  try { return fn() ?? null; } catch { return null; }
}

function bestIndex(values, better) {
  if (!better || values.length < 2 || values.some((v) => v == null) || values[0] === values[1]) return -1;
  return better === "high" ? (values[0] > values[1] ? 0 : 1) : (values[0] < values[1] ? 0 : 1);
}

function verdict(run) {
  const a = run.results.A;
  const b = run.results.B;
  if (!a || !b) return "Corre los dos sistemas para ver la comparación.";
  if (run.scenario === "flash_sale") {
    const ratio = b.extra.checkouts_per_s / Math.max(a.extra.checkouts_per_s, 0.1);
    return `Con ${a.extra.buyers} compradores sobre el mismo producto, A completó ${fmtDec(a.extra.checkouts_per_s)} compras/s y B ${fmtDec(b.extra.checkouts_per_s)} compras/s (${fmtDec(ratio)} veces). A tardó ${fmtMs(a.extra.wall_time_s * 1000)} en atender a todos; B, ${fmtMs(b.extra.wall_time_s * 1000)}.`;
  }
  if (run.scenario === "failover") {
    const rec = (r) => (r.extra.self_recovered ? `volvió a vender solo a los ${r.extra.recovered_after_s} s` : "no se recuperó hasta la reparación");
    return `Con el nodo caído, A estuvo ${a.extra.seconds_without_sales} s sin vender y ${rec(a)}; B estuvo ${b.extra.seconds_without_sales} s sin vender y ${rec(b)}.`;
  }
  const diff = ((b.summary.rps - a.summary.rps) / Math.max(a.summary.rps, 0.1)) * 100;
  const more = diff >= 0 ? `${fmtDec(diff)} % más` : `${fmtDec(-diff)} % menos`;
  return `Con ${run.params.users} compradores, B respondió ${more} peticiones por segundo que A. Latencia p95: A ${fmtMs(a.summary.p95_ms)}, B ${fmtMs(b.summary.p95_ms)}.`;
}
