// Panel de preparación: elegir escenario, ajustar parámetros y sistemas.
import { api } from "../api.js";
import { escapeHtml } from "../format.js";

const picker = document.getElementById("scenario-picker");
const form = document.getElementById("params-form");

let scenarios = [];
let selected = null;

export async function initSetup() {
  scenarios = await api.scenarios();
  picker.insertAdjacentHTML("beforeend", scenarios.map((s) => `
    <button type="button" class="scenario" role="radio" aria-checked="false" data-key="${s.key}"
      ${Object.values(s.available).some(Boolean) ? "" : "data-disabled"}>
      <strong>${escapeHtml(s.title)}</strong>
      <span>${escapeHtml(s.summary)}</span>
    </button>`).join(""));
  picker.addEventListener("click", (e) => {
    const btn = e.target.closest(".scenario");
    if (btn) select(btn.dataset.key);
  });
  form.addEventListener("input", syncPair);
  select(scenarios[0].key);
}

function select(key) {
  selected = scenarios.find((s) => s.key === key);
  picker.querySelectorAll(".scenario").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.key === key)));
  form.innerHTML = selected.params.map(paramField).join("");
}

function paramField(p) {
  if (p.kind === "bool") {
    return `<label class="param-check"><input type="checkbox" name="${p.name}" ${p.default ? "checked" : ""}> ${escapeHtml(p.label)}</label>`;
  }
  const step = p.kind === "float" ? "0.1" : "1";
  return `<label class="param">
      <span>${escapeHtml(p.label)}</span>
      <span class="param-row">
        <input type="range" data-pair="${p.name}" min="${p.min}" max="${p.max}" step="${step}" value="${p.default}" aria-hidden="true" tabindex="-1">
        <input type="number" name="${p.name}" min="${p.min}" max="${p.max}" step="${step}" value="${p.default}">
      </span>
      ${p.help ? `<small>${escapeHtml(p.help)}</small>` : ""}
    </label>`;
}

// El deslizador y la caja numérica siempre muestran el mismo valor.
function syncPair(e) {
  const el = e.target;
  if (el.dataset.pair) form.elements[el.dataset.pair].value = el.value;
  else if (el.type === "number") {
    const range = form.querySelector(`[data-pair="${el.name}"]`);
    if (range) range.value = el.value;
  }
}

export function readSetup() {
  const params = {};
  selected.params.forEach((p) => {
    const field = form.elements[p.name];
    params[p.name] = p.kind === "bool" ? field.checked : Number(field.value);
  });
  const systems = [...document.querySelectorAll('input[name="system"]:checked')].map((i) => i.value);
  return { scenario: selected.key, systems, params };
}

export function setRunning(running) {
  document.getElementById("start").disabled = running;
  document.getElementById("cancel").hidden = !running;
  form.querySelectorAll("input").forEach((i) => { i.disabled = running; });
}
