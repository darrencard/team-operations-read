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

Scorecard rows (1.1.0, 2026-11-27): the grammar of the outcome scorecard on dacard.ai/update. A visual is HTML and
CSS rows, not one scaled SVG: name | picture | figure | word, split by hairlines, with one mono head. Pictures are
four, each a fixed-height SVG with no text and no viewBox, so nothing scales: range line, paired plan/actual
bars, share bar, pips. Labels, figures and words are Geist Mono 12px; names Geist 14px. SCORECARD_CSS holds the
rules; sc_frame(), sc_row() and the pictures write the markup.

1.2.0: one scale per frame (frame_domain(), with a minimum visible gap between marks that differ), the stacking
breakpoint as a container query (a frame under 800px wide stacks its rows, as the site's row kit does), and a
word column that wraps at word_max instead of squeezing the name. The SVG primitives from 1.0.0 are deprecated:
each call warns, and legacy_in() finds their output on a page. tools/SCORECARD-ROLLOUT.md is the adoption recipe;
tools/scorecard-golden.json is the class structure the site's row kit must match.

Vendor this file byte-identical, pinned by landing-loop commit and sha256 (tools/SVGKIT.md).
Standard library only. Python 3.11 or later.
"""

from __future__ import annotations

import functools
import html
import re
import warnings
from collections.abc import Callable, Iterable, Sequence

VERSION = "1.2.0"

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



# Scorecard rows (1.1.0): HTML and CSS rows in the grammar of the /update outcome scorecard.

SC_MONO_PX = 12  # every label, figure and word, as rendered
SC_NAME_PX = 14  # every name, as rendered
SC_RANGE_H = 12  # the range line's height
SC_BAR_H = 6  # each plan or actual bar; 2px between them
SC_PIP_H = 8
STATUSES = ("landed", "watch", "stalled")

# Class names follow the Leader Report template (.sc, .sc-h, .sc-r, .sc-n, .sc-l, .sc-s, .st, .bl's .pr/.ac/.goal)
# and its colour variables, scoped under .scg so these sizes win over the template's 10px ones on the same page.
# Every font size here is 12px (mono) or 14px (names); a site under html{zoom:.8} sets --sc-z:.8 to keep them so.
SCORECARD_CSS = (
    ".scg{--sc-z:1;--sc-m:calc(12px / var(--sc-z));--sc-n:calc(14px / var(--sc-z));container:sc / inline-size;margin:0;padding:0;min-width:0;"
    "border-top:1px solid var(--line2);border-bottom:1px solid var(--line2)}"
    ".scg .sc-t{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 32px;padding:12px 0}"
    ".scg .sc-t>span:first-child{display:flex;flex-wrap:wrap;align-items:center;gap:6px 16px}"
    ".scg .sc-t,.scg .sc-h,.scg .sc-l,.scg .sc-s,.scg .st,.scg .sc-w,.scg .sc-o,.scg .sc-x,.scg .sc-c,.scg .sc-i{"
    "font-family:var(--mono);font-size:var(--sc-m);line-height:16px;font-weight:400;font-variant-numeric:tabular-nums}"
    ".scg .sc-t,.scg .sc-h,.scg .sc-s,.scg .st,.scg .sc-w,.scg .sc-i{letter-spacing:.06em;text-transform:uppercase}"
    ".scg .sc-t,.scg .sc-h,.scg .sc-x{color:var(--t3)}"
    ".scg .sc-k{display:inline-flex;align-items:center;gap:6px}"
    ".scg .sc-k i{display:inline-block;width:12px;height:6px;border-radius:1px;background:var(--agent-mid)}"
    ".scg .sc-k i.k-a{background:var(--t1)}"
    ".scg .sc-k i.k-o{background:repeating-linear-gradient(135deg,var(--t1) 0 2px,transparent 2px 4px)}"
    ".scg .sc-k i.k-pr{width:8px;height:8px;border-radius:50%}"
    ".scg .sc-k i.k-tg{width:1.5px;height:12px;border-radius:0;background:var(--t2)}"
    ".scg .sc-b{display:grid;grid-template-columns:minmax(120px,.9fr) minmax(96px,1.3fr) max-content fit-content(var(--sc-wmax,180px));column-gap:32px}"
    ".scg .sc-h,.scg .sc-r{grid-column:1/-1;display:grid;grid-template-columns:subgrid;align-items:center}"
    ".scg .sc-h{padding:0 0 10px}"
    ".scg .sc-r{border-top:1px solid var(--line);padding:14px 0}"
    ".scg .sc-h>:nth-child(3),.scg .sc-l{text-align:right}"
    ".scg .sc-h>:nth-child(4),.scg .sc-s{text-align:right}"
    ".scg .sc-n{font-family:var(--sans);font-size:var(--sc-n);line-height:1.4;color:var(--t1);min-width:0;overflow-wrap:anywhere}"
    ".scg .sc-l{color:var(--t3);white-space:nowrap}"
    ".scg .sc-l b{color:var(--t1);font-weight:500}.scg .sc-l i{font-style:normal}"
    ".scg .sc-p{min-width:0;display:flex;align-items:center}"
    ".scg .sc-p svg{display:block;width:100%;overflow:visible}"
    ".scg .sc-s{display:flex;flex-direction:column;align-items:flex-end;gap:2px;min-width:0;text-align:right}"
    ".scg .st{white-space:nowrap}"
    ".scg .st{display:inline-flex;align-items:center;gap:7px}"
    ".scg .st::before{content:'';width:7px;height:7px;border-radius:2px;background:currentColor;flex:none}"
    ".scg .st.watch::before{width:8px;height:8px;border-radius:50%;background:none;border:1.5px solid currentColor;box-sizing:border-box}"
    ".scg .st.landed{color:var(--landed)}.scg .st.watch{color:var(--watch)}.scg .st.stalled{color:var(--stalled)}"
    ".scg .sc-w{color:var(--t3)}.scg .sc-w.ink{color:var(--t1)}"
    ".scg .sc-o{display:inline;color:var(--brass);text-transform:none;letter-spacing:0}"
    ".scg .sc-o svg{display:inline-block;margin-right:6px;vertical-align:0}"
    ".scg .sc-x{grid-column:1/-1;border-top:1px solid var(--line);padding:12px 0}"
    ".scg .sc-c{display:block;color:var(--t3);padding:10px 0 12px;border-top:1px solid var(--line)}"
    ".scg .sc-i{display:inline-flex;align-items:center;gap:7px;color:var(--ill)}"
    ".scg .sc-i::before{content:'';width:4px;height:4px;border-radius:50%;background:currentColor;flex:none}"
    ".sc-rl .tr{fill:var(--line2)}.sc-rl .mv{fill:var(--agent-mid)}.sc-rl .tg{fill:var(--t2)}"
    ".sc-rl .pr{fill:var(--agent-mid)}.sc-rl .ac{fill:var(--t1);stroke:var(--bg);stroke-width:2}"
    ".sc-rl .ac.landed{fill:var(--landed)}.sc-rl .ac.stalled{fill:var(--stalled)}"
    ".sc-rl .ac.watch{fill:var(--bg);stroke:var(--watch);stroke-width:2}"
    ".sc-pv .pl{fill:var(--agent-mid)}.sc-pv .a{fill:var(--t1)}.sc-pv .ov{stroke:var(--t1);stroke-width:1}"
    ".sc-pv pattern line{stroke:var(--t1);stroke-width:1.5}"
    ".sc-sh .tr{fill:var(--line2)}.sc-sh .a{fill:var(--t1)}"
    ".sc-pp .on{fill:var(--t2)}.sc-pp .off{fill:none;stroke:var(--t3);stroke-width:1}.sc-pp .dash{stroke-dasharray:2 2}"
    ".sc-pm{fill:var(--brass)}"
    "@container sc (max-width:799.98px){"
    ".scg .sc-b{display:block}"
    ".scg .sc-h{display:none}"
    ".scg .sc-r{grid-template-columns:minmax(0,1fr) max-content;grid-template-areas:'n s' 'l l' 'p p';column-gap:16px;row-gap:6px}"
    ".scg .sc-n{grid-area:n}.scg .sc-s{grid-area:s;align-self:start;max-width:var(--sc-wmax,180px)}.scg .sc-l{grid-area:l;text-align:left;white-space:normal}"
    ".scg .sc-p{grid-area:p;margin-right:64px}.scg .sc-p:empty{display:none}}"
)


def _pct(value: float) -> str:
    return num(max(0.0, min(100.0, value))) + "%"


def _svg(cls: str, height: float, body: str) -> str:
    """A fixed-height picture: width 100% of its cell, height in pixels, no viewBox, so nothing in it scales."""
    return f'<svg class="{cls}" width="100%" height="{num(height)}" aria-hidden="true" focusable="false">{body}</svg>'


def sc_frame(
    rows: Iterable[str],
    *,
    label: str,
    title: str,
    head: Sequence[str] = (),
    legend: str = "",
    caption: str = "",
    illustrative: bool = True,
    word_max: int | None = None,
) -> str:
    """One visual: a frame head (section label, legend, Illustrative tag top right), one mono column head, the
    rows, and one caption line. role="img" with an aria-label that states the answer. Hairlines top and bottom,
    never a box, so it sits inside a card or a page without a box inside a box. The word column wraps at word_max
pixels (default 180), so a long role ("Head of Product, Quoting squad") takes two lines instead of squeezing the
name. A frame under 800px wide stacks its rows."""
    tag = '<span class="sc-i">Illustrative</span>' if illustrative else ""
    top = f'<div class="sc-t"><span><span>{esc(title)}</span>{legend}</span>{tag}</div>'
    cols = f'<div class="sc-h">{"".join(f"<span>{esc(h)}</span>" for h in head)}</div>' if head else ""
    cap = f'<span class="sc-c">{esc(caption)}</span>' if caption else ""
    wmax = f' style="--sc-wmax:{int(word_max)}px"' if word_max else ""
    return f'<div class="sc scg" role="img" aria-label="{esc(label)}"{wmax}>{top}<div class="sc-b">{cols}{"".join(rows)}</div>{cap}</div>'


def sc_row(name: str, *, picture: str = "", figure: str = "", word: str = "") -> str:
    """One row: name | picture | figure | word. name is plain text; the others are markup from this module."""
    figure = figure or '<span class="sc-l"></span>'
    return f'<div class="sc-r"><span class="sc-n">{esc(name)}</span><span class="sc-p">{picture}</span>{figure}<span class="sc-s">{word}</span></div>'


def sc_note(text: str) -> str:
    """One muted line in place of rows that have nothing to show, so no row is left blank."""
    return f'<div class="sc-x">{esc(text)}</div>'


def legend(kind: str, text: str) -> str:
    """A key mark for the frame head: plan, actual, over (hatched), prior (dot) or target (tick)."""
    cls = {"plan": "k-pl", "actual": "k-a", "over": "k-o", "prior": "k-pr", "target": "k-tg"}[kind]
    return f'<span class="sc-k"><i class="{cls}"></i>{esc(text)}</span>'


def figure_line(actual: str, *, prior: str | None = None, target: str | None = None, target_word: str = "TARGET", tail: str = "") -> str:
    """`prior → actual · TARGET x`: the actual in ink, medium weight, the rest muted; one right-aligned column."""
    parts = (f"{esc(prior)} <i>→</i> " if prior else "") + f"<b>{esc(actual)}</b>"
    if target:
        parts += f" · {esc(target_word)} {esc(target)}"
    if tail:
        parts += f" · {esc(tail)}"
    return f'<span class="sc-l">{parts}</span>'


MIN_GAP_PCT = 2.5  # marks closer than this share of the line are drawn apart
MIN_GAP_PX = 4  # by this many pixels each, in the order of their values


def frame_domain(rows: Iterable[tuple[float | None, float, float]], *, relative: bool = True, pad: float = 0.06) -> tuple[float, float]:
    """One scale for every range line in a frame. rows are (prior, actual, target). relative (the default) reads each
    value as a share of its row's target, so rows in different units share one scale and every target tick lines
    up; pass the result to range_line(domain=..., relative=True). The domain runs from the smallest value to the
    largest, padded by pad of the span each side: close values read apart, and nothing is invented."""
    values: list[float] = []
    for prior, actual, target in rows:
        base = target if relative and target else 1.0
        values += [v / base for v in (prior, actual, target) if v is not None]
    if not values:
        return (0.0, 1.0)
    lo, hi = min(values), max(values)
    room = (hi - lo) * pad or abs(hi) * 0.1 or 1.0
    return (lo - room, hi + room)


def range_line(
    *,
    actual: float,
    target: float | None = None,
    prior: float | None = None,
    status: str | None = None,
    domain: tuple[float, float] | None = None,
    relative: bool = False,
) -> str:
    """Prior (grey dot), actual (status dot, ink without a status), the move between them, a target tick. No band.

    domain: the frame's one scale, from frame_domain(); relative must match how it was built. Without a domain the
    row scales alone, 0 to 1.18 times its largest value, as the Leader Report's bullet() draws it. Two marks whose
    values differ but sit within MIN_GAP_PCT of the line are drawn MIN_GAP_PX apart each way, in value order, so
    2,060 → 2,100 and 18.1% against a target of 18% read apart. Equal values stay on the same spot."""
    if status is not None and status not in STATUSES:
        raise ValueError(f"status is landed, watch or stalled, not {status!r}")
    base = target if relative and target else 1.0
    values = [v for v in (actual, target, prior) if v is not None]
    lo, hi = domain or (0.0, max(values) * 1.18 or 1.0)
    x = scale((lo, hi), (0, 100))
    at = {k: x(v / base) for k, v in (("prior", prior), ("actual", actual), ("target", target)) if v is not None}
    raw = {"prior": prior, "actual": actual, "target": target}
    shift = {"prior": 0.0, "actual": 0.0}

    def apart(a: str, b: str, move_b_only: bool) -> None:
        if a not in at or b not in at or raw[a] == raw[b] or abs(at[a] - at[b]) >= MIN_GAP_PCT:
            return
        sign = 1 if raw[b] > raw[a] else -1  # b sits on its own side of a, in value order
        if move_b_only:
            shift[b] = sign * max(abs(shift[b]), MIN_GAP_PX)
        else:
            shift[b] += sign * MIN_GAP_PX
            shift[a] -= sign * MIN_GAP_PX

    apart("prior", "actual", move_b_only=False)
    apart("target", "actual", move_b_only=True)

    def nudge(k: str) -> str:
        return f' transform="translate({num(shift[k])} 0)"' if shift.get(k) else ""

    mid = SC_RANGE_H / 2
    parts = [f'<rect class="tr" x="0" y="{num(mid - 1)}" width="100%" height="2" rx="1"/>']
    if prior is not None:
        a, b = sorted((at["prior"], at["actual"]))
        parts.append(f'<rect class="mv" x="{_pct(a)}" y="{num(mid - 1)}" width="{_pct(b - a)}" height="2"/>')
    if target is not None:
        parts.append(f'<rect class="tg" x="{_pct(at["target"])}" y="0" width="1.5" height="{num(SC_RANGE_H)}" transform="translate(-0.75 0)"/>')
    if prior is not None:
        parts.append(f'<circle class="pr" cx="{_pct(at["prior"])}" cy="{num(mid)}" r="3.5"{nudge("prior")}/>')
    parts.append(f'<circle class="ac{" " + status if status else ""}" cx="{_pct(at["actual"])}" cy="{num(mid)}" r="4.5"{nudge("actual")}/>')
    return _svg("sc-rl", SC_RANGE_H, "".join(parts))


def paired_bars(plan: float, actual: float, *, top: float, hatch_id: str) -> str:
    """Plan grey above, actual ink below, both scaled to top (the visual's largest value). The part of the actual
    past the plan is hatched and outlined: hatching means over plan, nothing else. hatch_id must be unique on the page."""
    x = scale((0, top or 1), (0, 100))
    p, a = x(plan), x(actual)
    y2 = SC_BAR_H + 2
    pat = (
        f'<defs><pattern id="{esc(hatch_id)}" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="4"/></pattern></defs>'
    )
    parts = [f'<rect class="pl" x="0" y="0" width="{_pct(p)}" height="{SC_BAR_H}" rx="1"/>']
    parts.append(f'<rect class="a" x="0" y="{y2}" width="{_pct(min(a, p))}" height="{SC_BAR_H}" rx="1"/>')
    if actual > plan:
        parts.append(f'<rect class="ov" x="{_pct(p)}" y="{num(y2 + 0.5)}" width="{_pct(a - p)}" height="{num(SC_BAR_H - 1)}" fill="url(#{esc(hatch_id)})"/>')
        return _svg("sc-pv", 2 * SC_BAR_H + 2, pat + "".join(parts))
    return _svg("sc-pv", 2 * SC_BAR_H + 2, "".join(parts))


def share_bar(part: float, whole: float) -> str:
    """A proportion: the track in hairline grey, the share in ink. The figure prints beside it, as `13 of 15`."""
    w = part / whole * 100 if whole else 0
    return _svg("sc-sh", SC_BAR_H, f'<rect class="tr" x="0" y="0" width="100%" height="{SC_BAR_H}" rx="1"/><rect class="a" x="0" y="0" width="{_pct(w)}" height="{SC_BAR_H}" rx="1"/>')


def pips(filled: int, of: int, *, dashed: int = 0) -> str:
    """Level pips, filled to the level; `dashed` more pips after them print dashed (a band, not a known level).
    Fixed width: 12px a pip."""
    dots = []
    for i in range(of):
        cls = "on" if i < filled else "off dash" if i < filled + dashed else "off"
        dots.append(f'<circle class="{cls}" cx="{num(4 + i * 12)}" cy="4" r="3.5"/>')
    return f'<svg class="sc-pp" width="{num(of * 12 - 4)}" height="{SC_PIP_H}" aria-hidden="true" focusable="false">{"".join(dots)}</svg>'


def status_mark(word: str) -> str:
    """landed, watch or stalled with its mark. The only place green or red is painted."""
    if word not in STATUSES:
        raise ValueError(f"status is landed, watch or stalled, not {word!r}")
    return f'<span class="st {word}">{word}</span>'


def check_word(word: str, *, ink: bool = False) -> str:
    """A check word as text, never a boxed chip: muted, or ink when it needs attention (HOLD, BELOW TARGET)."""
    return f'<span class="sc-w{" ink" if ink else ""}">{esc(word)}</span>'


def person_mark() -> str:
    """A small brass person mark, 8 by 10, no text."""
    return '<svg width="8" height="10" aria-hidden="true" focusable="false"><circle class="sc-pm" cx="4" cy="2.5" r="2.2"/><path class="sc-pm" d="M0,10 Q0,5.5 4,5.5 Q8,5.5 8,10 Z"/></svg>'


def person_call(who: str, *, due: str | None = None) -> str:
    """A person's call: the role in brass text with the person mark, and the date beside it in muted mono."""
    out = f'<span class="sc-o">{person_mark()}{esc(who)}</span>'
    return out + (f'<span class="sc-w">{esc(due)}</span>' if due else "")


# Checks a page's tests use for scorecard rows

_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_PX = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?)px")


def font_sizes(css: str, scope: str = ".scg") -> list[str]:
    """Every font size declared by a rule whose selector is in scope: a px figure, or var(--sc-m)/var(--sc-n)."""
    out = []
    for sel, body in _RULE.findall(css):
        if scope not in sel:
            continue
        for decl in body.split(";"):
            prop, _, value = decl.partition(":")
            if prop.strip() == "font-size":
                out.append(value.strip())
            elif prop.strip() == "font":
                found = _PX.search(value)
                out.append(found.group(0) if found else value.strip())
    return out


def svgs_with_text(page: str) -> list[str]:
    return [svg for svg in svgs_in(page) if "<text" in svg]


def frames_in(page: str) -> list[str]:
    """Each scorecard frame's markup, whole."""
    out, start = [], 0
    while (i := page.find('<div class="sc scg"', start)) >= 0:
        depth, j = 0, i
        for m in re.finditer(r"<(/?)div\b", page[i:]):
            depth += -1 if m.group(1) else 1
            if depth == 0:
                j = i + m.end()
                break
        out.append(page[i : page.index(">", j) + 1])
        start = j
    return out


def scaled_svgs_in(page: str) -> list[str]:
    """SVGs inside scorecard frames that would scale: any with a viewBox. Empty is the pass."""
    return [svg for frame in frames_in(page) for svg in svgs_in(frame) if "viewBox" in svg.split(">", 1)[0]]


def boxed_classes(css: str) -> set[str]:
    """Classes that draw a full box: a rule with a border or outline on all sides that is not 0 or none."""
    out = set()
    for sel, body in _RULE.findall(css):
        if re.search(r"(?:^|;)\s*(?:border|outline)\s*:\s*(?!0|none)[^;]*\d", body):
            out |= set(re.findall(r"\.([\w-]+)\s*(?:$|,|::?[\w-]+\s*$)", sel.strip()))
    return out


def boxes_in_frames(page: str, css: str) -> list[str]:
    """Elements inside a scorecard frame that carry a boxed class: a box inside a box. Empty is the pass.
    Inline style borders count too."""
    boxed = boxed_classes(css) - {"st", "watch", "sc-t"}
    found = []
    for frame in frames_in(page):
        inner = frame.split(">", 1)[1]
        for cls in re.findall(r'class="([^"]+)"', inner):
            found += [c for c in cls.split() if c in boxed]
        found += re.findall(r'style="[^"]*(?:border|outline)\s*:[^"]*"', inner)
    return found


# The class structure of a frame, for the golden test the site's row kit shares (tools/scorecard-golden.json)

STRUCTURE_CLASS = re.compile(r"^(sc|scg|sc-[a-z]+|st|landed|watch|stalled|ink)$")


def structure(markup: str) -> list[str]:
    """The frame's skeleton: one line per element that carries a scorecard class, as the path of scorecard classes
    from the frame down ("sc.scg/sc-b/sc-r/sc-p/sc-rl"). Tags, other classes, text and attributes are ignored, so an
    HTML row kit (the site's rows.tsx) and this module can be checked for the same structure."""
    from html.parser import HTMLParser

    out: list[str] = []

    class Walk(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.stack: list[tuple[str, str | None]] = []

        def _label(self, attrs: list[tuple[str, str | None]]) -> str | None:
            cls = next((v for k, v in attrs if k in ("class", "classname")), None) or ""
            kept = sorted(c for c in cls.split() if STRUCTURE_CLASS.match(c))
            return ".".join(kept) or None

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            label = self._label(attrs)
            if label:
                out.append("/".join([x for _, x in self.stack if x] + [label]))
            if tag not in ("rect", "circle", "path", "line", "br", "img", "input", "meta"):
                self.stack.append((tag, label))

        def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            label = self._label(attrs)
            if label:
                out.append("/".join([x for _, x in self.stack if x] + [label]))

        def handle_endtag(self, tag: str) -> None:
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break

    Walk().feed(markup)
    return out


# Legacy (1.0.0) SVG primitives: deprecated in 1.2.0. They still draw, byte for byte, but each call warns, so a
# skill's tests can turn the warning into a failure, and legacy_in() finds their output on a page.

LEGACY = (
    "frame", "icon", "figure", "defs", "hatch_pattern", "label", "value", "status_word", "line_series", "point",
    "hollow", "rule", "target_line", "target_tick", "zone", "hatched", "deadline", "range_bar", "hbar", "dot_grid",
    "timeline_row", "tile", "gate", "chip", "chip_width", "spark", "person",
)  # fmt: skip
LEGACY_MARKERS = ('class="sk-wide"', 'class="sk-tall"', 'class="sk-one"', 'class="sk-icon"', 'class="sk-st"', 'class="sk-l"', 'class="sk-v"', '<figure class="sk')


def _deprecated(fn: Callable[..., str]) -> Callable[..., str]:
    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> str:
        warnings.warn(
            f"svgkit.{fn.__name__} is a legacy SVG primitive, deprecated in 1.2.0: draw scorecard rows (tools/SCORECARD-ROLLOUT.md)",
            DeprecationWarning,
            stacklevel=2,
        )
        return fn(*args, **kwargs)

    wrapper.deprecated = True  # type: ignore[attr-defined]
    return wrapper


for _name in LEGACY:
    globals()[_name] = _deprecated(globals()[_name])


def legacy_in(page: str) -> list[str]:
    """Marks of the legacy primitives on a page (their classes). Empty is the pass."""
    return [m for m in LEGACY_MARKERS if m in page]
