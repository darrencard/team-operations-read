"""svgkit: the SVG primitives every Landing Loop page draws with, in one visual family.

The family (design spec, 2026-11-27): inline SVG only, no images, no libraries. 1.5px strokes, 4px corners on
blocks, labels in the mono face at 11px, upper case, tracked 0.06em, values in the page's sans. No shadows, no
gradients. Every colour is one of the Leader Report template's CSS variables, so the page's stylesheet themes
every mark: --t1 ink, --t2, --t3 muted, --line, --line2, --line3, --bg, --brass, --agent, --landed, --watch,
--stalled. The Illustrative blue is the one colour the template lacks; CSS below adds it as --ill.

Meaning is fixed: brass is a person's call, grey with a spark is agent work, and the two never mix. Green and
red appear only inside status_word(), beside the printed word landed or stalled. Target lines are ink, dashed
4 3. Hatching marks "over" or "can't see".

A visual draws only figures its page already prints, and states its answer in its aria-label. numbers_in()
lists the figures an SVG prints, so a page's tests can check them against the page's text.

Output is deterministic: every coordinate goes through num(), which prints at most two decimals with no
trailing zeros, so the same inputs give the same bytes.

Vendor this file byte-identical, pinned by landing-loop commit and sha256 (tools/SVGKIT.md).
Standard library only. Python 3.11 or later.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Iterable, Sequence

VERSION = "1.0.0"

INK = "var(--t1)"
INK2 = "var(--t2)"
MUTED = "var(--t3)"
LINE = "var(--line)"
LINE2 = "var(--line2)"
LINE3 = "var(--line3)"
BG = "var(--bg)"
BRASS = "var(--brass)"
AGENT = "var(--agent)"
ILLUSTRATIVE = "var(--ill)"
STATUS_TONES = {"landed": "var(--landed)", "watch": "var(--watch)", "stalled": "var(--stalled)"}

STROKE = 1.5
RADIUS = 4
DASH = "4 3"
LABEL_PX = 11
VALUE_PX = 14
WIDE = 720  # the desktop viewBox width
TALL = 340  # the phone variant's width: it reads at 390px with a 16px gutter, no sideways scroll
MONO_ADVANCE = 0.6  # the mono face's advance per em, for sizing chips and checking that labels fit
TRACK = 0.06  # label tracking, in em

# The rules a page adds once, after its own stylesheet. Phones get the tall variant; desktops the wide one.
CSS = (
    ":root{--ill:#74A5DA}"
    ".sk{margin:0;min-width:0}"
    ".sk svg{display:block;max-width:100%;height:auto;overflow:visible}"
    ".sk .sk-tall{display:none}"
    ".sk svg.sk-one{width:100%}"
    ".sk svg.sk-icon{flex:none;overflow:visible}"
    "@media (max-width:760px){.sk .sk-wide{display:none}.sk .sk-tall{display:block}}"
    ".sk text{font-family:var(--sans);fill:currentColor}"
    ".sk .sk-l{font-family:var(--mono);font-size:11px;letter-spacing:.06em}"
    ".sk .sk-v{font-family:var(--sans);font-weight:500;font-variant-numeric:tabular-nums}"
    ".sk figcaption{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;margin-top:14px;"
    "font-size:13px;line-height:1.5;color:var(--t2);max-width:76ch}"
    ".sk-ill{display:inline-flex;align-items:center;gap:7px;font:400 10px/16px var(--mono);letter-spacing:.1em;"
    "text-transform:uppercase;color:var(--ill);border:1px solid currentColor;border-radius:4px;padding:1px 7px;"
    "white-space:nowrap}"
    ".sk-ill::before{content:'';width:4px;height:4px;border-radius:50%;background:currentColor;flex:none}"
    ".sk-hdr{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px 24px;"
    "padding-bottom:20px;margin-bottom:36px;border-bottom:1px solid var(--line)}"
    ".sk-brand{display:flex;align-items:center;gap:10px;font-weight:600;font-size:15px;letter-spacing:-.01em}"
    ".sk-meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;font:400 10px/16px var(--mono);"
    "letter-spacing:.1em;text-transform:uppercase;color:var(--t3)}"
    ".sk-meta>span:first-child{color:var(--t1)}"
)


def num(value: float) -> str:
    """A coordinate or size, fixed: at most two decimals, no trailing zeros, never -0."""
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def _attrs(pairs: dict[str, object]) -> str:
    out = []
    for key, value in pairs.items():
        if value is None or value is False:
            continue
        name = key.rstrip("_").replace("_", "-")
        shown = num(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else esc(value)
        out.append(f' {name}="{shown}"')
    return "".join(out)


def _el(tag: str, body: str | None = None, **attrs: object) -> str:
    if body is None:
        return f"<{tag}{_attrs(attrs)}/>"
    return f"<{tag}{_attrs(attrs)}>{body}</{tag}>"


def scale(domain: tuple[float, float], to: tuple[float, float]) -> Callable[[float], float]:
    """A linear map from data to the drawing. An empty domain maps everything to the middle."""
    (d0, d1), (r0, r1) = domain, to
    if d1 == d0:
        return lambda _v: (r0 + r1) / 2
    k = (r1 - r0) / (d1 - d0)
    return lambda v: r0 + (v - d0) * k


def label_width(text: str, px: float = LABEL_PX) -> float:
    """The width a mono label takes, tracking included, so a layout can check it fits."""
    return len(text) * px * (MONO_ADVANCE + TRACK)


# Frame and figure


def frame(body: str, *, label: str, height: float, width: float = WIDE, variant: str = "wide") -> str:
    """One SVG. role="img" with an aria-label that states the answer in one sentence.

    variant: wide (720, desktop), tall (340, phones) or one (always shown; for small multiples that reflow)."""
    if variant not in ("wide", "tall", "one"):
        raise ValueError("variant is wide, tall or one")
    return _el(
        "svg",
        body,
        class_=f"sk-{variant}",
        width=width,
        height=height,
        viewBox=f"0 0 {num(width)} {num(height)}",
        role="img",
        aria_label=label,
        xmlns="http://www.w3.org/2000/svg",
    )


def icon(body: str, *, width: float, height: float) -> str:
    """A small decorative SVG, such as a key swatch, hidden from screen readers because its words sit beside it."""
    return _el("svg", body, class_="sk-icon", width=width, height=height, viewBox=f"0 0 {num(width)} {num(height)}", aria_hidden="true", focusable="false")


def figure(*svgs: str, caption: str, illustrative: bool = True, cls: str = "") -> str:
    """The visual with its plain-words caption and, for synthetic figures, the Illustrative tag."""
    tag = '<span class="sk-ill">Illustrative</span>' if illustrative else ""
    return f'<figure class="sk{" " + esc(cls) if cls else ""}">{"".join(svgs)}<figcaption><span>{esc(caption)}</span>{tag}</figcaption></figure>'


def defs(*parts: str) -> str:
    return f"<defs>{''.join(parts)}</defs>"


def hatch_pattern(pattern_id: str, tone: str = MUTED) -> str:
    """45 degree, 1px hatching. Give each SVG its own id: a pattern inside a hidden SVG does not paint."""
    line = _el("line", x1=0, y1=0, x2=0, y2=6, stroke=tone, stroke_width=1)
    return _el("pattern", line, id=pattern_id, width=6, height=6, patternUnits="userSpaceOnUse", patternTransform="rotate(45)")


# Text


def label(x: float, y: float, text: str, *, anchor: str = "start", tone: str = MUTED) -> str:
    """A mono label: 11px, upper case, tracked."""
    return _el("text", esc(text.upper()), x=x, y=y, class_="sk-l", text_anchor=None if anchor == "start" else anchor, style=f"color:{tone}")


def value(x: float, y: float, text: str, *, anchor: str = "start", tone: str = INK, size: float = VALUE_PX) -> str:
    """A figure in the sans, tabular."""
    return _el("text", esc(text), x=x, y=y, class_="sk-v", font_size=size, text_anchor=None if anchor == "start" else anchor, style=f"color:{tone}")


def status_word(x: float, y: float, word: str, *, anchor: str = "start") -> str:
    """The status mark and its word, as the template's .st draws it: a square for landed and stalled, a ring for
    watch. The only place green or red is painted, so the colour never prints without its word."""
    tone = STATUS_TONES.get(word)
    if tone is None:
        raise ValueError(f"status is landed, watch or stalled, not {word!r}")
    width = 7 + 7 + label_width(word)
    left = {"start": x, "middle": x - width / 2, "end": x - width}[anchor]
    if word == "watch":
        mark = _el("circle", cx=left + 4, cy=y - 4, r=3.5, fill="none", stroke=tone, stroke_width=STROKE)
    else:
        mark = _el("rect", x=left, y=y - 7.5, width=7, height=7, rx=2, fill=tone)
    return f'<g class="sk-st">{mark}{label(left + 14, y, word, tone=tone)}</g>'


# Lines and marks


def line_series(points: Sequence[tuple[float, float]], *, tone: str = INK, width: float = STROKE, dashed: bool = False) -> str:
    """A series as one polyline."""
    pts = " ".join(f"{num(x)},{num(y)}" for x, y in points)
    return _el(
        "polyline",
        points=pts,
        fill="none",
        stroke=tone,
        stroke_width=width,
        stroke_linejoin="round",
        stroke_linecap="round",
        stroke_dasharray=DASH if dashed else None,
    )


def point(x: float, y: float, *, r: float = 4, fill: str = INK, ring: str | None = BG) -> str:
    """A reading. The ring in the page background lifts it off the lines behind."""
    return _el("circle", cx=x, cy=y, r=r, fill=fill, stroke=ring, stroke_width=2 if ring else None)


def hollow(x: float, y: float, *, r: float = 4, tone: str = INK) -> str:
    return _el("circle", cx=x, cy=y, r=r, fill=BG, stroke=tone, stroke_width=STROKE)


def rule(x1: float, y1: float, x2: float, y2: float, *, tone: str = LINE2, width: float = 1, dashed: bool = False) -> str:
    """A hairline: axes, gridlines, connectors."""
    return _el("line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=tone, stroke_width=width, stroke_dasharray=DASH if dashed else None)


def target_line(x1: float, x2: float, y: float, *, tone: str = INK) -> str:
    """The target, across: ink, dashed 4 3."""
    return rule(x1, y, x2, y, tone=tone, width=STROKE, dashed=True)


def target_tick(x: float, y1: float, y2: float, *, tone: str = INK) -> str:
    """The target, upright, for a horizontal scale."""
    return rule(x, y1, x, y2, tone=tone, width=STROKE, dashed=True)


def zone(x: float, y: float, w: float, h: float, *, tone: str = LINE) -> str:
    """The target zone. Neutral, never green: being in it is not the verdict, the status word is."""
    return _el("rect", x=x, y=y, width=max(0.0, w), height=max(0.0, h), fill=tone)


def hatched(x: float, y: float, w: float, h: float, *, pattern_id: str, rx: float = RADIUS) -> str:
    """An area filled with a hatch_pattern(): over budget, or can't see."""
    return _el("rect", x=x, y=y, width=max(0.0, w), height=max(0.0, h), rx=rx, fill=f"url(#{pattern_id})")


def deadline(x: float, y1: float, y2: float, *, tone: str = MUTED) -> str:
    """The date the target is due: a solid upright with a small cap."""
    return rule(x, y1, x, y2, tone=tone, width=STROKE) + rule(x - 4, y1, x + 4, y1, tone=tone, width=STROKE)


# Bars


def range_bar(x1: float, x2: float, y: float, *, point_x: float | None = None, height: float = 10, tone: str = LINE3, point_tone: str = INK) -> str:
    """A likely range as a band, with the point estimate on it."""
    lo, hi = sorted((x1, x2))
    band = _el("rect", x=lo, y=y - height / 2, width=max(1.0, hi - lo), height=height, rx=min(RADIUS, height / 2), fill=tone)
    return band + (point(point_x, y, r=6, fill=point_tone) if point_x is not None else "")


def hbar(x: float, y: float, *, actual: float, budget: float, height: float = 12, tone: str = INK2, hatch_id: str | None = None) -> str:
    """A horizontal bar against a budget notch. actual and budget are lengths in drawing units; any part of the
    bar past the notch is hatched, so the overage reads without colour."""
    inside = min(actual, budget)
    parts = [_el("rect", x=x, y=y, width=max(0.0, inside), height=height, rx=1, fill=tone)]
    if actual > budget:
        fill = f"url(#{hatch_id})" if hatch_id else "none"
        parts.append(_el("rect", x=x + budget, y=y + 0.75, width=actual - budget, height=height - 1.5, fill=fill, stroke=tone, stroke_width=STROKE))
    parts.append(rule(x + budget, y - 5, x + budget, y + height + 5, tone=INK, width=STROKE))
    return "".join(parts)


# Grids, rows and blocks


def dot_grid(x: float, y: float, *, cols: int, rows: int, cell: float, r: float = 1, tone: str = LINE3) -> str:
    """A faint dot at each grid crossing, for a two-axis read."""
    dots = (_el("circle", cx=x + c * cell, cy=y + w * cell, r=r, fill=tone) for w in range(rows + 1) for c in range(cols + 1))
    return "".join(dots)


def timeline_row(x1: float, x2: float, y: float, *, flagged: bool = False, tone: str = INK2) -> str:
    """Raised to decided: an open start, a line, a filled end. A flagged row draws heavier, in ink."""
    tone = INK if flagged else tone
    width = 2.5 if flagged else STROKE
    return rule(x1, y, x2, y, tone=tone, width=width) + hollow(x1, y, r=3.5, tone=tone) + point(x2, y, r=3.5, fill=tone)


def tile(x: float, y: float, w: float, h: float, *, filled: bool = False, tone: str = MUTED) -> str:
    """A block: filled for done, outlined for open."""
    if filled:
        return _el("rect", x=x, y=y, width=w, height=h, rx=RADIUS, fill=tone)
    return _el("rect", x=x + 0.75, y=y + 0.75, width=w - 1.5, height=h - 1.5, rx=RADIUS, fill="none", stroke=tone, stroke_width=STROKE)


def gate(x: float, y: float, *, state: str, size: float = 24) -> str:
    """One check: ready is an outline with a tick, hold is solid ink."""
    if state == "hold":
        return tile(x, y, size, size, filled=True, tone=INK)
    if state != "ready":
        raise ValueError("a gate is ready or hold")
    s = size
    tick = f"M{num(x + s * 0.28)},{num(y + s * 0.52)} L{num(x + s * 0.44)},{num(y + s * 0.68)} L{num(x + s * 0.74)},{num(y + s * 0.34)}"
    path = _el("path", d=tick, fill="none", stroke=INK, stroke_width=STROKE, stroke_linecap="round", stroke_linejoin="round")
    return tile(x, y, s, s, tone=INK) + path


def chip(x: float, y: float, text: str, *, tone: str = INK2, filled: bool = False) -> str:
    """A label in a 4px box. y is the box's top; the box is 18 high."""
    w = label_width(text) + 14
    box = _el("rect", x=x + 0.75, y=y + 0.75, width=w - 1.5, height=16.5, rx=RADIUS, fill=tone if filled else "none", stroke=tone, stroke_width=1)
    return box + label(x + 7, y + 13, text, tone=BG if filled else tone)


def chip_width(text: str) -> float:
    return label_width(text) + 14


# Who did it


def spark(x: float, y: float, *, size: float = 8, tone: str = AGENT) -> str:
    """Agent work: a small four-point spark, centred on (x, y)."""
    s, k = size / 2, size / 8
    pts = ((x, y - s), (x + k, y - k), (x + s, y), (x + k, y + k), (x, y + s), (x - k, y + k), (x - s, y), (x - k, y - k))
    d = "M" + " L".join(f"{num(px)},{num(py)}" for px, py in pts) + " Z"
    return _el("path", d=d, fill=tone)


def person(x: float, y: float, *, size: float = 12, tone: str = BRASS) -> str:
    """A person's call: head and shoulders in brass, centred on x, standing on y."""
    s = size
    head = _el("circle", cx=x, cy=y - s * 0.72, r=s * 0.22, fill=tone)
    w, top = s * 0.42, y - s * 0.42
    body = f"M{num(x - w)},{num(y)} Q{num(x - w)},{num(top)} {num(x)},{num(top)} Q{num(x + w)},{num(top)} {num(x + w)},{num(y)} Z"
    return head + _el("path", d=body, fill=tone)


# The shared page header


def mark(size: float = 22) -> str:
    """The four-bar mark: two agent bars in grey, the person's line in brass, the result in ink."""
    bars = (
        _el("rect", x=2, y=13, width=3, height=7, fill=AGENT),
        _el("rect", x=7, y=10, width=3, height=10, fill=AGENT),
        _el("rect", x=12, y=2, width=1.5, height=20, fill=BRASS),
        _el("rect", x=16, y=4, width=4, height=16, fill=INK),
    )
    return _el("svg", "".join(bars), width=size, height=size, viewBox="0 0 24 24", fill="none", aria_hidden="true", focusable="false")


def page_header(skill: str, *, date: str, version: str, illustrative: bool) -> str:
    """The header every sample page shares: mark, DACARD, the skill's name, the date, the version, and the blue
    Illustrative tag when the figures are synthetic."""
    tag = '<span class="sk-ill">Illustrative</span>' if illustrative else ""
    return (
        f'<header class="sk-hdr"><span class="sk-brand">{mark()}<span translate="no">DACARD</span></span>'
        f'<span class="sk-meta"><span>{esc(skill)}</span><span>{esc(date)}</span><span>{esc(version)}</span>{tag}</span></header>'
    )


# Checks a page's tests use

TEXT = re.compile(r"<text\b[^>]*>(.*?)</text>", re.DOTALL)
FIGURE = re.compile(r"\d[\d,.:/%-]*\d%?|\d%?")


def texts_in(svg: str) -> list[str]:
    """Every string an SVG prints, unescaped."""
    return [html.unescape(t) for t in TEXT.findall(svg)]


def numbers_in(svg: str) -> list[str]:
    """Every figure an SVG prints (numbers, percents, dates), so a test can find each in the page's own text."""
    return [m.group(0) for t in texts_in(svg) for m in FIGURE.finditer(t)]


def svgs_in(page: str) -> list[str]:
    return re.findall(r"<svg\b.*?</svg>", page, re.DOTALL)


def visuals_in(page: str) -> list[str]:
    """The page's pictures: every SVG with role="img", leaving out the mark and key icons."""
    return [svg for svg in svgs_in(page) if 'role="img"' in svg.split(">", 1)[0]]


def page_text(page: str) -> str:
    """The page's printed text with every SVG taken out, unescaped and upper-cased, for figure checks."""
    body = page.split("</style>", 1)[-1]
    for svg in svgs_in(body):
        body = body.replace(svg, " ")
    return html.unescape(re.sub(r"<[^>]+>", " ", body)).upper()


def unprinted(page: str) -> list[str]:
    """Figures drawn in the page's SVGs that the page does not also print as text. Empty is the pass."""
    text = page_text(page)
    return sorted({n for svg in svgs_in(page) for n in numbers_in(svg) if n.upper() not in text})


def join(parts: Iterable[str]) -> str:
    return "".join(parts)
