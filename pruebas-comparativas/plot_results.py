"""Genera las gráficas comparativas (PNG) y un resumen en Markdown.

Lee resultados/ (CSV de Locust, flash_sale_*.json, failover_*.csv,
consistencia_*.json) y escribe graficas/*.png y resultados/resumen.md.

Uso:  python plot_results.py
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
RES, OUT = HERE / "resultados", HERE / "graficas"

COLOR = {"A": "#eb6834", "B": "#2a78d6"}  # categórico fijo: A naranja, B azul
LABEL = {"A": "A · PostgreSQL único", "B": "B · MongoDB sharded + Redis"}
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 13, "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2,
    "ytick.color": INK_2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.titleweight": "bold", "axes.titlesize": 16, "axes.titlecolor": INK, "axes.titlelocation": "left",
})


def locust_levels(system: str) -> dict[int, dict[str, dict]]:
    levels = {}
    for f in sorted(RES.glob(f"{system}_*_stats.csv")):
        users = int(f.stem.split("_")[1])
        levels[users] = {r["Name"]: r for r in csv.DictReader(f.open())}
    return dict(sorted(levels.items()))


def save(fig, name: str) -> None:
    OUT.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("  ->", OUT / name)


def end_label(ax, x, y, text, color) -> None:
    ax.annotate(text, (x, y), xytext=(8, 0), textcoords="offset points", va="center", color=INK, fontsize=12,
                bbox={"boxstyle": "round,pad=0.2", "fc": SURFACE, "ec": color, "lw": 1.2})


def line_chart(data: dict[str, dict[int, float]], title: str, ylabel: str, name: str, fmt="{:.0f}") -> None:
    fig, ax = plt.subplots(figsize=(10, 5.6))
    for s, series in data.items():
        xs, ys = list(series), list(series.values())
        ax.plot(xs, ys, color=COLOR[s], lw=2.5, marker="o", ms=9, mec=SURFACE, mew=2, label=LABEL[s])
        end_label(ax, xs[-1], ys[-1], fmt.format(ys[-1]), COLOR[s])
    ax.set_title(title)
    ax.set_xlabel("Usuarios concurrentes")
    ax.set_ylabel(ylabel)
    ax.set_xticks(list(next(iter(data.values()))))
    ax.set_ylim(bottom=0)
    ax.margins(x=0.12)
    ax.legend(frameon=False, loc="upper left")
    save(fig, name)


def grouped_bars(cats: list, data: dict[str, list[float]], title: str, xlabel: str, ylabel: str, name: str, fmt="{:.0f}") -> None:
    fig, ax = plt.subplots(figsize=(10, 5.6))
    width = 0.36
    for i, (s, vals) in enumerate(data.items()):
        xs = [k + (i - 0.5) * (width + 0.02) for k in range(len(cats))]
        bars = ax.bar(xs, vals, width, color=COLOR[s], label=LABEL[s], edgecolor=SURFACE, linewidth=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), fmt.format(v), ha="center", va="bottom",
                    fontsize=12, color=INK, fontweight="bold")
    ax.set_xticks(range(len(cats)), [str(c) for c in cats])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, max(max(v) for v in data.values()) * 1.3)  # aire para la leyenda
    ax.legend(frameon=False, loc="upper center", ncol=2)
    save(fig, name)


def main() -> None:
    summary = ["# Resumen de resultados\n"]

    # ---- 1. Carga general (Locust) ----
    a, b = locust_levels("A"), locust_levels("B")
    if a and b:
        agg = lambda lv, col: {u: float(r["Aggregated"][col]) for u, r in lv.items()}  # noqa: E731
        line_chart({"A": agg(a, "Requests/s"), "B": agg(b, "Requests/s")},
                   "Peticiones atendidas por segundo (más es mejor)", "req/s", "01_throughput.png")
        line_chart({"A": agg(a, "95%"), "B": agg(b, "95%")},
                   "Latencia p95 de todas las peticiones (menos es mejor)", "milisegundos", "02_latencia_p95.png",
                   fmt="{:.0f} ms")
        users = list(a)
        grouped_bars(users, {s: [float(lv[u]["POST /orders/checkout"]["95%"]) for u in users] for s, lv in (("A", a), ("B", b))},
                     "Latencia p95 del checkout (menos es mejor)", "Usuarios concurrentes", "milisegundos",
                     "03_checkout_p95.png")
        summary.append("## Carga general (Black Friday, 80 % del tráfico en 20 productos)\n")
        summary.append("| Usuarios | Sistema | req/s | p50 (ms) | p95 (ms) | p95 checkout (ms) | Fallas |")
        summary.append("|---|---|---|---|---|---|---|")
        for u in users:
            for s, lv in (("A", a), ("B", b)):
                r, c = lv[u]["Aggregated"], lv[u]["POST /orders/checkout"]
                summary.append(f"| {u} | {s} | {float(r['Requests/s']):.0f} | {r['50%']} | {r['95%']} | {c['95%']} | {r['Failure Count']} |")
        summary.append("")

    # ---- 2. Venta relámpago ----
    fs = {s: json.loads((RES / f"flash_sale_{s}.json").read_text())["rounds"] for s in "AB"
          if (RES / f"flash_sale_{s}.json").exists()}
    if len(fs) == 2:
        buyers = [r["buyers"] for r in fs["A"]]
        grouped_bars(buyers, {s: [r["checkouts_per_s"] for r in fs[s]] for s in "AB"},
                     "Venta relámpago: compras completadas por segundo", "Compradores simultáneos del mismo producto",
                     "compras / s", "04_flash_sale_throughput.png")
        grouped_bars(buyers, {s: [r["wall_time_s"] for r in fs[s]] for s in "AB"},
                     "Venta relámpago: tiempo hasta atender a todos", "Compradores simultáneos del mismo producto",
                     "segundos", "05_flash_sale_tiempo.png", fmt="{:.1f} s")
        summary.append("## Venta relámpago (todos compran el producto P00001 a la vez)\n")
        summary.append("| Compradores | Sistema | Compras OK | Errores 5xx | Tiempo total (s) | Compras/s | p95 (ms) |")
        summary.append("|---|---|---|---|---|---|---|")
        for i, n in enumerate(buyers):
            for s in "AB":
                r = fs[s][i]
                summary.append(f"| {n} | {s} | {r['orders_ok']} | {r['errors_5xx']} | {r['wall_time_s']} | {r['checkouts_per_s']} | {r['latency_p95_ms']} |")
        summary.append("")

    # ---- 3. Caída de un nodo ----
    fo = {}
    for s in "AB":
        f = RES / f"failover_{s}.csv"
        if f.exists():
            fo[s] = list(csv.DictReader(f.open()))
    if len(fo) == 2:
        fig, ax = plt.subplots(figsize=(11, 5.6))
        for s, rows in fo.items():
            xs = [int(r["second"]) for r in rows]
            ys = [int(r["ok"]) for r in rows]
            ax.plot(xs, ys, color=COLOR[s], lw=2.5, label=LABEL[s])
        kill = next(int(r["second"]) for r in fo["A"] if r["event"] == "kill")
        restore = next((int(r["second"]) for r in fo["A"] if r["event"] == "restore"), None)
        ax.axvline(kill, color=INK_2, lw=1.2, ls="--")
        ax.text(kill + 0.5, ax.get_ylim()[1] * 0.95, "se cae un nodo de BD", color=INK, fontsize=12, va="top")
        if restore:
            ax.axvline(restore, color=INK_2, lw=1.2, ls=":")
            ax.text(restore + 0.5, ax.get_ylim()[1] * 0.95, "reparación manual", color=INK, fontsize=12, va="top")
        ax.set_title("Compras exitosas por segundo durante una falla")
        ax.set_xlabel("Segundos")
        ax.set_ylabel("compras OK / s")
        ax.set_ylim(bottom=0)
        ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
        save(fig, "06_failover.png")

        summary.append("## Caída de un nodo de base de datos\n")
        summary.append("| Sistema | Nodo apagado | Segundos sin vender | Compras OK | Compras fallidas |")
        summary.append("|---|---|---|---|---|")
        node = {"A": "PostgreSQL (único servidor)", "B": "primario del shard NORTE"}
        for s, rows in fo.items():
            window = [r for r in rows if kill <= int(r["second"]) < (restore or 10**9)]
            summary.append(f"| {s} | {node[s]} | {sum(1 for r in window if int(r['ok']) == 0)} | "
                           f"{sum(int(r['ok']) for r in rows)} | {sum(int(r['fail']) for r in rows)} |")
        summary.append("")

    # ---- 4. Consistencia ----
    cons = sorted(RES.glob("consistencia_*.json"))
    if cons:
        summary.append("## Consistencia (¿se vendió más de lo que había?)\n")
        summary.append("| Prueba | Pedidos | Unidades vendidas | Stock negativo | Violaciones | Redis vs Mongo | Consistente |")
        summary.append("|---|---|---|---|---|---|---|")
        for f in cons:
            r = json.loads(f.read_text())
            summary.append(f"| {f.stem} | {r['orders']} | {r['units_sold']} | {r['negative_stock_products']} | "
                           f"{r['invariant_violations']} | {r['redis_vs_mongo_diffs'] if r['redis_vs_mongo_diffs'] is not None else '—'} | "
                           f"{'sí' if r['consistent'] else 'NO'} |")

    (RES / "resumen.md").write_text("\n".join(summary) + "\n")
    print("  ->", RES / "resumen.md")


if __name__ == "__main__":
    main()
