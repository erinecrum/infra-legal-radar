"""Email delivery of the memo over SMTP, plus the HTML rendering of the body.

Standard library only for sending (smtplib + email); the `markdown` library
renders the analysed item sections. The HTML body is assembled with explicit
visual hierarchy — large verdict, distinct section headers, de-emphasized
(smaller, gray) appendix and footer — while reusing the shared structure helpers
in `radar.memo`, so the HTML email and the Markdown file stay in lock-step.

Credentials never appear here — they arrive via EmailConfig from the environment.
"""

from __future__ import annotations

import html as _html
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Dict, List

import markdown as _markdown

from . import memo as _memo
from .config import EmailConfig

_SUBJECT_PREFIX = "Infra Legal Radar"

_STYLE = """
  body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         line-height: 1.5; color: #1a1a1a; max-width: 760px; margin: 0 auto; padding: 16px; }
  h1.title { font-size: 15px; color: #888; font-weight: 600; letter-spacing: .03em;
             text-transform: uppercase; margin: 0 0 12px; }
  .verdict { font-size: 23px; font-weight: 700; line-height: 1.3; margin: 2px 0 12px; }
  .verdict.urgent { color: #b00020; }
  .verdict.review { color: #9a6700; }
  .verdict.quiet  { color: #1a7f37; }
  .triage { font-size: 14px; margin: 0 0 4px; }
  .watching { font-size: 12px; color: #888; font-style: italic; margin: 0 0 8px; }
  hr { border: none; border-top: 1px solid #e6e6e6; margin: 22px 0; }
  .content h2 { font-size: 17px; margin: 26px 0 8px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
  .content h3 { font-size: 15px; margin: 20px 0 6px; }
  .content blockquote { border-left: 3px solid #ccc; margin: 8px 0; padding: 2px 12px; color: #444; }
  .content code { background: #f2f2f2; padding: 1px 4px; border-radius: 3px; }
  .content ul { padding-left: 22px; }
  .appendix { color: #6a6a6a; font-size: 13px; }
  .appendix h2 { font-size: 14px; color: #6a6a6a; text-transform: uppercase; letter-spacing: .03em;
                 border: none; margin: 4px 0 8px; }
  .appendix h3 { font-size: 13px; color: #6a6a6a; margin: 12px 0 4px; }
  .appendix .muted { color: #999; font-style: italic; margin: 0 0 8px; }
  table.appendix-table { border-collapse: collapse; width: 100%; font-size: 12px; margin: 4px 0; }
  table.appendix-table th, table.appendix-table td { border: 1px solid #e0e0e0; padding: 5px 9px; text-align: left; }
  table.appendix-table th { background: #f7f7f7; color: #555; font-weight: 600; }
  .run { font-size: 13px; color: #555; }
  .run h2 { font-size: 13px; color: #888; text-transform: uppercase; letter-spacing: .03em; margin: 4px 0 6px; }
  .footer { margin-top: 26px; padding-top: 12px; border-top: 1px solid #eee;
            font-size: 11px; color: #9a9a9a; line-height: 1.45; }
"""

# Split head/tail so the CSS braces in _STYLE aren't treated as format fields.
_HTML_HEAD = (
    "<!doctype html><html><head><meta charset=\"utf-8\"><style>"
    + _STYLE
    + "</style></head><body>\n"
)
_HTML_TAIL = "\n</body></html>"


def build_subject(
    items: List[Dict[str, Any]], out_of_region_events: List[Dict[str, Any]] = None
) -> str:
    """Summarize triage counts. Only URGENT/REVIEW are 'material'.
    'Infra Legal Radar: 1 URGENT, 3 REVIEW' / 'Infra Legal Radar: all quiet'."""
    t = _memo.triage_split(items)
    parts = []
    if t["urgent"]:
        parts.append(f"{len(t['urgent'])} URGENT")
    if t["review"]:
        parts.append(f"{len(t['review'])} REVIEW")
    summary = ", ".join(parts) if parts else "all quiet"
    subject = f"{_SUBJECT_PREFIX}: {summary}"
    if t["failed"]:
        n = len(t["failed"])
        subject += f" (+{n} error{'s' if n != 1 else ''})"
    return subject


def _md_to_html(lines: List[str]) -> str:
    return _markdown.markdown(
        "\n".join(lines), extensions=["extra", "sane_lists", "nl2br"]
    )


def render_html(
    items: List[Dict[str, Any]],
    *,
    run_time: datetime,
    watchlist,
    detection: Dict[str, Any],
    out_of_region_events: List[Dict[str, Any]] = None,
) -> str:
    out_of_region_events = out_of_region_events or []
    t = _memo.triage_split(items)
    urgent, review, noise, failed = t["urgent"], t["review"], t["noise"], t["failed"]
    verdict, severity = _memo.build_verdict(items)

    p: List[str] = []
    p.append('<h1 class="title">Infrastructure Legal Event Radar</h1>')
    p.append(f'<div class="verdict {severity}">{_html.escape(verdict)}</div>')

    triage = (
        f"{len(urgent)} URGENT &middot; {len(review)} REVIEW &middot; {len(noise)} NOISE"
        + (f" &middot; {len(failed)} error(s)" if failed else "")
        + (
            f" &middot; {len(out_of_region_events)} out-of-region"
            if out_of_region_events
            else ""
        )
    )
    p.append(f'<div class="triage"><strong>Triage:</strong> {triage}</div>')
    p.append(f'<div class="watching">{_html.escape(_memo.human_watchlist(watchlist))}</div>')

    # Analysed item sections (reuse the Markdown item renderer, convert to HTML).
    content: List[str] = []
    n = 1
    if urgent:
        content.append("## 🔴 URGENT — deadline within 30 days or active exposure")
        content.append("")
        for it in urgent:
            content += _memo._render_item(it, n)
            n += 1
    if review:
        content.append("## 🟡 REVIEW — material, no immediate deadline")
        content.append("")
        for it in review:
            content += _memo._render_item(it, n)
            n += 1
    if failed:
        content.append("## ⚠️ Translation errors")
        content.append("")
        for it in failed:
            content += _memo._render_error(it, n)
            n += 1
    if content:
        p.append("<hr>")
        p.append(f'<div class="content">{_md_to_html(content)}</div>')

    # Appendix — de-emphasized.
    if noise or out_of_region_events:
        p.append("<hr>")
        p.append('<div class="appendix">')
        p.append("<h2>Appendix</h2>")
        if noise:
            noise_md: List[str] = []
            for it in noise:
                noise_md += _memo._render_item(it, n)
                n += 1
            p.append(_md_to_html(noise_md))
        if out_of_region_events:
            p.append("<h3>Out-of-region operational events</h3>")
            p.append(
                '<p class="muted">Not analyzed — these affect AWS regions outside '
                "your watchlist. Listed for awareness; confirm you have no footprint "
                "there.</p>"
            )
            p.append('<table class="appendix-table">')
            p.append("<tr><th>Region</th><th>Event</th><th>Started</th><th>Status</th></tr>")
            for region, event, started, status in _memo.appendix_rows(out_of_region_events):
                cells = "".join(
                    f"<td>{_html.escape(str(c))}</td>"
                    for c in (region, event, started, status)
                )
                p.append(f"<tr>{cells}</tr>")
            p.append("</table>")
        p.append("</div>")

    # Run summary.
    p.append("<hr>")
    p.append('<div class="run"><h2>Run</h2>')
    collapsed, lines = _memo.run_summary_lines(detection)
    if collapsed:
        p.append(f"<p>{_html.escape(lines[0])}</p>")
    else:
        p.append("<ul>" + "".join(f"<li>{_html.escape(ln)}</li>" for ln in lines) + "</ul>")
    p.append("</div>")

    # Footer: disclaimer + timestamp, small print.
    p.append(
        '<div class="footer"><p>'
        + _html.escape(_memo.DISCLAIMER)
        + "</p><p>Run: "
        + run_time.strftime("%Y-%m-%d %H:%M UTC")
        + " &middot; Full memo attached as Markdown.</p></div>"
    )

    return _HTML_HEAD + "\n".join(p) + _HTML_TAIL


def send_memo_email(
    cfg: EmailConfig,
    *,
    subject: str,
    html_body: str,
    memo_markdown: str,
    attachment_name: str,
) -> None:
    """Send the memo: HTML body + plain-text (Markdown) fallback + attachment.
    Raises on failure so the caller can report it."""
    missing = cfg.missing_credentials()
    if missing:
        raise RuntimeError(
            "Email not sent — missing credential(s): "
            + ", ".join(missing)
            + ". Set them in .env (local) or GitHub Actions secrets (CI)."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.from_addr
    msg["To"] = cfg.to
    msg.set_content(memo_markdown)  # plain-text fallback (already readable)
    msg.add_alternative(html_body, subtype="html")
    msg.add_attachment(
        memo_markdown.encode("utf-8"),
        maintype="text",
        subtype="markdown",
        filename=attachment_name,
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as server:
        server.starttls(context=context)
        server.login(cfg.username, cfg.password)
        server.send_message(msg)
