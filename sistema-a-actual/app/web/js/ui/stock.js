// Medidor de existencias que se muestra en cada producto.

const STOCK_SCALE = 500;  // tope del dataset: sirve de escala para el medidor

export function stockMarkup(stock) {
  const level = stock === 0 ? "out" : stock <= 20 ? "low" : "ok";
  const pct = Math.min(100, (stock / STOCK_SCALE) * 100);
  const text = stock === 0 ? "Agotado" : `Quedan ${stock} unidades`;
  return `<div class="stock" data-level="${level}">
      <span>${text}</span>
      <div class="stock-meter" aria-hidden="true"><span style="width:${pct}%"></span></div>
    </div>`;
}
