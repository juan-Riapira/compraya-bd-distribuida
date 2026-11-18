// Gráficas en vivo (Chart.js): A y B superpuestos sobre el mismo eje de segundos.
/* global Chart */

const COLORS = { A: "#eb6834", B: "#2a78d6" };
const INK_2 = "#4d5562";
const GRID = "#e6e9ee";

// Dibuja líneas verticales para "se cayó el nodo" y "se reparó".
const markerPlugin = {
  id: "markers",
  afterDatasetsDraw(chart) {
    const markers = chart.$markers || [];
    const { ctx, chartArea, scales } = chart;
    markers.forEach((m) => {
      const x = scales.x.getPixelForValue(m.t);
      if (x < chartArea.left || x > chartArea.right) return;
      ctx.save();
      ctx.strokeStyle = COLORS[m.system];
      ctx.setLineDash(m.kind === "kill" ? [6, 4] : [2, 3]);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
      ctx.fillStyle = COLORS[m.system];
      ctx.font = "600 11px system-ui, sans-serif";
      ctx.fillText(m.kind === "kill" ? `${m.system}: cae` : `${m.system}: repara`, x + 4, chartArea.top + 12 + (m.system === "B" ? 14 : 0));
      ctx.restore();
    });
  },
};

function baseOptions(yTitle) {
  return {
    animation: false,
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    parsing: false,
    scales: {
      x: { type: "linear", min: 0, title: { display: true, text: "segundos", color: INK_2 }, grid: { color: GRID }, ticks: { color: INK_2 } },
      y: { beginAtZero: true, title: { display: true, text: yTitle, color: INK_2 }, grid: { color: GRID }, ticks: { color: INK_2 } },
    },
    plugins: {
      legend: { position: "top", align: "end", labels: { boxWidth: 26, color: INK_2, usePointStyle: true } },
      tooltip: { callbacks: { title: (items) => `t = ${items[0].parsed.x} s` } },
    },
    elements: { point: { radius: 0, hitRadius: 8, hoverRadius: 4 }, line: { borderWidth: 2, tension: 0.25 } },
  };
}

function series(label, system, dashed = false) {
  return {
    label, data: [], system, pointStyle: "line",
    borderColor: COLORS[system], backgroundColor: COLORS[system], borderDash: dashed ? [5, 4] : [],
  };
}

export class LiveCharts {
  constructor() {
    this.throughput = new Chart(document.getElementById("chart-throughput"), {
      type: "line", plugins: [markerPlugin], options: baseOptions("peticiones / s"),
      data: { datasets: [series("A · PostgreSQL", "A"), series("B · Distribuido", "B")] },
    });
    this.latency = new Chart(document.getElementById("chart-latency"), {
      type: "line", plugins: [markerPlugin], options: baseOptions("milisegundos"),
      data: { datasets: [series("A · p95", "A"), series("B · p95", "B")] },
    });
    this.outcomes = new Chart(document.getElementById("chart-outcomes"), {
      type: "line", plugins: [markerPlugin], options: baseOptions("por segundo"),
      data: {
        datasets: [
          series("A · compras OK", "A"), series("B · compras OK", "B"),
          series("A · fallas técnicas", "A", true), series("B · fallas técnicas", "B", true),
        ],
      },
    });
    this.all = [this.throughput, this.latency, this.outcomes];
    this.markers = [];
    this.all.forEach((c) => { c.$markers = this.markers; });
  }

  reset() {
    this.markers.length = 0;
    this.all.forEach((c) => {
      c.data.datasets.forEach((d) => { d.data = []; });
      c.update();
    });
  }

  addTick(tick) {
    const i = tick.system === "A" ? 0 : 1;
    this.throughput.data.datasets[i].data.push({ x: tick.t, y: tick.rps });
    this.latency.data.datasets[i].data.push({ x: tick.t, y: tick.p95 });
    this.outcomes.data.datasets[i].data.push({ x: tick.t, y: tick.checkouts });
    this.outcomes.data.datasets[i + 2].data.push({ x: tick.t, y: tick.failures });
    this._scheduleUpdate();
  }

  addMarker(event) {
    if (!["kill", "restore"].includes(event.kind) || event.t == null) return;
    this.markers.push({ t: event.t, kind: event.kind, system: event.system });
    this._scheduleUpdate();
  }

  load(run) {
    this.reset();
    Object.values(run.results).forEach((r) => r.timeline.forEach((t) => this.addTick({ ...t, system: r.system })));
    run.events.forEach((e) => this.addMarker(e));
  }

  _scheduleUpdate() {
    if (this._pending) return;
    this._pending = requestAnimationFrame(() => {
      this._pending = null;
      this.all.forEach((c) => c.update("none"));
    });
  }
}
