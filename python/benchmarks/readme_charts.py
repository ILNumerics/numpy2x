"""Draws the README's charts as small SVG files (light and dark theme).

Usage:
    python python/benchmarks/readme_charts.py [--results DIR]

Reads the results of readme_examples.py (examples.json, toy/shape_map.json)
and writes docs/images/loop.svg, kmeans.svg and toy_shape_map.svg. Prints the
numbers the README quotes.
"""

import argparse
import json
import math
import os
import statistics

STYLE = """<style>
  .bg{fill:none}
  .t{font:600 13px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:#0b0b0b}
  .l{font:12px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:#52514e}
  .v{font:600 12px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:#0b0b0b}
  .c{font:11px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}
  .grid{stroke:#e1e0d9;stroke-width:1}
  .base{stroke:#c3c2b7;stroke-width:1}
  .np{fill:#b9b8ae}
  .nx{fill:#2a78d6}
  .k0{fill:#c93b3b}.k1{fill:#e98a86}.k2{fill:#f4c6c2}.k3{fill:#f0efec}
  .k4{fill:#cde2fb}.k5{fill:#86b6ef}.k6{fill:#2a78d6}
  .dk{fill:#0b0b0b}.lt{fill:#ffffff}
  @media (prefers-color-scheme: dark){
    .t,.v{fill:#f0efec}.l{fill:#c3c2b7}
    .grid{stroke:#2c2c2a}.base{stroke:#383835}
    .np{fill:#6b6a63}.nx{fill:#3987e5}
    .k0{fill:#b83232}.k1{fill:#8f3b38}.k2{fill:#5a3331}.k3{fill:#383835}
    .k4{fill:#1f3a5c}.k5{fill:#25558f}.k6{fill:#3987e5}
    .dk{fill:#f0efec}
  }
</style>"""


def svg(width, height, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img">\n{STYLE}\n{body}\n</svg>\n')


def bar_path(x, y0, w, h, r=4):
    """A bar from the baseline y0 up by h, rounded at the data end only."""
    r = min(r, w / 2, h)
    top = y0 - h
    return (f'<path d="M{x:.1f},{y0:.1f} V{top + r:.1f} Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f} '
            f'H{x + w - r:.1f} Q{x + w:.1f},{top:.1f} {x + w:.1f},{top + r:.1f} V{y0:.1f} Z"')


def bars(spec):
    """Grouped bars per size: NumPy (1x) and numpy2x, with the numpy2x value labeled."""
    labels, values = spec["labels"], spec["values"]
    group_w, bar_w, gap = 62, 22, 2
    left, top, bottom = 34, 52, 26
    plot_h = 120
    width = max(left + group_w * len(labels) + 12, 140)
    height = top + plot_h + bottom
    vmax = max(2.5, math.ceil((max(values) + 0.3) * 2) / 2)  # room for the labels
    y = lambda v: top + plot_h - v / vmax * plot_h
    out = [f'<text class="t" x="0" y="16">{spec["title"]}</text>',
           f'<rect class="np" x="0" y="28" width="10" height="10" rx="2"/>'
           f'<text class="l" x="14" y="37">NumPy</text>',
           f'<rect class="nx" x="66" y="28" width="10" height="10" rx="2"/>'
           f'<text class="l" x="80" y="37">numpy2x</text>']
    t = 0.0
    while t <= vmax + 1e-9:
        out.append(f'<line class="grid" x1="{left}" x2="{width - 4}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                   f'<text class="l" x="{left - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{t:g}x</text>')
        t += 1.0
    for i, (lab, v) in enumerate(zip(labels, values)):
        x0 = left + 8 + i * group_w
        out.append(bar_path(x0, y(0), bar_w, y(0) - y(1.0)) + ' class="np"><title>NumPy: 1x</title></path>')
        x1 = x0 + bar_w + gap
        out.append(bar_path(x1, y(0), bar_w, y(0) - y(v)) +
                   f' class="nx"><title>numpy2x: {v:.2f}x</title></path>')
        out.append(f'<text class="v" x="{x1 + bar_w / 2:.1f}" y="{y(max(v, 1.0)) - 5:.1f}" '
                   f'text-anchor="middle">{(f"{v:.2f}" if v < 1 else f"{v:.1f}")}x</text>')
        out.append(f'<text class="l" x="{x0 + bar_w + gap / 2:.1f}" y="{top + plot_h + 17}" '
                   f'text-anchor="middle">{lab}</text>')
    out.append(f'<line class="base" x1="{left}" x2="{width - 4}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>')
    return svg(width, height, "\n".join(out))


BINS = [(0.5, "k0", "lt"), (0.8, "k1", "dk"), (0.95, "k2", "dk"), (1.05, "k3", "dk"),
        (1.25, "k4", "dk"), (2.0, "k5", "dk"), (float("inf"), "k6", "lt")]


def heatmap(run, title):
    """Median speedup per (rows, cols) point: blue faster, red slower, gray even."""
    by_shape = {}
    for res in run["results"]:
        if len(res["shape"]) == 2 and res.get("speedup"):
            by_shape.setdefault(tuple(res["shape"]), []).append(res["speedup"])
    pts = {k: statistics.median(v) for k, v in by_shape.items()}
    rows = sorted({r for r, _ in pts})
    cols = sorted({c for _, c in pts})
    cell, left, top = 44, 52, 40
    width = max(left + cell * len(cols) + 8, 7 * len(title) + 8)  # room for the title
    height = top + cell * len(rows) + 64
    out = [f'<text class="t" x="0" y="16">{title}</text>']
    for j, c in enumerate(cols):
        out.append(f'<text class="l" x="{left + j * cell + cell / 2}" y="{top - 6}" '
                   f'text-anchor="middle">{c:,}</text>')
    for i, r in enumerate(rows):
        yy = top + i * cell
        out.append(f'<text class="l" x="{left - 6}" y="{yy + cell / 2 + 4}" text-anchor="end">{r:,}</text>')
        for j, c in enumerate(cols):
            v = pts.get((r, c))
            if v is None:
                continue
            fill, ink = next((f, k) for b, f, k in BINS if v < b)
            xx = left + j * cell
            out.append(f'<rect class="{fill}" x="{xx + 1}" y="{yy + 1}" width="{cell - 2}" '
                       f'height="{cell - 2}" rx="3"><title>{r:,} x {c:,}: {v:.2f}x</title></rect>'
                       f'<text class="c {ink}" x="{xx + cell / 2}" y="{yy + cell / 2 + 4}" '
                       f'text-anchor="middle">{v:.2f}</text>')
    yb = top + cell * len(rows)
    out.append(f'<text class="l" x="0" y="{top - 6}">rows\\cols</text>')
    out.append(f'<text class="l" x="0" y="{yb + 22}">speedup vs. NumPy:</text>')
    labs = ["&lt;0.5", "0.5–0.8", "0.8–0.95", "0.95–1.05", "1.05–1.25", "1.25–2", "≥2"]
    lx, ly = 0, yb + 34
    used = {next(i for i, (b, _, _) in enumerate(BINS) if v < b) for v in pts.values()}
    for i, ((b, f, _), lab) in enumerate(zip(BINS, labs)):
        if i not in used:  # only the bins the map shows
            continue
        w = 16 + 7 * len(lab.replace("&lt;", "<")) + 12
        if lx + w > width:
            lx, ly = 0, ly + 18
        out.append(f'<rect class="{f}" x="{lx}" y="{ly}" width="12" height="12" rx="2"/>'
                   f'<text class="l" x="{lx + 16}" y="{ly + 10}">{lab}</text>')
        lx += w
    return svg(width, ly + 20, "\n".join(out))


def size_label(n):
    return f"{n}\u00b2"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--results", default=os.path.join(here, "results", "readme"),
                   help="readme_examples.py's output")
    p.add_argument("--out", default=os.path.join(here, "..", "..", "docs", "images"))
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)
    res = json.load(open(os.path.join(args.results, "examples.json"), encoding="utf-8"))
    ex = res["examples"]
    m = res["machine"]
    print(f"machine: {m.get('cpu')}, {m.get('cores')} cores, {m.get('os')}, Python "
          f"{m.get('python')}, NumPy {m.get('numpy')}, {m.get('workers')} workers")
    for name, rows in ex.items():
        for r in rows:
            print(f"  {r['name']:26s} NumPy {r['numpy_s'] * 1e3:8.1f} ms  numpy2x "
                  f"{r['numpy2x_s'] * 1e3:8.1f} ms  {r['speedup']:.2f}x  identical {r['identical']}")
    bars_spec = {
        "loop": {"title": "Speedup vs. NumPy", "labels": [size_label(1500)],
                 "values": [ex["loop"][0]["speedup"]]},
        "kmeans": {"title": "k-means, speedup vs. NumPy",
                   "labels": [size_label(r["size"]) for r in ex["kmeans"]],
                   "values": [r["speedup"] for r in ex["kmeans"]]},
    }
    for name, spec in bars_spec.items():
        with open(os.path.join(args.out, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(bars(spec))
    toy = os.path.join(args.results, "toy", "shape_map.json")
    if os.path.exists(toy):
        run = json.load(open(toy, encoding="utf-8"))
        n = len({r["case"] for r in run["results"]})
        with open(os.path.join(args.out, "toy_shape_map.svg"), "w", encoding="utf-8") as f:
            f.write(heatmap(run, f"Toy examples: one op, no AILP (median of {n} toy programs)"))
        ok = sum(r["identical"] for r in run["results"])
        print(f"  toy shape map: {ok} / {len(run['results'])} bit-identical")
    print(f"written: {os.path.normpath(args.out)}")


if __name__ == "__main__":
    main()
