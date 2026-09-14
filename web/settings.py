"""Settings → Integrations: connect job boards, social, calendar and e-sign.

API keys are encrypted before storage and only ever rendered back as a masked
hint. The form treats a blank secret field as "leave unchanged", so re-saving
does not require retyping a key you cannot see.
"""
from __future__ import annotations

from fasthtml.common import (
    Div, H3, H4, P, Span, A, Table, Thead, Tbody, Tr, Th, Td, Form, Input, Button,
    Select, Option, Label, Small, Strong, Details, Summary, NotStr,
)

import integrations
from web.layout import kpi_card, NAV_ITEMS
from web.i18n import current_lang, t_app
from web.views import _pill, _title
from web.rbac import MODULES, permissions_for


def _c(key):
    return t_app(current_lang(), key)

STATUS_TONE = {"Connected": "ok", "Error": "error", "Disabled": "cancelled",
               "Not configured": ""}


def _status_pill(status):
    return Span(status, cls="pill " + (STATUS_TONE.get(status) or "").lower())


def _card(i):
    cls = "int-card" + (" on" if i["status"] == "Connected" else
                        " err" if i["status"] == "Error" else "")
    key_line = (Span(i["key_hint"], cls="int-key") if i["key_hint"]
                else Small(_c("settings_no_key"), style="color:var(--text-mute);"))
    tested = None
    if i["last_test_at"]:
        tested = Div(("✓ " if i["last_test_ok"] else "✕ ") + (i["last_test_note"] or ""),
                     cls="int-meta",
                     style="color:var(--danger);" if not i["last_test_ok"] else "")
    return Div(
        Div(Div(Span(i["label"], cls="nm"),
                Div(integrations.CATEGORY_LABELS.get(i["category"], i["category"]),
                    cls="int-meta")),
            _status_pill(i["status"]), cls="int-head"),
        P(i["blurb"], cls="int-blurb"),
        Div(key_line, style="margin:2px 0;"),
        tested,
        Div(A(_c("settings_configure"), href=f"/settings/integrations/{i['provider']}", cls="btn sm primary"),
            Button(_c("settings_test"), cls="btn sm",
                   **{"hx-post": f"/settings/integrations/{i['provider']}/test",
                      "hx-target": "#int-grid", "hx-swap": "innerHTML"}) if i["key_hint"] else None,
            Button(_c("settings_sync"), cls="btn sm",
                   **{"hx-post": f"/settings/integrations/{i['provider']}/sync",
                      "hx-target": "#int-grid", "hx-swap": "innerHTML"})
            if i["status"] == "Connected" else None,
            cls="int-actions"),
        cls=cls)


def integrations_grid():
    grouped = integrations.by_category()
    blocks = []
    for cat in integrations.CATEGORIES:
        items = grouped.get(cat) or []
        if not items:
            continue
        blocks.append(Div(H4(integrations.CATEGORY_LABELS.get(cat, cat),
                             style="margin:18px 0 10px;font-size:12px;text-transform:uppercase;"
                                   "letter-spacing:.8px;color:var(--text-mute);"),
                          Div(*[_card(i) for i in items], cls="int-grid")))
    return Div(*blocks)


def integrations_page(saved: str = ""):
    lang = current_lang()
    c = lambda key: t_app(lang, key)
    k = integrations.kpis()
    banner = P(saved, cls="flag",
               style="border-left-color:var(--accent);background:var(--accent-light);"
                     "color:var(--accent-hover);") if saved else None
    return (
        _title(c("settings_integrations"), c("settings_connect_subtitle")),
        banner,
        Div(kpi_card(c("settings_connected"), k["connected"], c("settings_available").format(n=k["total"])),
            kpi_card(c("settings_attention"), k["error"], c("settings_failed_test"),
                     tone="danger" if k["error"] else ""),
            kpi_card(c("settings_not_configured"), k["unconfigured"], c("settings_no_credentials")),
            kpi_card(c("settings_providers"), k["total"], c("settings_categories")),
            cls="kpi-grid"),
        P(NotStr(c("settings_encryption_notice")),
          style="color:var(--text-mute);font-size:12.5px;margin:-4px 0 14px;"),
        Div(integrations_grid(), id="int-grid"),
        Div(Div(H3(c("settings_recent_activity")), cls="card-header"),
            _event_table(integrations.events(limit=15)), cls="card", style="margin-top:20px;"),
    )


ROLES = ["admin", "hrbp", "recruiter", "hiring_manager", "manager", "employee"]
ROLE_BLURB = {
    "admin": {"et": "Kõik, sealhulgas integratsioonid ja rollid.", "en": "Everything, including integrations and roles."},
    "hrbp": {"et": "Kõik inimeste andmed, juhtumid, tulemuslikkus ja elutsükkel.", "en": "All people data, cases, performance and lifecycle."},
    "recruiter": {"et": "Vabad ametikohad, kandidaadid, intervjuud ja pakkumised.", "en": "Requisitions, candidates, interviews and offers."},
    "hiring_manager": {"et": "Kandidaadid tema ametikohtadele ja tema meeskond.", "en": "Candidates on their own requisitions, and their team."},
    "manager": {"et": "Tema otsesed alluvad: eesmärgid, tagasiside, puhkus ja hindamised.", "en": "Their direct reports: goals, feedback, leave and reviews."},
    "employee": {"et": "Ainult tema enda kirje.", "en": "Their own record only."},
}


ROLE_LABELS = {
    "admin": {"et": "Administraator", "en": "Administrator"},
    "hrbp": {"et": "HR-partner", "en": "HRBP"},
    "recruiter": {"et": "Värbaja", "en": "Recruiter"},
    "hiring_manager": {"et": "Värbamisjuht", "en": "Hiring manager"},
    "manager": {"et": "Juht", "en": "Manager"},
    "employee": {"et": "Töötaja", "en": "Employee"},
}


def permissions_matrix():
    lang = current_lang()
    c = lambda key: t_app(lang, key)
    rows = []
    for role in ROLES:
        role_permissions = permissions_for({role})
        cells = []
        for key, label in MODULES:
            permission = role_permissions.get(key, {"view": False, "edit": False})
            cells.append(Td(
                Label(Input(type="checkbox", name=f"view_{role}_{key}", value="1",
                            checked=permission["view"]), c("rbac_view")),
                Label(Input(type="checkbox", name=f"edit_{role}_{key}", value="1",
                            checked=permission["edit"]), c("rbac_edit")),
                cls="rbac-cell"))
        rows.append(Tr(Td(Strong(ROLE_LABELS[role][lang])), *cells))
    headers = [Th(c("rbac_role"))] + [Th(label) for _key, label in MODULES]
    return Form(
        Table(Thead(Tr(*headers)), Tbody(*rows), cls="tbl rbac-table"),
        Div(Button(c("rbac_save"), cls="btn primary", type="submit"),
            P(c("rbac_unconfigured"), cls="int-meta")),
        method="post", action="/settings/roles/permissions")


def roles_page(saved: str = ""):
    lang = current_lang()
    c = lambda key: t_app(lang, key)
    import db
    assigned = db.rows("""SELECT r.*, e.first_name||' '||e.last_name employee
                          FROM account_roles r LEFT JOIN employees e ON e.id=r.employee_id
                          ORDER BY r.account_email, r.role""")
    emps = db.employees_min()
    banner = P(saved, cls="flag",
               style="border-left-color:var(--accent);background:var(--accent-light);"
                     "color:var(--accent-hover);") if saved else None

    tbl = Table(Thead(Tr(Th(c("settings_account")), Th(c("settings_role")), Th(c("settings_scope")), Th(c("settings_linked_employee")), Th(""))),
                Tbody(*[Tr(Td(r["account_email"]), Td(_pill(r["role"])), Td(_pill(r["scope"])),
                           Td(r["employee"] or "—"),
                           Td(Button(c("settings_remove"), cls="btn sm",
                                     **{"hx-post": f"/settings/roles/{r['id']}/delete",
                                        "hx-target": "#roles", "hx-swap": "innerHTML"})))
                        for r in assigned] or [Tr(Td(c("settings_no_roles"), colspan="5"))]),
                cls="tbl")

    form = Form(
        Input(name="account_email", type="email", placeholder="person@company.com",
              cls="hr-inp", required=True, style="min-width:220px;"),
        Select(*[Option(r, value=r) for r in ROLES], name="role", cls="hr-inp"),
        Select(Option(c("settings_all_data"), value="all"), Option(c("settings_own_department"), value="dept"),
               Option(c("settings_themselves"), value="self"), name="scope", cls="hr-inp"),
        Select(Option(c("settings_link_optional"), value="0"),
               *[Option(f"{e['first_name']} {e['last_name']}", value=str(e["id"])) for e in emps],
               name="employee_id", cls="hr-inp"),
        Button(c("settings_assign"), cls="btn primary", type="submit"),
        method="post", action="/settings/roles", cls="inline-form",
        style="flex-wrap:wrap;gap:8px;")

    return (_title(c("rbac_title"), c("rbac_subtitle")),
            banner,
            P(NotStr(c("settings_role_notice")),
              cls="flag"),
            Div(Div(H3(c("settings_assign_role")), cls="card-header"), form, cls="card"),
            Div(Div(Div(H3(c("settings_assigned_roles").format(n=len(assigned))), cls="card-header"), tbl,
                    cls="card"), id="roles"),
            Div(Div(H3(c("settings_role_purpose")), cls="card-header"),
                Table(Thead(Tr(Th(c("settings_role")), Th(c("settings_intended_access")))),
                      Tbody(*[Tr(Td(_pill(r)), Td(ROLE_BLURB[r][lang])) for r in ROLES]), cls="tbl"),
                cls="card"),
            Div(H3(c("rbac_permissions"), cls="card-header"),
                permissions_matrix(), cls="card"))


def roles_table():
    return roles_page()[4].children[0]


def _event_table(evts):
    lang = current_lang()
    c = lambda key: t_app(lang, key)
    return Table(Thead(Tr(Th(c("settings_when")), Th(c("settings_provider")), Th(c("settings_event")), Th(c("settings_result")), Th(c("settings_detail")))),
                 Tbody(*[Tr(Td(Small(e["created"], style="color:var(--text-mute);white-space:nowrap;")),
                            Td(integrations.provider_meta(e["provider"] or "")["label"]),
                            Td(_pill(e["kind"] or "—")),
                            Td(Span("OK" if e["ok"] else "Failed",
                                    cls="pill " + ("ok" if e["ok"] else "error"))),
                            Td(Small(e["detail"] or "—")))
                         for e in evts] or [Tr(Td("Nothing yet.", colspan="5"))]), cls="tbl")


def integration_detail(provider: str, note: str = ""):
    lang = current_lang()
    c = lambda key: t_app(lang, key)
    meta = integrations.provider_meta(provider)
    live = next((i for i in integrations.all_integrations() if i["provider"] == provider), None)
    if not live:
        return _title(c("settings_unknown")), P(c("settings_no_provider"))

    banner = None
    if note:
        ok = not note.lower().startswith(("no ", "failed", "stored credential"))
        banner = P(note, cls="flag",
                   style=("border-left-color:var(--accent);background:var(--accent-light);"
                          "color:var(--accent-hover);") if ok else "")

    secret_field = None
    if meta["secret_label"]:
        secret_field = Div(
            Label(meta["secret_label"], style="font-size:12px;color:var(--text-mute);"),
            Input(type="password", name="api_secret", cls="hr-inp", style="width:100%;",
                  placeholder=live["secret_hint"] or f"{_c('settings_enter')} {meta['secret_label'].lower()}",
                  autocomplete="new-password"),
            style="margin-bottom:12px;")

    form = Form(
        Div(Label(meta["key_label"], style="font-size:12px;color:var(--text-mute);"),
            Input(type="password", name="api_key", cls="hr-inp", style="width:100%;",
                  placeholder=live["key_hint"] or f"{_c('settings_enter')} {meta['key_label'].lower()}",
                  autocomplete="new-password"),
            style="margin-bottom:12px;"),
        secret_field,
        Div(Label(_c("settings_account_ref"),
                  style="font-size:12px;color:var(--text-mute);"),
            Input(name="account_ref", value=live["account_ref"], cls="hr-inp", style="width:100%;",
                  placeholder=_c("settings_account_ref_hint")),
            style="margin-bottom:12px;"),
        Div(Label(Input(type="checkbox", name="auto_sync", value="1",
                        checked=live["auto_sync"], style="margin-right:7px;"),
                  _c("settings_auto_sync"),
                  style="font-size:13px;display:flex;align-items:center;"),
            style="margin-bottom:14px;"),
        Div(Button(_c("settings_save_credentials"), cls="btn primary", type="submit"),
            Button(_c("settings_test"), cls="btn", type="submit", name="test", value="1"),
            style="display:flex;gap:8px;"),
        method="post", action=f"/settings/integrations/{provider}")

    danger = Form(
        Button(_c("settings_disconnect"), cls="btn", type="submit",
               style="color:var(--danger);border-color:var(--danger);"),
        method="post", action=f"/settings/integrations/{provider}/disconnect") if live["key_hint"] else None

    detail = Div(Div(H3(_c("settings_connection")), _status_pill(live["status"]), cls="card-header"),
                 Div(Span(_c("settings_provider_label"), cls="k"), Span(meta["label"]),
                     Span(_c("settings_category"), cls="k"),
                     Span(integrations.CATEGORY_LABELS.get(meta["category"], meta["category"])),
                     Span(meta["key_label"], cls="k"),
                     Span(Span(live["key_hint"], cls="int-key") if live["key_hint"] else "— not set"),
                     *([Span(meta["secret_label"], cls="k"),
                        Span(Span(live["secret_hint"], cls="int-key") if live["secret_hint"]
                             else "— not set")] if meta["secret_label"] else []),
                     Span(_c("settings_last_tested"), cls="k"), Span(live["last_test_at"] or _c("settings_never")),
                     Span(_c("settings_last_sync"), cls="k"), Span(live["last_sync_at"] or _c("settings_never")),
                     Span(_c("settings_auto"), cls="k"), Span(_c("settings_on") if live["auto_sync"] else _c("settings_off")),
                     cls="kv"),
                 P(live["last_test_note"], cls="int-meta",
                   style="margin-top:10px;") if live["last_test_note"] else None,
                 cls="card")

    return (_title(meta["label"], meta["blurb"],
                   A("← " + c("settings_integrations"), href="/settings/integrations", cls="btn")),
            banner,
            Div(Div(Div(Div(H3(c("settings_credentials")), cls="card-header"),
                        P(_c("settings_stored_hint"),
                          style="color:var(--text-mute);font-size:12.5px;margin:0 0 12px;"),
                        form,
                        Div(danger, style="margin-top:16px;padding-top:14px;"
                                          "border-top:1px solid var(--border);") if danger else None,
                        cls="card")),
                Div(detail,
                    Div(Div(H3(c("settings_activity")), cls="card-header"),
                        _event_table(integrations.events(provider, limit=12)), cls="card")),
                cls="detail-grid"))
