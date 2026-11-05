"""Regenerate the editable SVG charts with the project calculator."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stereo_audit import audit, depth_and_bounds, read_samples

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INK, MUTED, GRID = "#102f3c", "#365867", "#c8dadd"
TEAL, RUST = "#117777", "#a6492a"


def label(x, y, value, size=27, color=INK, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}">{value}</text>')


def line(x1, y1, x2, y2, color, width=2):
    return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" stroke-width="{width}"/>'


def box(x, y, width, height, color, radius=0):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{color}"/>'


def write(name, title, desc, height, parts):
    (HERE / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="840" height="{height}" viewBox="0 0 840 {height}" role="img">'
        f'<title>{title}</title><desc>{desc}</desc><g font-family="DejaVu Sans,sans-serif">'
        + box(0, 0, 840, height, "#eff7f7", 22) + "\n".join(parts) + "</g></svg>\n",
        encoding="utf-8",
    )


def intervals():
    x = lambda value: 420 + value * 1.47
    parts = [label(44, 62, "Same pixel error, different depth", 38, weight=700),
             label(44, 108, "Disparity bound: ±0.25 px", 29, MUTED)]
    for value in (-200, -100, 0, 100, 200):
        p = x(value)
        parts.extend([line(p, 146, p, 420, GRID, 3 if value == 0 else 2),
                      label(p, 463, f"{value}", 27, MUTED, anchor="middle")])
    for disparity, y, color in [(36, 244, TEAL), (10, 372, RUST)]:
        depth, (near, far) = depth_and_bounds(900, .08, disparity, .25)
        lo, hi = 1000 * (near - depth), 1000 * (far - depth)
        parts.extend([label(44, y - 48, f"{depth:.1f} m depth   ·   {disparity} px", 30, weight=700),
                      line(x(lo), y, x(hi), y, color, 10),
                      line(x(lo), y-12, x(lo), y+12, color, 4),
                      line(x(hi), y-12, x(hi), y+12, color, 4),
                      f'<circle cx="420" cy="{y}" r="5" fill="{INK}"/>',
                      label(44, y + 42, f"{lo:+.0f} to {hi:+.0f} mm", 28, color, 700)])
    parts.append(label(420, 510, "Depth offset from nominal (mm)", 29, anchor="middle"))
    write("stereo-depth-error-intervals", "Exact disparity error intervals",
          "The 7.2 metre case has a much wider and more asymmetric interval than the 2 metre case.", 552, parts)


def coverage():
    groups = audit(read_samples(ROOT / "examples/mixed.csv"), 900, .08, .25)
    parts = [label(44, 63, "Keep the missing samples", 41, weight=700),
             label(44, 110, "Synthetic CSV audit at 1 to 2 m", 28, MUTED)]
    for name, y in [("textured", 174), ("glossy", 346)]:
        group = groups[name]
        valid, total = len(group["errors"]), group["total"]
        worst = max(map(abs, group["errors"]))
        parts.append(label(44, y, name.capitalize(), 36, weight=700))
        for i in range(total):
            parts.append(box(44 + i*114, y+20, 96, 33, TEAL if i < valid else GRID, 8))
        parts.extend([label(416, y+48, f"{valid}/{total} valid", 33, TEAL if valid == total else RUST, 700),
                      label(44, y+104, f"Worst valid error: {worst:.0f} mm", 30, MUTED)])
    write("stereo-depth-coverage-audit", "Valid returns and worst error",
          "Three of three textured samples return depth; only one of three glossy samples does.", 500, parts)


if __name__ == "__main__":
    intervals()
    coverage()
