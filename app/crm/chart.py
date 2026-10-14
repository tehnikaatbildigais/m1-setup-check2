"""F7 · servera pusē ģenerēta horizontālu stabiņu diagramma (SVG, bez JavaScript).

Krāsa nāk no CSS mainīgā `--chart-bar` (pārbaudīta ar dataviz validatoru gaišajam un
tumšajam režīmam). Vērtības ir arī tabulā zem diagrammas.
"""

from __future__ import annotations

import math
from html import escape

LABEL_WIDTH = 170
PLOT_WIDTH = 300
RIGHT_PAD = 16
ROW = 26
BAR = 20
TOP = 8
AXIS = 28
RADIUS = 4


def _nice_max(value: int) -> int:
    if value <= 5:
        return max(value, 1)
    magnitude = 10 ** int(math.log10(value))
    for step in (1, 2, 5, 10):
        if value <= step * magnitude:
            return step * magnitude
    return value


def _bar_path(x: float, y: float, width: float, height: float) -> str:
    """Stabiņš ar noapaļotu galu tikai datu pusē (bāze paliek taisna)."""
    r = min(RADIUS, width / 2)
    return (
        f"M{x:.1f},{y:.1f} H{x + width - r:.1f} "
        f"Q{x + width:.1f},{y:.1f} {x + width:.1f},{y + r:.1f} "
        f"V{y + height - r:.1f} "
        f"Q{x + width:.1f},{y + height:.1f} {x + width - r:.1f},{y + height:.1f} "
        f"H{x:.1f} Z"
    )


def bar_chart(rows: list[tuple[str, int]], title: str, description: str) -> str:
    """`rows`: (nosaukums, vērtība), jau sakārtoti. Atgriež SVG kā drošu HTML virkni."""
    top_value = _nice_max(max((v for _, v in rows), default=0))
    height = TOP + ROW * len(rows) + AXIS
    width = LABEL_WIDTH + PLOT_WIDTH + RIGHT_PAD
    x0 = LABEL_WIDTH
    scale = PLOT_WIDTH / top_value

    ticks = sorted({0, top_value // 2, top_value}) if top_value > 1 else [0, top_value]
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" width="{width}" height="{height}"'
        ' role="img" aria-labelledby="chart-title chart-desc">',
        f'<title id="chart-title">{escape(title)}</title>',
        f'<desc id="chart-desc">{escape(description)}</desc>',
    ]
    plot_bottom = TOP + ROW * len(rows)
    for tick in ticks:
        x = x0 + tick * scale
        parts.append(
            f'<line class="chart-grid" x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{plot_bottom}"/>'
        )
        parts.append(
            f'<text class="chart-tick" x="{x:.1f}" y="{plot_bottom + 18}"'
            f' text-anchor="middle">{tick}</text>'
        )
    for index, (label, value) in enumerate(rows):
        y = TOP + index * ROW + (ROW - BAR) / 2
        parts.append(
            f'<text class="chart-label" x="{x0 - 8}" y="{y + BAR / 2:.1f}"'
            f' text-anchor="end" dominant-baseline="central">{escape(label)}</text>'
        )
        if value:
            parts.append(
                f'<path class="chart-bar" d="{_bar_path(x0, y, value * scale, BAR)}">'
                f"<title>{escape(label)}: {value}</title></path>"
            )
    parts.append(
        f'<line class="chart-axis" x1="{x0}" y1="{TOP}" x2="{x0}" y2="{plot_bottom}"/>'
    )
    parts.append("</svg>")
    return "".join(parts)
