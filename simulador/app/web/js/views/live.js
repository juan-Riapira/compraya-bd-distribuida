// Seguimiento en vivo de una corrida: estado, bitácora de eventos y gráficas.
import { api } from "../api.js";
import { SCENARIO_NAMES, escapeHtml } from "../format.js";
import { showResults } from "./results.js";

const statusEl = document.getElementById("run-status");
const log = document.getElementById("event-log");
const outcomesTitle = document.getElementById("chart-3-title");

export class LiveView {
  constructor(charts, { onFinished }) {
    this.charts = charts;
    this.onFinished = onFinished;
    this.source = null;
    this.runId = null;
  }

  async follow(run) {
    this.close();
    this.runId = run.id;
    this.charts.reset();
    log.innerHTML = "";
    document.getElementById("results").hidden = true;
    this.setStatus("running", `${SCENARIO_NAMES[run.scenario]} en curso…`);
    this.setOutcomesTitle(run.scenario);

    this.source = api.stream(run.id);
    this.source.addEventListener("tick", (e) => this.charts.addTick(JSON.parse(e.data)));
    this.source.addEventListener("event", (e) => {
      const ev = JSON.parse(e.data);
      this.charts.addMarker(ev);
      this.appendEvent(ev);
    });
    this.source.addEventListener("status", async (e) => {
      const { status } = JSON.parse(e.data);
      if (["done", "failed", "cancelled"].includes(status)) await this.finish();
    });
    // Por si la corrida terminó antes de conectarnos.
    const fresh = await api.run(run.id);
    if (["done", "failed", "cancelled"].includes(fresh.status)) await this.finish();
  }

  async show(runId) {
    this.close();
    const run = await api.run(runId);
    this.charts.load(run);
    log.innerHTML = "";
    run.events.forEach((ev) => this.appendEvent(ev));
    this.setOutcomesTitle(run.scenario);
    this.setStatusFor(run);
    showResults(run);
  }

  async finish() {
    const id = this.runId;
    if (!id) return;  // ya se cerró (evita procesar el final dos veces)
    this.runId = null;
    this.close();
    const run = await api.run(id);
    this.setStatusFor(run);
    showResults(run);
    this.onFinished(run);
  }

  close() {
    if (this.source) this.source.close();
    this.source = null;
  }

  setStatusFor(run) {
    const name = SCENARIO_NAMES[run.scenario];
    const text = {
      done: `${name}: terminada`,
      cancelled: `${name}: detenida antes de terminar`,
      failed: `${name}: falló — ${run.error || "error desconocido"}`,
      running: `${name} en curso…`,
    }[run.status] || name;
    this.setStatus(run.status, text);
  }

  setStatus(state, text) {
    statusEl.dataset.state = state;
    statusEl.textContent = text;
  }

  setOutcomesTitle(scenario) {
    outcomesTitle.textContent = scenario === "failover"
      ? "Compras completadas por segundo: las líneas punteadas marcan la caída y la reparación"
      : "Compras completadas y fallas técnicas por segundo";
  }

  appendEvent(ev) {
    const li = document.createElement("li");
    li.dataset.kind = ev.kind;
    const when = ev.t != null ? ` (t = ${ev.t} s)` : "";
    li.innerHTML = `<span class="tag" data-system="${ev.system || ""}">${ev.system || ""}</span><span>${escapeHtml(ev.message)}${when}</span>`;
    log.append(li);
    log.scrollTop = log.scrollHeight;
  }
}
