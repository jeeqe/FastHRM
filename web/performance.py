"""Performance renderers — goals/OKRs, continuous feedback, review cycles."""
from __future__ import annotations

from fasthtml.common import (
    Div, H3, H4, P, Span, A, Table, Thead, Tbody, Tr, Th, Td, Form, Input, Button,
    Select, Option, Textarea, Small, Strong, Label,
)

import db
import people
import talent
from web.layout import kpi_card
from web.i18n import current_lang, t_app
from web.views import _pill, _title

TONE = {"On track": "", "Complete": "ok", "At risk": "warn", "Behind": "danger",
        "Cancelled": "cancelled"}


def _c(key):
    return t_app(current_lang(), key)


def _bar(pct, status=""):
    cls = "bar" + (" danger" if status == "Behind" else " warn" if status == "At risk" else "")
    return Div(Span(style=f"width:{max(2, min(100, pct))}%;display:block;height:100%;"), cls=cls)


def _progress(g):
    pct = people.goal_progress(g)
    cls = "bar" + (" danger" if g["status"] == "Behind" else
                   " warn" if g["status"] == "At risk" else "")
    return Div(Div(style=f"width:{max(2, min(100, pct))}%", cls=""), cls=cls)


def _goal_bar(g):
    pct = people.goal_progress(g)
    tone = ("danger" if g["status"] == "Behind" else "warn" if g["status"] == "At risk" else "")
    inner = f'<i style="width:{max(2, min(100, pct))}%"></i>'
    from fasthtml.common import NotStr
    return Div(NotStr(inner), cls=f"bar {tone}".strip())


# ---------- goals -----------------------------------------------------------

def goals_page(period="All", status="All", owner_type="All"):
    k = people.performance_kpis()
    periods = people.goal_periods()
    gs = people.goals(period=period, status=status, owner_type=owner_type)

    seg = Div(A("All periods", href="/performance/goals", cls="active" if period == "All" else ""),
              *[A(p, href=f"/performance/goals?period={p}", cls="active" if period == p else "")
                for p in periods], cls="seg")
    seg2 = Div(*[A(s, href=f"/performance/goals?period={period}&status={s}",
                   cls="active" if status == s else "")
                 for s in ["All"] + people.GOAL_STATUSES], cls="seg")

    rows = []
    for g in gs:
        pct = people.goal_progress(g)
        rows.append(Div(
            Div(Div(A(g["title"], href=f"/performance/goals/{g['id']}"), cls="t"),
                Div(f"{g['owner_name'] or '—'} · {g['metric'] or 'no metric'}"
                    + (f" · {g['period']}" if g["period"] else ""), cls="m")),
            _goal_bar(g),
            Div(f"{pct}%", cls="score-cell", style="text-align:right;"),
            Div(_pill(g["status"], TONE.get(g["status"], "")), style="text-align:right;"),
            cls="goal-row"))

    return (_title(_c("perf_goals"), _c("perf_shown").format(n=len(gs))),
            Div(kpi_card(_c("perf_active_goals"), k["goals"], _c("perf_at_risk").format(n=k["at_risk"]),
                         tone="warn" if k["at_risk"] else ""),
                kpi_card(_c("perf_feedback_30d"), k["feedback_30d"], _c("perf_pieces")),
                kpi_card(_c("perf_open_cycles"), k["open_cycles"], f"{k['reviews_due']} {_c('perf_reviews_due').lower()}",
                         tone="danger" if k["reviews_due"] else ""),
                kpi_card(_c("perf_alignment"), sum(1 for g in gs if g["parent_goal_id"]),
                         _c("perf_linked")),
                cls="kpi-grid"),
            seg, seg2,
            Div(_new_goal_form(), cls="card"),
             Div(Div(H3(_c("perf_goals")), A(_c("perf_alignment_link"), href="/performance/alignment",
                                   cls="btn sm"), cls="card-header"),
                 Div(*rows) if rows else P(_c("perf_no_match"), style="color:var(--text-mute);"),
                cls="card"))


def _new_goal_form():
    emps = db.employees_min()
    depts = db.rows("SELECT id, name FROM departments ORDER BY name")
    parents = db.rows("""SELECT id, title FROM goals WHERE owner_type IN ('company','department')
                         ORDER BY owner_type, title""")
    return Div(
        Div(H3(_c("perf_add_goal")), cls="card-header"),
        Form(
            Input(name="title", placeholder=_c("perf_add_a_goal"), cls="hr-inp", required=True,
                  style="flex:2;min-width:200px;"),
            Select(Option("Company", value="company"), Option("Department", value="department"),
                   Option("Employee", value="employee", selected=True),
                   name="owner_type", cls="hr-inp"),
            Select(Option("— owner —", value="0"),
                   *[Option(f"{e['first_name']} {e['last_name']}", value=f"e{e['id']}")
                     for e in emps],
                   *[Option(d["name"], value=f"d{d['id']}") for d in depts],
                   name="owner", cls="hr-inp"),
            Select(Option("— no parent —", value="0"),
                   *[Option(p["title"][:40], value=str(p["id"])) for p in parents],
                   name="parent_goal_id", cls="hr-inp"),
            Input(name="metric", placeholder="Metric", cls="hr-inp", style="min-width:130px;"),
            Input(name="target", type="number", step="any", placeholder="Target", cls="hr-inp",
                  style="width:100px;"),
            Input(name="period", placeholder="2026-Q3", cls="hr-inp", value="2026-Q3",
                  style="width:110px;"),
             Button(_c("perf_add_goal"), cls="btn primary", type="submit"),
            method="post", action="/performance/goals",
            cls="inline-form", style="flex-wrap:wrap;gap:8px;"))


def goal_detail(goal_id: int):
    g = people.goal(goal_id)
    if not g:
        return _title(_c("perf_goal_not_found")), P(_c("perf_no_goal"))
    pct = people.goal_progress(g)
    history = people.checkins(goal_id)
    children = people.goals()
    kids = [c for c in children if c["parent_goal_id"] == goal_id]

    info = Div(Div(H3(_c("perf_goals")), _pill(g["status"], TONE.get(g["status"], "")), cls="card-header"),
               Div(Span("Owner", cls="k"), Span(g.get("owner_name") or g["owner_type"]),
                   Span("Metric", cls="k"), Span(g["metric"] or "—"),
                   Span(_c("perf_target"), cls="k"), Span(f"{g['target'] or 0:g} {g['unit'] or ''}".strip()),
                   Span(_c("perf_current"), cls="k"), Span(f"{g['current'] or 0:g}"),
                   Span(_c("perf_period"), cls="k"), Span(g["period"] or "—"),
                   Span(_c("perf_due"), cls="k"), Span(g["due_date"] or "—"),
                   Span(_c("perf_parent"), cls="k"), Span(g["parent_title"] or "— top level"),
                   cls="kv"),
               Div(_goal_bar(g), style="margin-top:12px;"),
                P(_c("perf_of_target").format(n=pct), style="color:var(--text-mute);font-size:12px;margin:6px 0 0;"),
               cls="card")

    form = Div(Div(H3(_c("perf_checkin")), cls="card-header"),
                Form(Input(name="value", type="number", step="any", placeholder=_c("perf_current_value"),
                          cls="hr-inp", required=True, style="width:140px;"),
                    Select(*[Option(s, value=s, selected=(s == g["status"]))
                             for s in people.GOAL_STATUSES], name="status", cls="hr-inp"),
                     Input(name="note", placeholder=_c("perf_changed"), cls="hr-inp", style="flex:1;"),
                     Button(_c("perf_save_checkin"), cls="btn primary", type="submit"),
                    **{"hx-post": f"/performance/goals/{goal_id}/checkin",
                       "hx-target": "#goal-body", "hx-swap": "innerHTML"},
                    cls="inline-form", style="flex-wrap:wrap;gap:8px;"), cls="card")

    hist = Div(Div(H3(_c("perf_checkin_history")), cls="card-header"),
               Table(Thead(Tr(Th(_c("perf_when")), Th(_c("perf_value"), cls="num"), Th(_c("perf_status")), Th(_c("perf_note")), Th(_c("perf_by")))),
                     Tbody(*[Tr(Td(Small(h["created"], style="color:var(--text-mute);")),
                                 Td(f"{h['value']:g}" if h["value"] is not None else "—", cls="num"),
                                 Td(_pill(h["status"] or "—", TONE.get(h["status"], ""))),
                                 Td(h["note"] or "—"), Td(Small(h["created_by"] or "—")))
                              for h in history] or [Tr(Td(_c("perf_no_checkins"), colspan="5"))]),
                     cls="tbl"), cls="card")

    kid_card = Div(Div(H3(_c("perf_contributing").format(n=len(kids))), cls="card-header"),
                   Div(*[Div(Div(Div(A(c["title"], href=f"/performance/goals/{c['id']}"), cls="t"),
                                 Div(c["owner_name"] or "—", cls="m")),
                             _goal_bar(c),
                             Div(f"{people.goal_progress(c)}%", cls="score-cell",
                                 style="text-align:right;"),
                             Div(_pill(c["status"], TONE.get(c["status"], "")),
                                 style="text-align:right;"),
                             cls="goal-row") for c in kids]
                        or [P(_c("perf_none_linked"), style="color:var(--text-mute);")]),
                   cls="card") if kids else None

    return (_title(g["title"], f"{g.get('owner_name') or ''} · {g['period'] or ''}".strip(" ·"),
                    A(_c("perf_goal_list"), href="/performance/goals", cls="btn")),
            Div(Div(form, hist, kid_card), Div(info), cls="detail-grid", id="goal-body"))


def goal_body(goal_id: int):
    """HTMX-swappable inner half after a check-in."""
    return goal_detail(goal_id)[1].children


def alignment_page(period="All"):
    tree = people.goal_tree(period if period != "All" else None)
    periods = people.goal_periods()
    seg = Div(A("All", href="/performance/alignment", cls="active" if period == "All" else ""),
              *[A(p, href=f"/performance/alignment?period={p}", cls="active" if period == p else "")
                for p in periods], cls="seg")

    def render(nodes, depth=0):
        out = []
        for n in nodes:
            out.append(Div(
                Div(Div(Div(A(n["title"], href=f"/performance/goals/{n['id']}"), cls="t"),
                        Div(f"{n['owner_name'] or '—'} · {n['metric'] or 'no metric'}", cls="m")),
                    _goal_bar(n),
                    Div(f"{people.goal_progress(n)}%", cls="score-cell", style="text-align:right;"),
                    Div(_pill(n["status"], TONE.get(n["status"], "")), style="text-align:right;"),
                    cls="goal-row"),
                Div(*render(n["children"], depth + 1), cls="kid") if n["children"] else None))
        return out

    return (_title(_c("perf_goal_alignment"),
                   "How individual goals ladder up to team and company objectives"),
            seg,
             Div(Div(H3(_c("perf_cascade")), A(_c("perf_goal_list"), href="/performance/goals", cls="btn sm"),
                    cls="card-header"),
                Div(*render(tree), cls="goal-tree") if tree
                 else P(_c("perf_no_goals"), style="color:var(--text-mute);"), cls="card"))


# ---------- feedback --------------------------------------------------------

def feedback_page(kind="All"):
    items = people.feedback_feed(kind=kind)
    seg = Div(*[A(k, href=f"/performance/feedback?kind={k}", cls="active" if kind == k else "")
                for k in ["All"] + people.FEEDBACK_KINDS], cls="seg")
    emps = db.employees_min()
    comps = talent.competencies()

    form = Div(Div(H3(_c("perf_give_feedback")), cls="card-header"),
               Form(Select(Option("— from —", value="0"),
                           *[Option(f"{e['first_name']} {e['last_name']}", value=str(e["id"]))
                             for e in emps], name="from_employee_id", cls="hr-inp"),
                    Select(*[Option(f"{e['first_name']} {e['last_name']}", value=str(e["id"]))
                             for e in emps], name="to_employee_id", cls="hr-inp"),
                    Select(*[Option(k, value=k) for k in people.FEEDBACK_KINDS],
                           name="kind", cls="hr-inp"),
                    Select(Option("— competency —", value="0"),
                           *[Option(c["name"], value=str(c["id"])) for c in comps],
                           name="competency_id", cls="hr-inp"),
                    Select(*[Option(v, value=v) for v in people.VISIBILITIES],
                           name="visibility", cls="hr-inp"),
                    Input(name="body", placeholder="What did they do well, or differently?",
                          cls="hr-inp", required=True, style="flex:1;min-width:220px;"),
                     Button(_c("perf_post"), cls="btn primary", type="submit"),
                    **{"hx-post": "/performance/feedback", "hx-target": "#feed",
                       "hx-swap": "innerHTML"},
                    cls="inline-form", style="flex-wrap:wrap;gap:8px;"), cls="card")

    return (_title(_c("perf_feedback"), f"{len(items)} entries — {_c('perf_feedback_subtitle')}"),
            form, seg, Div(feed_list(kind), id="feed"))


def feed_list(kind="All"):
    items = people.feedback_feed(kind=kind)
    return Div(Div(H3(_c("perf_recent_feedback")), cls="card-header"),
               *[Div(Div(f"{i['from_name'] or 'Anonymous'} → ",
                         A(i["to_name"], href=f"/employees/{i['to_id']}"),
                         Span(f" · {i['created'][:16]}", style="color:var(--text-mute);"),
                         cls="who"),
                     Div(i["body"], cls="body"),
                     Div(_pill(i["kind"]),
                         _pill(i["competency"]) if i["competency"] else None,
                         _pill(i["visibility"]),
                         style="margin-top:6px;display:flex;gap:5px;flex-wrap:wrap;"),
                     cls="feed-item")
                  for i in items] or [P(_c("perf_no_feedback"), style="color:var(--text-mute);")],
               cls="card")


# ---------- review cycles ---------------------------------------------------

def reviews_page():
    cs = people.cycles()
    k = people.performance_kpis()
    tbl = Table(Thead(Tr(Th(_c("perf_cycle")), Th(_c("perf_period")), Th(_c("perf_reviews"), cls="num"),
                         Th(_c("perf_submitted"), cls="num"), Th(_c("perf_progress")), Th(_c("perf_status")), Th(""))),
                Tbody(*[Tr(Td(A(Strong(c["name"]), href=f"/performance/reviews/{c['id']}")),
                           Td(f"{c['period_start']} → {c['period_end']}",
                              style="white-space:nowrap;color:var(--text-mute);"),
                           Td(str(c["n_reviews"]), cls="num"),
                           Td(str(c["n_done"]), cls="num"),
                           Td(_bar(round(100 * c["n_done"] / c["n_reviews"]) if c["n_reviews"] else 0)),
                           Td(_pill(c["status"])),
                            Td(Button(_c("perf_open_cycle"), cls="btn sm primary",
                                     **{"hx-post": f"/performance/reviews/{c['id']}/status?status=Open",
                                        "hx-target": "#cycles", "hx-swap": "innerHTML"})
                              if c["status"] == "Draft" else
                               Button(_c("perf_calibrate"), cls="btn sm",
                                     **{"hx-post": f"/performance/reviews/{c['id']}/status?status=Calibration",
                                        "hx-target": "#cycles", "hx-swap": "innerHTML"})
                              if c["status"] == "Open" else Span("—", style="color:var(--text-mute);")))
                         for c in cs] or [Tr(Td(_c("perf_no_cycles"), colspan="7"))]), cls="tbl")

    form = Div(Div(H3(_c("perf_new_cycle")), cls="card-header"),
               Form(Input(name="name", placeholder="e.g. 2026 H2 review", cls="hr-inp",
                          required=True, style="flex:1;min-width:180px;"),
                    Input(type="date", name="period_start", cls="hr-inp", required=True, aria_label="Perioodi algus"),
                    Input(type="date", name="period_end", cls="hr-inp", required=True, aria_label="Perioodi lõpp"),
                     Button(_c("perf_create"), cls="btn primary", type="submit"),
                    method="post", action="/performance/reviews",
                    cls="inline-form", style="flex-wrap:wrap;gap:8px;"), cls="card")

    return (_title(_c("perf_cycles"), _c("perf_cycle_subtitle")),
            Div(kpi_card(_c("perf_open_cycles"), k["open_cycles"]),
                kpi_card(_c("perf_reviews_due"), k["reviews_due"], _c("perf_not_submitted"),
                         tone="danger" if k["reviews_due"] else ""),
                kpi_card(_c("perf_active_goals"), k["goals"]),
                kpi_card(_c("perf_feedback_30d"), k["feedback_30d"]),
                cls="kpi-grid"),
            form, Div(Div(Div(H3(_c("perf_cycles")), cls="card-header"), tbl, cls="card"), id="cycles"))


def cycles_fragment():
    return reviews_page()[3].children[0]


def cycle_detail(cycle_id: int, status="All"):
    c = people.cycle(cycle_id)
    if not c:
        return _title(_c("perf_cycle_not_found")), P(_c("perf_no_cycle"))
    rs = people.reviews_in(cycle_id, status)
    grid = people.calibration_grid(cycle_id)
    dist = people.rating_distribution(cycle_id)

    seg = Div(*[A(s, href=f"/performance/reviews/{cycle_id}?status={s}",
                  cls="active" if status == s else "")
                for s in ["All"] + people.REVIEW_STATUSES], cls="seg")

    tbl = Table(Thead(Tr(Th(_c("perf_employee")), Th(_c("perf_department")), Th(_c("perf_kind")), Th(_c("perf_reviewer")),
                         Th(_c("perf_overall"), cls="num"), Th(_c("perf_status")), Th(""))),
                Tbody(*[Tr(Td(r["employee"]), Td(r["dept"] or "—"), Td(_pill(r["kind"])),
                           Td(r["reviewer"] or "—"),
                           Td(f"{r['overall']:.1f}" if r["overall"] else "—", cls="num"),
                           Td(_pill(r["status"])),
                           Td(A("Complete", href=f"/performance/reviews/{cycle_id}/{r['id']}",
                                cls="btn sm") if r["status"] != "Submitted"
                              else Span("—", style="color:var(--text-mute);")))
                        for r in rs] or [Tr(Td(_c("perf_no_reviews"), colspan="7"))]), cls="tbl")

    cal = Div(Div(H3(_c("perf_calibration")), cls="card-header"),
              Table(Thead(Tr(Th(_c("perf_department")), Th(_c("perf_reviews"), cls="num"), Th(_c("perf_average"), cls="num"),
                             Th(_c("perf_range"), cls="num"))),
                    Tbody(*[Tr(Td(g["dept"] or "—"), Td(str(g["n"]), cls="num"),
                               Td(Strong(f"{g['avg_score']:.2f}"), cls="num"),
                               Td(f"{g['lo']:.1f} – {g['hi']:.1f}", cls="num"))
                            for g in grid] or [Tr(Td(_c("perf_nothing_submitted"), colspan="4"))]),
                    cls="tbl"), cls="card")

    mx = max((d["n"] for d in dist), default=1) or 1
    distro = Div(Div(H3(_c("perf_rating")), cls="card-header"),
                 *[Div(Div(f"{d['band']} ★", style="color:var(--text-dim);"),
                       Div(Div(cls="funnel-bar", style=f"width:{max(2, 100 * d['n'] / mx):.0f}%;")),
                       Div(str(d["n"]), cls="v"), cls="funnel-row") for d in dist]
                  or [P(_c("perf_nothing_submitted"), style="color:var(--text-mute);")], cls="card")

    return (_title(c["name"], f"{c['period_start']} → {c['period_end']} · {c['status']}",
                   A("← Cycles", href="/performance/reviews", cls="btn")),
            seg,
            Div(Div(Div(H3(f"Reviews ({len(rs)})"), cls="card-header"), tbl, cls="card"),
                Div(cal, distro), cls="detail-grid"))


def review_form(cycle_id: int, review_id: int):
    r = db.one("""SELECT r.*, e.first_name||' '||e.last_name employee, e.designation,
                         rv.first_name||' '||rv.last_name reviewer
                  FROM reviews r JOIN employees e ON e.id=r.employee_id
                  LEFT JOIN employees rv ON rv.id=r.reviewer_id WHERE r.id=?""", (review_id,))
    if not r:
        return _title(_c("perf_review_not_found")), P(_c("perf_no_such_review"))
    comps = talent.competencies()
    return (_title(f"{r['kind']} review — {r['employee']}", r["designation"] or "",
                   A("← Cycle", href=f"/performance/reviews/{cycle_id}", cls="btn")),
             Div(Div(H3(_c("perf_review")), cls="card-header"),
                Form(
                    *[Div(Label(c["name"], style="font-size:13px;font-weight:600;"),
                          Small(f" — {c['description'] or c['category']}",
                                style="color:var(--text-mute);"),
                          Select(*[Option(f"{i} — {lbl}", value=str(i)) for i, lbl in
                                     ((5, _c("perf_outstanding")), (4, _c("perf_exceeds")), (3, _c("perf_meets")),
                                      (2, _c("perf_developing")), (1, _c("perf_below")))],
                                 name=f"comp_{c['id']}", cls="hr-inp",
                                 style="margin-left:10px;width:190px;"),
                          style="margin-bottom:10px;display:flex;align-items:center;"
                                "justify-content:space-between;gap:10px;")
                      for c in comps],
                    Div(Label(_c("perf_overall_summary"), style="font-size:13px;font-weight:600;"),
                        Textarea(name="narrative", cls="prompt-box",
                                 style="min-height:150px;margin-top:6px;",
                                 placeholder=_c("perf_review_prompt")),
                        style="margin-top:14px;"),
                    Button(_c("perf_submit_review"), cls="btn primary", type="submit",
                           style="margin-top:12px;"),
                    method="post", action=f"/performance/reviews/{cycle_id}/{review_id}"),
                cls="card"))


# ---------- signals ---------------------------------------------------------

def signals_page(dept="All"):
    depts = db.rows("SELECT name FROM departments ORDER BY name")
    seg = Div(A("All", href="/performance/signals", cls="active" if dept == "All" else ""),
              *[A(d["name"], href=f"/performance/signals?dept={d['name']}",
                  cls="active" if dept == d["name"] else "") for d in depts], cls="seg")
    risk = people.attrition_signals(None if dept == "All" else dept)
    ready = people.promotion_readiness()

    risk_card = Div(
        Div(H3(_c("perf_attrition")),
            Small(_c("perf_advisory"), style="color:var(--text-mute);"), cls="card-header"),
        P(_c("perf_signals_explanation"),
          style="color:var(--text-mute);font-size:12.5px;margin:0 0 12px;"),
        Table(Thead(Tr(Th(_c("perf_employee")), Th(_c("perf_department")),
                      Th(_c("perf_signal")), Th(_c("perf_why")))),
              Tbody(*[Tr(Td(A(r["name"], href=f"/employees/{r['id']}"),
                            Div(r["designation"] or "", style="font-size:11.5px;color:var(--text-mute);")),
                         Td(r["dept"] or "—"),
                         Td(Span(r["band"], cls="pill " + ("rejected" if r["band"] == "High" else "pending"))),
                         Td(Div(*[Div("• " + f, style="font-size:12px;color:var(--text-dim);")
                                  for f in r["factors"]])))
                      for r in risk] or [Tr(Td(_c("perf_no_signals"), colspan="4"))]),
              cls="tbl"), cls="card")

    ready_card = Div(
        Div(H3(_c("perf_readiness")), cls="card-header"),
        Table(Thead(Tr(Th(_c("perf_employee")), Th(_c("perf_department")),
                      Th(_c("perf_score"), cls="num"), Th(_c("perf_why")))),
              Tbody(*[Tr(Td(A(r["name"], href=f"/employees/{r['id']}")),
                         Td(r["dept"] or "—"),
                         Td(Strong(f"{r['score']:.1f}"), cls="num score-cell"),
                         Td(Div(*[Div("• " + f, style="font-size:12px;color:var(--text-dim);")
                                  for f in r["factors"]])))
                      for r in ready] or [Tr(Td("Not enough data yet.", colspan="4"))]),
              cls="tbl"), cls="card")

    return (_title(_c("perf_signals"),
                   "Explainable, advisory indicators — every score shows its working"),
            seg, risk_card, ready_card)
