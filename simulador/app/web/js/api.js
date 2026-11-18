// Cliente de la API del simulador (única capa que conoce sus rutas).

async function request(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || `Error ${response.status}`);
  return data;
}

export const api = {
  scenarios: () => request("GET", "/api/scenarios"),
  targets: () => request("GET", "/api/targets"),
  resetTarget: (system) => request("POST", `/api/targets/${system}/reset`),
  startRun: (payload) => request("POST", "/api/runs", payload),
  cancelRun: (id) => request("POST", `/api/runs/${id}/cancel`),
  run: (id) => request("GET", `/api/runs/${id}`),
  runs: () => request("GET", "/api/runs"),
  deleteRun: (id) => request("DELETE", `/api/runs/${id}`),
  stream: (id) => new EventSource(`/api/runs/${id}/stream`),
};
