// Arranque del panel del simulador.
import { api } from "./api.js";
import { LiveCharts } from "./charts.js";
import { initHistory, refreshHistory } from "./views/history.js";
import { LiveView } from "./views/live.js";
import { initSetup, readSetup, setRunning } from "./views/setup.js";
import { initTargets, refreshTargets } from "./views/targets.js";

const errorEl = document.getElementById("form-error");
const charts = new LiveCharts();
let currentRunId = null;

const live = new LiveView(charts, {
  onFinished: () => {
    setRunning(false);
    currentRunId = null;
    refreshHistory();
    refreshTargets();
  },
});

async function start() {
  errorEl.textContent = "";
  try {
    const run = await api.startRun(readSetup());
    currentRunId = run.id;
    setRunning(true);
    await live.follow(run);
  } catch (error) {
    errorEl.textContent = error.message;
  }
}

async function cancel() {
  if (!currentRunId) return;
  try {
    await api.cancelRun(currentRunId);
  } catch (error) {
    errorEl.textContent = error.message;
  }
}

async function main() {
  document.getElementById("start").addEventListener("click", start);
  document.getElementById("cancel").addEventListener("click", cancel);
  initTargets();
  initHistory((id) => { if (!currentRunId) live.show(id); });
  await initSetup();

  // Si hay una corrida activa (por ejemplo, se recargó la página), seguirla.
  const { active } = await api.runs();
  if (active) {
    currentRunId = active;
    setRunning(true);
    await live.follow(await api.run(active));
  }
}

main();
