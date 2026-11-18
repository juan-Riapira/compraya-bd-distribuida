// Estado compartido de la interfaz (cliente actual y carrito) con suscriptores.

const listeners = new Set();

export const state = {
  userId: localStorageGet("compraya:user") || "U00001",
  user: null,
  cart: { items: [], total: 0 },
};

export function setState(patch) {
  Object.assign(state, patch);
  if (patch.userId) localStorageSet("compraya:user", patch.userId);
  listeners.forEach((fn) => fn(state));
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function localStorageGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

function localStorageSet(key, value) {
  try { localStorage.setItem(key, value); } catch { /* almacenamiento no disponible */ }
}
