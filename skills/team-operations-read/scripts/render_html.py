"""The read as one self-contained HTML page, on the Leader Report's template and the Landing Loop's one visual family.

The page takes the report's whole stylesheet from its template (assets/vendor/template.html, vendored byte-identical
at a pinned commit) and draws its picture with svgkit (scripts/vendor/svgkit.py, vendored byte-identical from
landing-loop). Only a few rules for this page's layout are added.

It reads top down for someone who has never seen the framework: the shared header, where to start as the heading,
the area grid (every one of the 27 areas, the read ones shaded by level, the rest hatched because these exports
can't see them, the place to start ringed), then one thing to do next, owned by the person named. The areas read
and what the exports can't see follow in two columns. Each area in full, the evidence ledger and everything
technical sit in folds. Public copy uses plain words: area, level, scoring guide. The stored JSON keeps its words.

A team read has no project status, so the page uses no status colour: landed, watch and stalled belong to
did-it-land. Brass is only the person who decides the next step. Nothing is loaded from the network, nothing in the
output depends on the clock or the machine, and every piece of text from an export is escaped.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from framework import DIMENSION_IDS, FUNCTIONS
from rules import describe
from vendored import load

sk = load("svgkit")  # vendored unchanged from landing-loop; see VENDORED.json

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "vendor" / "template.html"
STYLE = re.compile(r"<style>(.*?)</style>", re.S)

# Layout for this page only. Everything else comes from the template's stylesheet and svgkit.CSS.
PAGE_CSS = """
main.solo{margin-left:0}
.solo .slide{min-height:0}
.solo .slide.cover{min-height:0;padding-top:40px;padding-bottom:48px;justify-content:flex-start}
.solo h1{font-size:clamp(34px,4.6vw,60px);line-height:1;letter-spacing:-.04em;max-width:20ch;margin-bottom:20px}
.solo .lede{margin-bottom:24px}
.solo h2{margin-bottom:16px}
.status{display:inline-block;font:400 11px/16px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t1);border:1px solid var(--line3);border-radius:3px;padding:1px 6px;white-space:nowrap}
.verdict{margin:0 0 20px;display:flex;flex-wrap:wrap;gap:8px}
.panel{border:1px solid var(--line);border-radius:12px;background:var(--s1);padding:24px 28px 20px}
@media (min-width:1100px){.panel .sk{display:grid;grid-template-columns:720px minmax(0,1fr);gap:16px 40px;align-items:start}.panel .sk figcaption{margin-top:0;flex-direction:column;align-items:flex-start}}
.next{margin-top:28px;display:grid;grid-template-columns:200px minmax(0,1fr);gap:8px 32px;align-items:baseline;border:1px solid var(--brass);border-radius:12px;padding:20px 24px;background:var(--brass-bg)}
.next>b{font:400 11px/22px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--brass)}
.next p{margin:0;font-size:16px;line-height:1.5;color:var(--t1)}
.next .who{display:flex;flex-wrap:wrap;gap:4px 24px;margin-top:10px;font:400 11.5px/16px var(--mono);color:var(--brass)}
.next .who span::before{font-size:11px;letter-spacing:.1em;color:var(--t3);margin-right:8px}
.next .who .o::before{content:"DECIDES"}.next .who .d::before{content:"RE-CHECK"}
.cols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px 56px;align-items:start}
.cols h3{margin-bottom:8px}
.areas{margin:0;padding:0;list-style:none}
.areas li{border-top:1px solid var(--line);padding:12px 0;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 16px;align-items:baseline}
.areas li b{font-weight:500;color:var(--t1);font-size:14.5px}
.areas li .lv{font:400 11px/16px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t1);white-space:nowrap}
.areas li p{grid-column:1/-1;margin:0;font-size:13.5px;line-height:1.5;color:var(--t2)}
.unseen{margin:0;padding:0;list-style:none}
.unseen li{border-top:1px solid var(--line);padding:10px 0;font-size:13.5px;line-height:1.5;color:var(--t2)}
.unseen li span{display:block;font:400 11px/18px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t3)}
.cols>div>p{font-size:13.5px;line-height:1.55;color:var(--t2);margin:0 0 10px}
.limits{margin:0;padding-left:18px;font-size:13.5px;line-height:1.55;color:var(--t2)}
.limits li{margin-bottom:8px}
.solo details{margin-top:4px}
.solo details>*:not(summary){margin-top:12px}
.solo details p,.solo details li{margin:0 0 10px;font-size:13px;color:var(--t2);max-width:80ch}
.solo details ul{padding-left:18px}
.solo details h3{margin:22px 0 6px}
.solo details .q{font-style:italic}
.tablewrap td,.tablewrap th{overflow-wrap:anywhere}
.tablewrap .ex{font-size:12px;color:var(--t3)}
::selection{background:var(--t1);color:var(--bg)}
:focus-visible{outline:2px solid var(--t1);outline-offset:3px;border-radius:3px}
.foot{max-width:1120px;margin:0 auto;padding:28px 40px 64px;color:var(--t3);font-size:12px}
@media (max-width:980px){.foot{padding:24px 16px 48px}.solo .slide.cover{padding-top:24px}.cols,.next{grid-template-columns:1fr}.panel{padding:18px 16px 16px}
.stack table,.stack tbody,.stack tr,.stack td{display:block}.stack tr:first-child{display:none}.stack tr{padding:10px 16px;border-bottom:1px solid var(--line)}
.stack td{border:0;padding:3px 0;display:grid;grid-template-columns:118px 1fr;gap:12px}.stack td.num{text-align:left;white-space:normal}
.stack td::before{content:attr(data-l);font:400 11px/20px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t3)}}
@media (max-width:440px){.panel{margin:0 -8px;padding:16px 8px 14px}}
"""

# The smallest text the page prints, at every width. The vendored template and svgkit keep their own sizes on disk
# (both are hash-pinned); the page raises any smaller size to this one as it inlines their rules.
FONT_FLOOR = 11
FONT_SIZE = re.compile(r"(font-size:\s*|font:[^;{}]*?)(\d+(?:\.\d+)?)px")


def floor_fonts(css: str) -> str:
    """Every font size below FONT_FLOOR, raised to it: font-size and the size in a font shorthand."""
    return FONT_SIZE.sub(lambda m: m.group(1) + (str(FONT_FLOOR) if float(m.group(2)) < FONT_FLOOR else m.group(2)) + "px", css)


LIMITS = [
    "It reads how work moves through the team, not whether what shipped worked. Pair it with outcome data before judging the team.",
    "Do not turn these figures into targets. A team pushed to cut review wait or reopens can hit the number and miss the point. Use them to pick where to look.",
    "The thresholds are Dacard v0.1 heuristics, not industry benchmarks. Treat each bound as a hypothesis to test with the team.",
    "Read a gap with the squad that owns it before acting. The slowest squads are where to ask questions, not who to blame.",
]

# The framework's words as the rules write them, and as the page prints them. The stored JSON keeps the rules' words.
WORDS = (
    (r"\(rubric Stage (\d)\)", r"(scoring guide, level \1)"),
    (r"\bShow Stage (\d):", r"To reach level \1:"),
    (r"\bStage (\d)", r"level \1"),
    (r"\bstages\b", "levels"),
    (r"\bstage\b", "level"),
    (r"\bdimensions\b", "areas"),
    (r"\bdimension\b", "area"),
    (r"Book a full Team Operations read to review (.+?) directly\.", r"A full Team Operations read would review \1 directly."),
    (r"\bspec template\b", "build plan template"),
    (r"\bautomated evaluation\b", "automated quality tests"),
    (r"\bdecision records\b", "decision logs"),
    (r"\barchitecture records\b", "architecture notes"),
    (r"\bincident records\b", "incident logs"),
    (r"\bpricing records\b", "pricing history"),
)
UNSEEN = "Can't see from these exports"


def e(text: Any) -> str:
    return html.escape(str(text), quote=True)


def plain(text: str) -> str:
    for pattern, to in WORDS:
        text = re.sub(pattern, to, text)
    return text


def said(f: dict) -> str:
    """A finding in plain words, with what it does to the level said outright: the scoring guide's citation alone
    reads as a level reached, when a ceiling cites the level not reached."""
    text = plain(re.sub(r" \(rubric Stage \d\)", "", f["says"]))
    if f["bound"]:
        side, n = f["bound"]
        text += f" That caps it at level {n}." if side == "ceiling" else f" That shows level {n} at least."
    return text


def stylesheet() -> str:
    """The report template's whole stylesheet, fonts included."""
    try:
        found = STYLE.search(TEMPLATE.read_text(encoding="utf-8"))
    except OSError:
        found = None
    return found.group(1) if found else ""


def level(d: dict) -> str:
    """The one phrase the page uses for an area's level: the read's own bounds, in plain words."""
    if d["read"] == "stage":
        return f"Level {d['stage']} ({d['stage_name']})"
    if d["read"] == "range":
        if d["ceiling"] == 5:
            return f"Level {d['floor']} or above"
        if d["floor"] == 1:
            return f"Level {d['ceiling']} or below"
        return f"Level {d['floor']} to {d['ceiling']}"
    if d["read"] == "conflict":
        return "Mixed evidence, no level"
    return UNSEEN


def short_level(d: dict) -> str:
    """The level as the grid prints it, in a box 112 wide."""
    if d["read"] == "stage":
        return f"Level {d['stage']}"
    if d["read"] == "conflict":
        return "Mixed"
    return level(d).removeprefix("Level ")


def fold(title: str, body: str) -> str:
    return f"<details><summary>{e(title)}</summary>{body}</details>"


class Table:
    """A table whose cells carry their column name, so a phone shows each row as labelled lines."""

    def __init__(self, heads: tuple[str, ...]) -> None:
        self.heads = heads
        self.rows: list[str] = []

    def row(self, *cells: tuple[str, str]) -> None:
        tds = []
        for head, (cls, body) in zip(self.heads, cells, strict=True):
            attr = f' class="{cls}"' if cls else ""
            tds.append(f'<td{attr} data-l="{e(head)}">{body}</td>')
        self.rows.append("<tr>" + "".join(tds) + "</tr>")

    def html(self) -> str:
        head = "<tr>" + "".join(f"<th>{e(h)}</th>" for h in self.heads) + "</tr>"
        return f'<div class="tablewrap stack"><table>{head}{"".join(self.rows)}</table></div>'


# The signature picture: the area grid


def wrap(text: str, chars: int) -> list[str]:
    """Words into lines of at most `chars` characters, so a name fits its box."""
    lines: list[str] = []
    for word in text.split():
        if lines and len(lines[-1]) + 1 + len(word) <= chars:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def _bar(x: float, y: float, w: float, *, filled: bool) -> str:
    if filled:
        return f'<rect x="{sk.num(x)}" y="{sk.num(y)}" width="{sk.num(w)}" height="8" rx="1" fill="{sk.INK}"/>'
    return (
        f'<rect x="{sk.num(x + 0.75)}" y="{sk.num(y + 0.75)}" width="{sk.num(w - 1.5)}" height="6.5" rx="1" fill="none" stroke="{sk.INK}" stroke-width="1.5"/>'
    )


def meter(x: float, y: float, d: dict, width: float) -> str:
    """Five marks for levels 1 to 5. Filled: levels the evidence shows. Outlined: levels it allows but cannot
    confirm. Faint: levels it rules out."""
    gap = 3.0
    w = (width - 4 * gap) / 5
    parts = []
    for st in range(1, 6):
        mx = x + (st - 1) * (w + gap)
        if d["read"] == "stage":
            shown, allowed = st <= d["stage"], False
        elif d["read"] == "range":
            shown, allowed = st <= d["floor"], d["floor"] < st <= d["ceiling"]
        else:  # conflict: the two ends the evidence points at, neither confirmed
            shown, allowed = False, st in (d["floor"], d["ceiling"])
        if shown or allowed:
            parts.append(_bar(mx, y, w, filled=shown))
        else:
            parts.append(f'<rect x="{sk.num(mx)}" y="{sk.num(y)}" width="{sk.num(w)}" height="8" rx="1" fill="{sk.LINE}"/>')
    return "".join(parts)


def area_tile(x: float, y: float, w: float, h: float, d: dict, chars: int, hid: str, start: bool) -> str:
    """One area. Read: a shaded box with its name, its level and the meter. Not read: an outline with its name and a
    hatched strip where the level would be."""
    read = d["read"] != "not_read"
    parts = []
    if read:
        parts.append(f'<rect x="{sk.num(x)}" y="{sk.num(y)}" width="{sk.num(w)}" height="{sk.num(h)}" rx="4" fill="var(--s2)"/>')
        parts.append(sk.tile(x, y, w, h, tone=sk.INK))
    else:
        parts.append(sk.tile(x, y, w, h, tone=sk.LINE2))
    for i, line in enumerate(wrap(d["name"], chars)[:2]):
        parts.append(sk.value(x + 9, y + 19 + i * 15, line, size=12.5, tone=sk.INK if read else sk.MUTED))
    if read:
        parts.append(sk.label(x + 9, y + h - 20, short_level(d), tone=sk.INK))
        parts.append(meter(x + 9, y + h - 14, d, w - 18))
    else:
        parts.append(sk.hatched(x + 9, y + h - 15, w - 18, 8, pattern_id=hid, rx=1))
    if start:
        parts.append(
            f'<rect x="{sk.num(x - 5)}" y="{sk.num(y - 5)}" width="{sk.num(w + 10)}" height="{sk.num(h + 10)}" rx="9" fill="none" stroke="{sk.INK}" stroke-width="1.5"/>'
        )
        parts.append(sk.chip(x + w - sk.chip_width("Start here") + 5, y - 14, "Start here", tone=sk.INK, filled=True))
    return "".join(parts)


def key(x: float, y: float, hid: str, stacked: bool) -> str:
    """The key, in the picture's own marks."""
    items = [
        (_bar(0, -8, 22, filled=True), "Level shown"),
        (_bar(0, -8, 22, filled=False), "Level possible"),
        (sk.hatched(0, -8, 22, 8, pattern_id=hid, rx=1), UNSEEN),
    ]
    parts = []
    cx = x
    for i, (mark, text) in enumerate(items):
        dx, dy = (x, y + i * 20.0) if stacked else (cx, y)
        parts.append(f'<g transform="translate({sk.num(dx)} {sk.num(dy)})">{mark}{sk.label(30, 0, text)}</g>')
        cx += 30 + sk.label_width(text) + 26
    return "".join(parts)


def area_grid(doc: dict, variant: str) -> str:
    """Every one of the 27 areas, by function. Wide: one column per function. Tall: each function in turn, two areas
    to a row."""
    wide = variant == "wide"
    hid = f"sk-to-hatch-{variant}"
    start = (doc["start_here"] or {}).get("dimension")
    by_fn = {fn: [d for d in doc["dimensions"] if d["function"] == fn] for fn in FUNCTIONS}
    parts = [sk.defs(sk.hatch_pattern(hid))]
    th, gap = 74.0, 12.0
    if wide:
        width, col, tw, top = sk.WIDE, 120.0, 112.0, 30.0
        for c, fn in enumerate(FUNCTIONS):
            x = c * col
            parts.append(sk.label(x, 12, fn, tone=sk.INK2))
            for r, d in enumerate(by_fn[fn]):
                parts.append(area_tile(x, top + r * (th + gap), tw, th, d, 15, hid, d["id"] == start))
        rows = max(len(v) for v in by_fn.values())
        y = top + rows * (th + gap) + 14
        parts.append(key(0, y, hid, stacked=False))
        height = y + 8
    else:
        width, tw = sk.TALL, 164.0
        y = 12.0
        for fn in FUNCTIONS:
            parts.append(sk.label(0, y, fn, tone=sk.INK2))
            y += 18
            group = by_fn[fn]
            for pair in (group[i : i + 2] for i in range(0, len(group), 2)):
                # A row of areas the exports can't see needs no room for a level, so the phone's grid stays short.
                lines = max(len(wrap(d["name"], 22)) for d in pair)
                rh = th if any(d["read"] != "not_read" for d in pair) else 30.0 + 15 * lines
                for i, d in enumerate(pair):
                    parts.append(area_tile(0.0 if i == 0 else width - tw, y, tw, rh, d, 22, hid, d["id"] == start))
                y += rh + gap
            y += 16
        parts.append(key(0, y, hid, stacked=True))
        height = y + 48
    return sk.frame("".join(parts), label=aria(doc), height=height, width=width, variant=variant)


def aria(doc: dict) -> str:
    """The answer the grid gives, in one sentence."""
    read = [d for d in doc["dimensions"] if d["read"] != "not_read"]
    text = f"These exports show {len(read)} of the 27 Team Operations areas and can't see the other {27 - len(read)}"
    sh = doc["start_here"]
    if not sh:
        return text + ", and none is bounded yet, so there is no place to start."
    d = next(x for x in doc["dimensions"] if x["id"] == sh["dimension"])
    return text + f"; start with {d['name']}, read at {level(d).lower()}."


# The words


def recheck_figure(doc: dict) -> dict | None:
    sh = doc["start_here"]
    return doc["figures"].get(sh["recheck_figure"]) if sh and sh["recheck_figure"] else None


def heading(doc: dict) -> str:
    sh = doc["start_here"]
    return f"Start with {sh['name']}." if sh else "No area can be read yet."


def answer(doc: dict) -> str:
    """The one line a leader reads first: where to start, and the figure that says why. The Markdown opens with it."""
    sh = doc["start_here"]
    if not sh:
        return "No area is bounded yet. Add squads.csv, then items.csv from your tracker, and run the read again."
    f = recheck_figure(doc)
    why = f" {f['label']}: {f['display']}." if f else ""
    return f"Start with {sh['name']}.{why}"


def lede(doc: dict) -> str:
    """The paragraph under the heading, plain text."""
    read = [d for d in doc["dimensions"] if d["read"] != "not_read"]
    w = doc["window"]
    text = (
        f"Team Operations scores how a product team works in 27 areas, each on five levels. {doc['company']}'s exports for the {w['days']} days "
        f"to {w['end']} show {len(read)} of them."
    )
    sh = doc["start_here"]
    if not sh:
        return text + " None is bounded yet: the data is below every rule's minimum sample or inside every threshold."
    d = next(x for x in doc["dimensions"] if x["id"] == sh["dimension"])
    f = binding(d)
    why = f" {said(f)}" if f else f" It reads {level(d).lower()}."
    return text + f" {sh['name']} asks: {d['question'][:1].lower()}{d['question'][1:]}{why}"


def summary(doc: dict) -> list[str]:
    """Five lines: what was read, the higher and lower reads, the open ones, and what was not read."""
    dims = doc["dimensions"]
    read = [d for d in dims if d["read"] != "not_read"]
    higher = [d for d in read if d["read"] in ("stage", "range") and (d["stage"] if d["read"] == "stage" else d["floor"]) >= 3]
    lower = [d for d in read if d["read"] in ("stage", "range") and (d["stage"] if d["read"] == "stage" else d["ceiling"]) <= 2]
    rest = [d for d in read if d not in higher and d not in lower]
    ov = doc["overall"]
    overall = f"Overall level {ov['stage']} ({ov['stage_name']})." if ov["claimed"] else "No overall level: that needs all 27."

    def names(ds: list[dict]) -> str:
        return "; ".join(f"{d['name']} at {level(d).lower()}" for d in ds) if ds else "none"

    return [
        f"Read {len(read)} of 27 areas from {len(doc['sources'])} exports over {doc['window']['days']} days. {overall}",
        f"Level 3 or higher: {names(higher)}.",
        f"Level 2 or lower: {names(lower)}.",
        f"Open or mixed: {names(rest)}.",
        f"{UNSEEN}: {len(dims) - len(read)} areas. Re-check on {doc['recheck_on']}.",
    ]


def binding(d: dict) -> dict | None:
    """The finding behind the area's tightest bound."""
    bound = [f for f in d["findings"] if f["bound"]]
    if not bound:
        return None
    ceilings = sorted((f for f in bound if f["bound"][0] == "ceiling"), key=lambda f: f["bound"][1])
    return (ceilings or bound)[0]


def areas_read(doc: dict) -> str:
    items = []
    for d in (x for x in doc["dimensions"] if x["read"] != "not_read"):
        f = binding(d)
        why = f"<p>{e(said(f))}</p>" if f else ""
        items.append(f'<li><b>{e(d["name"])}</b><span class="lv">{e(level(d))}</span>{why}</li>')
    return f'<ul class="areas">{"".join(items)}</ul>'


def unseen(doc: dict) -> str:
    items = []
    for fn in FUNCTIONS:
        group = [d["name"] for d in doc["dimensions"] if d["read"] == "not_read" and d["function"] == fn]
        if group:
            items.append(f"<li><span>{e(fn)}</span>{e(', '.join(group))}</li>")
    count = sum(1 for d in doc["dimensions"] if d["read"] == "not_read")
    lead = f"<p>{count} areas live in documents, conversations and decisions that tracker, source-control and survey exports do not capture.</p>"
    return lead + f'<ul class="unseen">{"".join(items)}</ul>'


def area_full(d: dict) -> str:
    rows = []
    for f in d["findings"]:
        note = "" if f["bound"] else (" Context, not scored." if f.get("context") else " Not scored.")
        rows.append(f"<li>{e(said(f))}{e(note)}</li>")
    if d["survey"]:
        rows.append(f"<li>{e(plain(d['survey']['says']))}</li>")
    if d["survey_disagrees"]:
        rows.append(f"<li>{e(plain(d['survey_disagrees']))}</li>")
    return (
        f'<h3 id="{e(d["id"])}">{e(d["name"])}: {e(level(d).lower())}</h3><p class="q">{e(d["question"])}</p>'
        f"<ul>{''.join(rows)}</ul><p><b>Next step:</b> {e(plain(d['next_step']))}</p>"
    )


def what_would_read(doc: dict) -> str:
    tab = Table(("Function", "Areas", "What would read them"))
    for fn in FUNCTIONS:
        group = [d for d in doc["dimensions"] if d["read"] == "not_read" and d["function"] == fn]
        steps: dict[str, list[dict]] = {}
        for d in group:
            steps.setdefault(d["next_step"], []).append(d)
        for step, ds in steps.items():
            views = " ".join(f"{d['name']}: {d['survey']['says']}" for d in ds if d["survey"] and d["survey"]["shown"])
            tab.row(("", e(fn)), ("", e(", ".join(d["name"] for d in ds))), ("", e(plain(step)) + ((" " + e(views)) if views else "")))
    return tab.html()


def ledger(doc: dict) -> str:
    def table(figs: list[dict]) -> str:
        tab = Table(("Figure", "Value", "Source", "Window", "Rows", "Method"))
        for f in figs:
            w = f"{f['window']['from']} to {f['window']['to']}"
            tab.row(("", e(f["label"])), ("num", e(f["display"])), ("ex", e(f["source"])), ("ex", e(w)), ("num", e(f["n"])), ("ex", e(f["method"])))
        return tab.html()

    figs = list(doc["figures"].values())
    main_rows = [f for f in figs if ".squad." not in f["id"]]
    squad_rows = [f for f in figs if ".squad." in f["id"]]
    body = f"<p>Every figure, computed in code from the exports named, as of {e(doc['as_of'])}. Nothing is estimated.</p>{table(main_rows)}"
    if squad_rows:
        body += f"<h3>By squad ({len(squad_rows)} figures), context only</h3>{table(squad_rows)}"
    if doc["systems"]:
        body += "<p>" + e("Where each file came from: " + "; ".join(f"{k}, {v}" for k, v in doc["systems"].items()) + ".") + "</p>"
    return body


def engineers(doc: dict) -> str:
    rows = Table(("Area", "Stored read", "Rules"))
    for d in doc["dimensions"]:
        if d["read"] == "not_read":
            continue
        rows.row(("", e(d["id"])), ("", e(describe(d))), ("ex", e(", ".join(f["rule"] for f in d["findings"]))))
    return (
        f"<p>Skill: <code>team-operations-read</code> {e(doc['version'])}.</p>"
        "<p>Each area's read as the JSON stores it, with the rules behind it (references/rules.md). The page prints Stage as level and "
        "dimension as area.</p>"
        f"{rows.html()}"
        f"<p>Run: <code>python3 skills/team-operations-read/scripts/read.py --data DIR --as-of {e(doc['as_of'])} --window-days {e(doc['window']['days'])} "
        "--decides ROLE --out DIR --stem NAME</code>. It writes NAME.json, NAME.md and NAME.html, and exits 2 on bad input with the file, line and "
        "column named. Exports read: " + e(", ".join(f"{s}.csv" for s in doc["sources"])) + ".</p>"
        "<p>Before any prose about this read is shown, <code>check_claims.py --read NAME.json --draft draft.md</code> blocks a level the read "
        "does not support, an overall level it withholds, a figure not in the ledger, and project status words.</p>"
        "<p>Record key: none. A team read is about the team, not a project, so it writes nothing into a Landing Loop project file "
        "(<code>landing/&lt;bet&gt;.json</code>) and never opens one.</p>"
    )


def page(doc: dict) -> str:
    ill = doc["illustrative"]
    sh = doc["start_here"]
    header = sk.page_header("Team operations read", date=doc["as_of"], version=f"v{doc['version']}", illustrative=ill)
    read = [d for d in doc["dimensions"] if d["read"] != "not_read"]
    pic = sk.figure(
        area_grid(doc, "wide"),
        area_grid(doc, "tall"),
        caption=f"Each box is one of the 27 areas Team Operations scores, under its function. The {len(read)} shaded boxes are the areas these "
        "exports can read: the five marks are levels 1 to 5, filled where the evidence shows the level and outlined where it allows it but "
        f"cannot confirm it. The {27 - len(read)} hatched boxes can't be seen from these exports. The ringed box is where to start.",
        illustrative=ill,
    )
    chips = f'<span class="status">{len(read)} of 27 areas read</span>'
    if sh:
        d = next(x for x in doc["dimensions"] if x["id"] == sh["dimension"])
        chips = f'<span class="status">{e(sh["name"])}: {e(level(d).lower())}</span>' + chips
        who = f'<span class="o">{e(doc["decides"])}</span>' if doc["decides"] else ""
        f = recheck_figure(doc)
        again = f" Then run this read again with the same window to see whether it moved from {f['display']}." if f else ""
        step = (
            f'<div class="next"><b>What to do next</b><div><p>{e(plain(sh["next_step"]))}{e(again)}</p>'
            f'<span class="who">{who}<span class="d">{e(doc["recheck_on"])}</span></span></div></div>'
        )
    else:
        step = (
            '<div class="next"><b>What to do next</b><div><p>Add squads.csv (one row per squad with its roles), then items.csv from your tracker, '
            "and run the read again.</p></div></div>"
        )
    cover = (
        f'<section class="slide cover">{header}<h1>{e(heading(doc))}</h1><p class="lede">{e(lede(doc))}</p>'
        f'<p class="verdict">{chips}</p><div class="panel">{pic}</div>{step}</section>'
    )
    limits = "".join(f"<li>{e(x)}</li>" for x in LIMITS)
    detail = (
        '<section class="slide"><div class="meta"><span>What the read found</span></div><div class="cols">'
        f"<div><h3>The {len(read)} areas these exports can read</h3>{areas_read(doc)}</div>"
        f"<div><h3>{e(UNSEEN)}</h3>{unseen(doc)}"
        f'<h3 style="margin-top:28px">How to use this read</h3><ul class="limits">{limits}</ul></div>'
        "</div></section>"
    )
    folds = [
        fold("Each area in full", "".join(area_full(d) for d in sorted(read, key=lambda x: DIMENSION_IDS.index(x["id"])))),
        fold("What would read the other areas", what_would_read(doc)),
        fold("Every figure, with its source", ledger(doc)),
        fold("For your engineers", engineers(doc)),
    ]
    more = f'<section class="slide"><div class="meta"><span>Detail</span></div>{"".join(folds)}</section>'
    title = f"Team Operations read: {doc['company']}"
    return (
        '<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{e(title)}</title><style>{floor_fonts(stylesheet() + sk.CSS + PAGE_CSS)}</style></head><body><main class="solo">{cover}{detail}{more}'
        '<p class="foot">Every figure is computed in code from the exports named, and every level comes from a rule in references/rules.md. '
        "This read is about the team, not a project: it writes nothing into a Landing Loop project file.</p></main></body></html>\n"
    )
