// Panel "Redis en vivo": consulta /admin/redis cada segundo y dibuja llaves y TTL.
const POLL_MS = 1000;
const LABELS = { product: "Productos", list: "Páginas del catálogo", stock: "Stock", cart: "Carritos", idem: "Idempotencia" };

const el = (id) => document.getElementById(id);
const state = { group: "product", previous: new Map(), firstLoad: true, groups: [] };

function fmtDuration(s) {
  if (s < 0) return "no vence";
  if (s >= 86400) return `${Math.floor(s / 86400)} d ${Math.floor((s % 86400) / 3600)} h`;
  if (s >= 3600) return `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min`;
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function esc(t) {
  return String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
}

function renderGroups(groups) {
  state.groups = groups;
  el("rp-groups").innerHTML = groups.map((g) => `
    <button type="button" class="rp-group" role="tab" data-group="${g.id}" aria-selected="${g.id === state.group}">
      <span>${LABELS[g.id] ?? g.id}</span>
      <b>${g.count.toLocaleString("es-CO")}</b>
      <span class="pat">${esc(g.pattern)}</span>
      <span class="why">${esc(g.purpose)} · ${g.configured_ttl_s ? "vence en " + fmtDuration(g.configured_ttl_s) : "no vence"}</span>
    </button>`).join("");
  const current = groups.find((g) => g.id === state.group);
  el("rp-clear").hidden = !current?.clearable;
}

function renderRows(keys) {
  const maxTtl = state.groups.find((g) => g.id === state.group)?.configured_ttl_s;
  const rows = keys.map((k) => {
    const isNew = !state.firstLoad && !state.previous.has(k.key);
    const pct = maxTtl && k.ttl_s >= 0 ? Math.max(0, Math.min(100, (k.ttl_s / maxTtl) * 100)) : 100;
    const low = maxTtl && k.ttl_s >= 0 && k.ttl_s <= Math.min(10, maxTtl * 0.1);
    return `<tr class="${isNew ? "is-new" : ""}">
      <td class="key">${esc(k.key)}</td>
      <td>${esc(k.type)}</td>
      <td class="ttl ${low ? "low" : ""}">
        <span class="ttl-text">${fmtDuration(k.ttl_s)}</span>
        <div class="ttl-bar" aria-hidden="true"><span style="width:${pct}%"></span></div>
      </td>
      <td class="val">${esc(k.preview)}</td>
    </tr>`;
  });
  el("rp-rows").innerHTML = rows.join("");
  const empty = el("rp-empty");
  empty.hidden = keys.length > 0;
  if (!keys.length) {
    empty.textContent = state.group === "product"
      ? "La caché de productos está vacía. Consulta un producto y verás aparecer su llave con 5 minutos de vida."
      : "No hay llaves en este grupo todavía.";
  }
}

function logGone(keys) {
  const now = new Date();
  const seen = new Set(keys.map((k) => k.key));
  const gone = [...state.previous.entries()].filter(([key]) => !seen.has(key));
  if (!gone.length) return;
  el("rp-log-empty").hidden = true;
  const html = gone.map(([key, ttl]) => `<li><code>${esc(key)}</code><span>${now.toLocaleTimeString("es-CO")} · ${
    ttl <= 2 && ttl >= 0 ? "expiró (TTL llegó a 0)" : "borrada"}</span></li>`).join("");
  el("rp-log-list").insertAdjacentHTML("afterbegin", html);
}

async function poll() {
  try {
    const res = await fetch(`/admin/redis?group=${state.group}&limit=40`);
    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();
    renderGroups(data.groups);
    renderRows(data.keys);
    if (!state.firstLoad) logGone(data.keys);
    state.previous = new Map(data.keys.map((k) => [k.key, k.ttl_s]));
    state.firstLoad = false;
  } catch (err) {
    el("rp-empty").hidden = false;
    el("rp-empty").textContent = `No se pudo leer Redis (${err.message}). ¿Está corriendo el Sistema B?`;
  }
}

el("rp-groups").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-group]");
  if (!btn || btn.dataset.group === state.group) return;
  state.group = btn.dataset.group;
  state.previous = new Map();
  state.firstLoad = true;
  poll();
});

el("rp-probe").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = el("rp-product").value.trim().toUpperCase();
  const wasCached = state.group === "product" && state.previous.has(`product:${id}`);
  const t0 = performance.now();
  const res = await fetch(`/api/v1/products/${encodeURIComponent(id)}`);
  const ms = Math.round(performance.now() - t0);
  const out = el("rp-probe-result");
  if (!res.ok) { out.textContent = `${id} no existe`; return; }
  const p = await res.json();
  out.innerHTML = `<strong>${esc(p.name)}</strong> en ${ms} ms · ${
    wasCached ? "salió de Redis (caché)" : "no estaba en caché: se leyó de MongoDB y se guardó en Redis"}`;
  poll();
});

el("rp-clear").addEventListener("click", async () => {
  const res = await fetch("/admin/redis/cache", { method: "DELETE" });
  const { deleted } = await res.json();
  el("rp-probe-result").textContent = `Se borraron ${deleted.toLocaleString("es-CO")} llaves de caché. La próxima consulta irá a MongoDB.`;
  poll();
});

poll();
setInterval(poll, POLL_MS);
