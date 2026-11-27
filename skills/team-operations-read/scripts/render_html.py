"""The read as one self-contained HTML page, in the Leader Report style guide.

The page takes the report's whole stylesheet from its template (assets/vendor/template.html, vendored
byte-identical at a pinned commit), so it is the same brand family as the deck and the Landing Loop pages.
Only a few rules for this page's layout are added. It follows the report's references/design.md: mono
capitals for labels, sans for sentences; hairlines, not boxes; grey for possible stages and ink for the
read; brass only for a person's call (who decides the start-here step, and the re-check date).

A team read has no bet status, so the page uses no status colour. landed, watch and stalled are a bet's
words and only did-it-land sets them. This page prints stages, ranges and "not read".

Nothing is loaded from the network, nothing in the output depends on the clock or the machine, and every
piece of text from an export is escaped.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from framework import DIMENSION_IDS, FUNCTIONS
from rules import describe

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "vendor" / "template.html"
STYLE = re.compile(r"<style>(.*?)</style>", re.S)

# Layout for this page only. Everything else comes from the template's stylesheet.
PAGE_CSS = """
main.solo{margin-left:0}
.solo .slide{min-height:0}
.solo .slide.cover{padding-top:72px;padding-bottom:40px}
.solo .lede{margin-bottom:8px}
.head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:10px 24px}
.head h2{margin-bottom:12px}
.rdw{font:400 10px/16px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t1);white-space:nowrap}
.rdw.none{color:var(--t3)}
@media (min-width:981px){.sc-h,.sc-r{grid-template-columns:minmax(0,1.1fr) minmax(0,1fr) 150px}}
.sb{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;max-width:240px}
.sb i{display:block;font:400 9.5px/16px var(--mono);font-style:normal;text-align:center;color:var(--t3);border:1px solid var(--line);border-radius:2px}
.sb i.in{border-color:var(--t2);color:var(--t1)}
.sb i.at{background:var(--t1);border-color:var(--t1);color:var(--bg)}
.sb.conflict i.in{background:repeating-linear-gradient(135deg,var(--line3) 0 3px,transparent 3px 6px)}
.rows{margin-top:8px}
.rows>div{display:grid;grid-template-columns:168px minmax(0,1fr);gap:6px 36px;border-top:1px solid var(--line);padding:14px 0}
.rows>div>span:first-child{font:400 10px/22px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--t3)}
.rows>div>span:last-child{color:var(--t2);font-size:13.5px}
.rows .rule{font:400 10px/16px var(--mono);color:var(--t3);margin-left:8px;white-space:nowrap}
.rows .step{color:var(--t1)}
.solo .need{margin-top:24px}
.solo .need-r{margin-top:6px}
.need-r p{color:var(--t1);font-size:15px}
.need .who{color:var(--brass);font:400 11.5px/16px var(--mono);white-space:nowrap}
.need .when{color:var(--brass);font:400 11.5px/16px var(--mono);white-space:nowrap}
.need .who::before{content:"DECIDES";font-size:10px;letter-spacing:.1em;color:var(--t3);margin-right:6px}
.need .when::before{content:"RE-CHECK";font-size:10px;letter-spacing:.1em;color:var(--t3);margin-right:6px}
.nr td:first-child{white-space:nowrap}
.solo details{margin-top:14px}
.foot{max-width:1120px;margin:0 auto;padding:28px 40px 64px;color:var(--t3);font-size:12px}
@media (max-width:980px){.rows>div{grid-template-columns:1fr;gap:2px}.foot{padding:24px 16px 48px}.solo .slide.cover{padding-top:48px}}
"""

MARK = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">'
    '<rect x="2" y="13" width="3" height="7" fill="var(--agent)"/><rect x="7" y="10" width="3" height="10" fill="var(--agent)"/>'
    '<rect x="12" y="2" width="1.5" height="20" fill="var(--brass)"/><rect x="16" y="4" width="4" height="16" fill="var(--t1)"/></svg>'
)

LIMITS = [
    "It reads how work moves through the team, not whether what shipped worked. Pair it with outcome data before judging the team.",
    "Do not turn these figures into targets. A team pushed to cut review wait or reopens can hit the number and miss the point. Use them to pick where to look.",
    "The thresholds are Dacard v0.1 heuristics, not industry benchmarks. Treat each bound as a hypothesis to test with the team.",
    "Read a gap with the squad that owns it before acting. The slowest squads are where to ask questions, not who to blame.",
]


def e(text: Any) -> str:
    return html.escape(str(text), quote=True)


def stylesheet() -> str:
    """The report template's whole stylesheet, fonts included."""
    try:
        found = STYLE.search(TEMPLATE.read_text(encoding="utf-8"))
    except OSError:
        found = None
    return found.group(1) if found else ""


def band(d: dict) -> str:
    """Five cells, one per stage. Outlined: the stages the evidence leaves open. Filled: the one stage read."""
    if d["read"] == "not_read":
        return ""
    cells = []
    for st in range(1, 6):
        if d["read"] == "stage" and st == d["stage"]:
            cls = "at"
        elif d["read"] == "conflict":
            cls = "in" if st in (d["floor"], d["ceiling"]) else ""
        else:
            cls = "in" if d["floor"] <= st <= d["ceiling"] else ""
        cells.append(f'<i class="{cls}">{st}</i>' if cls else f"<i>{st}</i>")
    conflict = " conflict" if d["read"] == "conflict" else ""
    return f'<span class="sb{conflict}" role="img" aria-label="{e(describe(d))}">{"".join(cells)}</span>'


def read_word(d: dict) -> str:
    none = " none" if d["read"] == "not_read" else ""
    return f'<span class="rdw{none}">{e(describe(d))}</span>'


def evidence_line(d: dict, figs: dict) -> str:
    """The figure behind the binding bound, in mono, the value in ink."""
    bound = [f for f in d["findings"] if f["bound"]]
    if not bound:
        return ""
    ceilings = sorted((f for f in bound if f["bound"][0] == "ceiling"), key=lambda f: f["bound"][1])
    pick = (ceilings or bound)[0]
    f = figs.get(pick["figures"][0])
    if not f:
        return ""
    return f'<span class="sc-l">{e(f["label"])} <b>{e(f["display"])}</b></span>'


def meta(*items: str, illustrative: bool) -> str:
    spans = "".join(f"<span>{e(x)}</span>" for x in items)
    if illustrative:
        spans += '<span class="ill">Illustrative</span>'
    return f'<div class="meta">{spans}</div>'


def scorecard(doc: dict, read: list[dict]) -> str:
    figs = doc["figures"]
    rows = []
    for d in read:
        rows.append(
            f'<div class="sc-r"><div class="sc-n"><span><a href="#{e(d["id"])}">{e(d["name"])}</a></span>'
            f'<span class="sc-d">{e(d["function"])}. {e(d["question"])}</span></div>'
            f'<div class="sc-v">{band(d)}{evidence_line(d, figs)}</div><div class="sc-s">{read_word(d)}</div></div>'
        )
    head = '<div class="sc-h"><span>Dimension</span><span>Stages the evidence allows</span><span>Read</span></div>'
    return f'<div class="tablewrap sc">{head}{"".join(rows)}</div>'


def start_here(doc: dict) -> str:
    sh = doc["start_here"]
    ill = doc["illustrative"]
    if not sh:
        return (
            f'<section class="slide">{meta("Start here", illustrative=ill)}<h2>No dimension is bounded yet</h2>'
            '<p class="lede">The data is below every rule\'s minimum sample or inside every threshold. The quickest addition is squads.csv '
            "(one row per squad with its roles), then items.csv from your tracker.</p></section>"
        )
    f = doc["figures"].get(sh["recheck_figure"]) if sh["recheck_figure"] else None
    d = next(x for x in doc["dimensions"] if x["id"] == sh["dimension"])
    why = next((x["says"] for x in d["findings"] if x["bound"] and x["next_step"] == sh["next_step"]), "")
    rows = [("Why", why)] if why else []
    if f:
        rows.append(("Re-check", f"{f['label']}, now {f['display']}. Run this read again on {doc['recheck_on']} with the same window to see whether it moved."))
    body = "".join(f"<div><span>{e(k)}</span><span>{e(v)}</span></div>" for k, v in rows)
    who = f'<span class="who">{e(doc["decides"])}</span>' if doc["decides"] else "<span></span>"
    need = (
        f'<div class="need"><b>Start here</b><div class="need-r"><p>{e(sh["next_step"])}</p>{who}<span class="when">{e(doc["recheck_on"])}</span></div></div>'
    )
    return (
        f'<section class="slide">{meta("Start here", illustrative=ill)}<div class="head"><h2>{e(sh["name"])}</h2>{read_word(d)}</div>'
        f'{need}<div class="rows">{body}</div></section>'
    )


def dimension_section(doc: dict, d: dict) -> str:
    n = DIMENSION_IDS.index(d["id"]) + 1
    rows = []
    for f in d["findings"]:
        if f["bound"]:
            label = "Evidence"
        elif f.get("context"):
            label = "Context, not scored"
        else:
            label = "Not scored"
        rows.append((label, f'{e(f["says"])}<span class="rule">{e(f["rule"])}</span>'))
    if d["survey"]:
        rows.append(("Team view", e(d["survey"]["says"])))
    if d["survey_disagrees"]:
        rows.append(("Team view", e(d["survey_disagrees"])))
    rows.append(("Next step", f'<span class="step">{e(d["next_step"])}</span>'))
    body = "".join(f"<div><span>{e(k)}</span><span>{v}</span></div>" for k, v in rows)
    return (
        f'<section class="slide">{meta(d["function"], f"Dimension {n:02d} of 27", illustrative=doc["illustrative"])}'
        f'<div class="head"><h2 id="{e(d["id"])}">{e(d["name"])}</h2>{read_word(d)}</div>'
        f'<p class="lede">{e(d["question"])}</p>{band(d)}<div class="rows">{body}</div></section>'
    )


def not_read(doc: dict) -> str:
    rows = []
    for fn in FUNCTIONS:
        group = [d for d in doc["dimensions"] if d["read"] == "not_read" and d["function"] == fn]
        steps: dict[str, list[dict]] = {}
        for d in group:
            steps.setdefault(d["next_step"], []).append(d)
        for step, ds in steps.items():
            views = " ".join(f"{d['name']}: {d['survey']['says']}" for d in ds if d["survey"] and d["survey"]["shown"])
            rows.append(f"<tr><td>{e(fn)}</td><td>{e(', '.join(d['name'] for d in ds))}</td><td>{e(step)}{(' ' + e(views)) if views else ''}</td></tr>")
    head = "<tr><th>Function</th><th>Dimensions</th><th>What would read them</th></tr>"
    count = sum(1 for d in doc["dimensions"] if d["read"] == "not_read")
    return (
        f'<section class="slide">{meta("Not read", illustrative=doc["illustrative"])}<h2>{count} dimensions these exports cannot read</h2>'
        f'<div class="tablewrap"><table class="nr"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div></section>'
    )


def ledger(doc: dict) -> str:
    def row(f: dict) -> str:
        w = f"{f['window']['from']} to {f['window']['to']}"
        return (
            f'<tr><td>{e(f["label"])}</td><td class="num">{e(f["display"])}</td><td>{e(f["source"])}</td>'
            f'<td class="mo">{e(w)}</td><td class="mo">{e(f["as_of"])}</td><td class="num">{e(f["n"])}</td><td>{e(f["method"])}</td></tr>'
        )

    head = '<tr><th>Figure</th><th class="num">Value</th><th>Source</th><th>Window</th><th>As of</th><th class="num">Rows</th><th>Method</th></tr>'
    figs = list(doc["figures"].values())
    main_rows = [f for f in figs if ".squad." not in f["id"]]
    squad_rows = [f for f in figs if ".squad." in f["id"]]
    table = f'<div class="tablewrap"><table><thead>{head}</thead><tbody>{"".join(row(f) for f in main_rows)}</tbody></table></div>'
    if squad_rows:
        table += (
            f"<details><summary>Per-squad figures ({len(squad_rows)}), context only</summary>"
            f'<div class="tablewrap"><table><thead>{head}</thead><tbody>{"".join(row(f) for f in squad_rows)}</tbody></table></div></details>'
        )
    systems = ""
    if doc["systems"]:
        systems = (
            '<p class="asof" style="margin-top:14px">'
            + e("Where each file came from: " + "; ".join(f"{k}, {v}" for k, v in doc["systems"].items()) + ".")
            + "</p>"
        )
    return (
        f'<section class="slide">{meta("Evidence ledger", illustrative=doc["illustrative"])}<h2>Every figure, with its source</h2>'
        f'<p class="lede">Computed by scripts/metrics.py from the exports named. Nothing is estimated.</p>{table}{systems}</section>'
    )


def page(doc: dict) -> str:
    dims = doc["dimensions"]
    read = [d for d in dims if d["read"] != "not_read"]
    single = sum(1 for d in read if d["read"] == "stage")
    ill = doc["illustrative"]
    title = f"Team Operations read: {doc['company']}"
    ov = doc["overall"]
    if ov["claimed"]:
        overall = f"Overall: Stage {ov['stage']} ({ov['stage_name']}), {ov['total']} of 135."
    else:
        overall = "No overall stage: that needs a single-stage read on all 27 dimensions."
    lede = f"{len(read)} of 27 dimensions read from {len(doc['sources'])} exports over {doc['window']['days']} days, {single} to a single stage. {overall}"
    facts = [
        (f"{len(read)} of 27", "Dimensions read"),
        (str(single), "Single stage"),
        (f"{doc['window']['days']} days", "Window"),
        (str(len(doc["figures"])), "Figures, each sourced"),
    ]
    facts_html = "".join(f"<span><b>{e(v)}</b>{e(k)}</span>" for v, k in facts)
    cover_meta = meta(f"Read {doc['as_of']}", f"{doc['window']['start']} to {doc['window']['end']}", f"team-operations-read {doc['version']}", illustrative=ill)
    limits = "".join(f"<li>{e(x)}</li>" for x in LIMITS)
    return (
        '<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{e(title)}</title><style>{stylesheet()}{PAGE_CSS}</style></head><body><main class="solo">'
        f'<section class="slide cover"><div class="brand">{MARK}<span translate="no">DACARD</span></div>{cover_meta}'
        f'<h1>{e(title)}</h1><p class="lede">{e(lede)}</p><div class="facts">{facts_html}</div></section>'
        f"{start_here(doc)}"
        f'<section class="slide">{meta("Scorecard", illustrative=ill)}<h2>What the exports can read</h2>{scorecard(doc, read)}</section>'
        f"{''.join(dimension_section(doc, d) for d in read)}"
        f"{not_read(doc)}"
        f'<section class="slide">{meta("How to use this read", illustrative=ill)}<h2>Where to look, not a grade</h2>'
        f'<div class="card"><ul>{limits}</ul></div></section>'
        f"{ledger(doc)}"
        '<p class="foot">Every figure is computed in code from the exports named, and every stage comes from a rule in references/rules.md. '
        "This read is about the team, not a bet: it writes nothing into a Landing Loop record.</p></main></body></html>\n"
    )
