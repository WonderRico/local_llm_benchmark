#!/usr/bin/env python3
"""Render every .traj.json trajectory into one standalone HTML page (secrets redacted)."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import jinja2

REDACTED = "[redacted]"
SECRET_KEYS = ("api_key", "api_base", "authorization", "password", "secret", "token")
HTML_TRAJ_DIR = Path(__file__).parent / "html_traj"
TEMPLATE = jinja2.Environment(autoescape=True).from_string(
    (Path(__file__).parent / "template-traj.html").read_text(encoding="utf-8")
)

CSS = """
/* Same design language as the dashboards, which mirror desing-ref.html: near-black
   ground, one orange accent, hairline rules, mono uppercase apparatus labels.
   The reference ships dark only; the light theme is its counterpart - neutral paper,
   ink text, the same accent darkened to hold contrast. */
:root {
  --bg: #f5f4f1; --bg-alt: #fff; --bg-code: #efeeea; --fg: #17181a; --fg-dim: #6b6760;
  --border: rgba(23, 24, 26, .12); --border-strong: rgba(23, 24, 26, .55); --border-select: rgba(23, 24, 26, .3);
  --accent: #d8431c; --accent-eyebrow: #6b6760;
  --ok: #1f7a4d; --bad: #b3261e; --warn: #b4661d; --info: #0e7fbf;
  --atmos-line: rgba(23, 24, 26, .05); --atmos-line-2: rgba(23, 24, 26, .035); --grain: .035;
  --sans: "Archivo", "Helvetica Neue", "Segoe UI", system-ui, -apple-system, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
/* The dashboards own the `dashboard-theme` preference; these pages only read/obey it. */
:root[data-theme="dark"] {
  --bg: #0a0b0c; --bg-alt: #0e0f11; --bg-code: #101214; --fg: #eae7e0; --fg-dim: #9a968c;
  --border: rgba(234, 231, 224, .09); --border-strong: rgba(234, 231, 224, .34); --border-select: rgba(234, 231, 224, .2);
  --accent: #ff5a2b; --accent-eyebrow: #9a968c;
  --ok: #6cc38a; --bad: #ef7a6d; --warn: #e0a35c; --info: #63c8f5;
  --atmos-line: rgba(234, 231, 224, .04); --atmos-line-2: rgba(234, 231, 224, .028); --grain: .05;
}
::selection { background: var(--accent); color: var(--bg); }
/* Fixed atmosphere (the reference's hairline grid + film grain), behind the content. */
body::before { content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: linear-gradient(to right, var(--atmos-line) 1px, transparent 1px), linear-gradient(to bottom, var(--atmos-line-2) 1px, transparent 1px);
  background-size: 96px 96px;
  mask-image: radial-gradient(120% 100% at 50% 0%, #000 30%, transparent 92%);
  -webkit-mask-image: radial-gradient(120% 100% at 50% 0%, #000 30%, transparent 92%); }
body::after { content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: var(--grain);
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>"); }
#prog { position: fixed; top: 0; left: 0; height: 2px; width: 0; background: var(--accent); z-index: 100; transition: width .12s linear; }
.theme-toggle { position: absolute; top: 20px; right: 22px; background: none; color: var(--fg-dim);
  border: 1px solid var(--border-strong); border-radius: 2px; padding: 8px 12px; cursor: pointer;
  font-family: var(--mono); font-size: 10.5px; letter-spacing: .16em; text-transform: uppercase;
  transition: border-color .3s, color .3s; }
.theme-toggle:hover { border-color: var(--accent); color: var(--accent); }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.6 var(--sans); -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
.wrap { position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; padding: 0 20px 80px; }
header .wrap { padding-top: 76px; padding-bottom: 0; position: relative; }
h1 { font-family: var(--mono); font-weight: 500; font-size: clamp(18px, 2.4vw, 26px); letter-spacing: -.01em; margin: 0 0 8px; padding-right: 120px; overflow-wrap: anywhere; }
h1 code { color: var(--fg); }
.meta { font-family: var(--mono); color: var(--fg-dim); font-size: 11px; letter-spacing: .1em; overflow-wrap: anywhere; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.chip { border: 1px solid var(--border); background: none; border-radius: 2px; padding: 5px 9px; font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--fg-dim); }
.chip b { font-weight: 400; color: var(--fg); }
.ok { color: var(--ok); } .bad { color: var(--bad); } .warn { color: var(--warn); }
.nav { margin-top: 16px; font-family: var(--mono); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; display: flex; justify-content: space-between; gap: 12px; }
a { color: var(--fg); text-decoration: underline; text-decoration-color: var(--accent); text-underline-offset: 3px; transition: color .25s; }
a:hover { color: var(--accent); }
/* The reference's `.tick` label: mono, tracked, leading accent dash. */
h2 { font-family: var(--mono); font-weight: 400; font-size: 11px; text-transform: uppercase; letter-spacing: .22em; color: var(--accent-eyebrow); margin: 34px 0 12px; display: flex; align-items: center; gap: 10px; }
h2::before { content: ""; display: block; width: 14px; height: 1px; background: var(--accent); }
details { border: 1px solid var(--border); border-radius: 3px; background: var(--bg-alt); margin: 0; }
summary { cursor: pointer; padding: 10px 12px; font-size: 0.85rem; color: var(--fg-dim); }
details[open] summary { border-bottom: 1px solid var(--border-select); }
pre { margin: 0; padding: 10px 12px; overflow: auto; max-height: 560px; background: var(--bg-code); font: 12.5px/1.55 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere; border-radius: 0 0 3px 3px; }
.msg { border: 1px solid var(--border); border-left: 1px solid var(--fg-dim); border-radius: 3px; margin: 0 0 10px; background: var(--bg-alt); scroll-margin-top: 140px; transition: border-color .2s; }
.msg:hover { border-color: var(--border-strong); }
.msg > .head { display: flex; align-items: baseline; gap: 10px; padding: 8px 12px; border-bottom: 1px solid var(--border); background: var(--bg-code); border-radius: 3px 3px 0 0; }
.role { font-family: var(--mono); font-weight: 400; font-size: 10.5px; text-transform: uppercase; letter-spacing: .22em; }
.turn { font-family: var(--mono); color: var(--fg-dim); font-size: 10.5px; letter-spacing: .14em; }
.head .spacer { flex: 1; }
.small { font-family: var(--mono); color: var(--fg-dim); font-size: 10.5px; letter-spacing: .1em; }
.msg .inner { padding: 10px 12px; display: grid; gap: 8px; }
.r-assistant { border-left-color: var(--accent); }
.r-tool { border-left-color: var(--warn); }
.r-user { border-left-color: var(--info); }
.r-system { border-left-color: var(--fg-dim); }
.r-exit { border-left-color: var(--ok); }
.cmd { background: var(--bg-code); border: 1px solid var(--border); border-radius: 2px; padding: 8px 10px; font: 12.5px/1.55 var(--mono); white-space: pre-wrap; overflow-wrap: anywhere; }
.rc { font-family: var(--mono); font-weight: 400; }
footer { margin-top: 34px; padding-top: 18px; border-top: 1px solid var(--border-strong); font-family: var(--mono); font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase; color: var(--fg-dim); }
"""


def _secrets(obj: Any, found: set[str]) -> None:
    """Collect credential-looking string values so we can scrub them everywhere."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                _secrets(value, found)
            elif isinstance(value, str) and len(value) >= 6 and any(s in key.lower() for s in SECRET_KEYS):
                found.add(value)
    elif isinstance(obj, list):
        for value in obj:
            _secrets(value, found)


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            key: (REDACTED if isinstance(value, str) and any(s in key.lower() for s in SECRET_KEYS) else _redact(value))
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(value) for value in obj]
    return obj


def _scrub(text: str, secrets: set[str]) -> str:
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, REDACTED).replace(html.escape(secret), REDACTED)
    return text


def _commands(msg: dict) -> list[str]:
    cmds: list[str] = []
    for call in msg.get("tool_calls") or []:
        func = call.get("function") or {}
        try:
            args = json.loads(func.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        cmd = args.get("command") if isinstance(args, dict) else None
        cmds.append(cmd or json.dumps(func.get("arguments", ""), indent=2))
    return [cmd for cmd in cmds if cmd.strip()]


def _elapsed(extra: dict, base_ts: float | None) -> str:
    ts = extra.get("timestamp")
    return f"+{ts - base_ts:.0f}s" if isinstance(ts, (int, float)) and base_ts is not None else ""


def _message(msg: dict, index: int, step: int, out_index: int, base_ts: float) -> tuple[dict, int, int]:
    """Turn one trajectory message into template data: role, anchor, meta parts and content items."""
    role = str(msg.get("role", "unknown"))
    extra = msg.get("extra") or {}
    turn, meta, blocks, anchor = "", [], [], f"m{index}"

    if role == "assistant":
        step, out_index, turn, anchor = step + 1, 0, f"turn {step + 1}", f"turn-{step + 1}"
        usage = (extra.get("response") or {}).get("usage") or {}
        if usage:
            meta.append({"text": f"{usage.get('prompt_tokens', 0)} in / {usage.get('completion_tokens', 0)} out tok"})
        if elapsed := _elapsed(extra, base_ts):
            meta.append({"text": elapsed})
        reasoning = str(msg.get("reasoning_content") or "")
        if reasoning.strip():
            blocks.append({"kind": "fold", "summary": f"reasoning ({len(reasoning):,} chars)", "text": reasoning})
        blocks.append({"kind": "pre", "text": str(msg.get("content") or "")})
        cmds = _commands(msg)
        blocks.extend(
            {
                "kind": "cmd",
                "text": cmd,
                "label": f"command {i} of {len(cmds)}" if len(cmds) > 1 else "",
            }
            for i, cmd in enumerate(cmds, 1)
        )
    elif role == "tool":
        out_index += 1
        turn = f"turn {step} · output {out_index}"
        rc = extra.get("returncode")
        raw = str(extra.get("raw_output") or "") or str(msg.get("content") or "")
        if rc is not None:
            meta.append({"text": f"rc {rc}", "css": f"rc {'ok' if rc == 0 else 'bad'}"})
        if raw:
            meta.append({"text": f"{len(raw):,} chars"})
        if elapsed := _elapsed(extra, base_ts):
            meta.append({"text": elapsed})
        if extra.get("exception_info"):
            blocks.append({"kind": "alert", "text": str(extra["exception_info"])})
        blocks.append({"kind": "pre", "text": raw})
    elif role == "exit":
        status = str(extra.get("exit_status") or "exit")
        turn, meta = status, [{"text": status}]
        blocks.append(
            {"kind": "fold", "summary": "submission / patch", "text": str(msg.get("content") or ""), "open": True}
        )
    else:
        content = str(msg.get("content") or "")
        meta.append({"text": f"{len(content):,} chars"})
        blocks.append(
            {
                "kind": "fold",
                "summary": f"{role} message ({len(content):,} chars)",
                "text": content,
                "open": len(content) < 4000,
            }
        )

    return {"role": role, "turn": turn, "anchor": anchor, "meta": meta, "blocks": blocks}, step, out_index


def render_traj_html(path: Path, *, prev: str | None = None, next_: str | None = None) -> str:
    """Render one trajectory file to a complete standalone HTML document.

    prev/next are hrefs to the neighbouring instances' pages within the same variant.
    """
    raw = json.loads(path.read_text())
    messages = raw.get("messages", []) if isinstance(raw, dict) else raw
    info = raw.get("info", {}) if isinstance(raw, dict) else {}
    config = info.get("config", {}) or {}
    model_stats = info.get("model_stats", {}) or {}

    secrets: set[str] = set()
    _secrets(raw, secrets)

    timestamps = [ts for msg in messages if isinstance((ts := (msg.get("extra") or {}).get("timestamp")), (int, float))]
    base_ts = timestamps[0] if timestamps else 0.0
    wall_time = f"{max(timestamps) - base_ts:.0f}s" if timestamps else "-"
    non_zero_rc = sum(1 for msg in messages if (msg.get("extra") or {}).get("returncode") not in (0, None))
    exit_status = next(
        ((msg.get("extra") or {}).get("exit_status") for msg in messages if msg.get("role") == "exit"),
        None,
    )

    rendered, step, out_index = [], 0, 0
    for index, msg in enumerate(messages):
        message, step, out_index = _message(msg, index, step, out_index, base_ts)
        rendered.append(message)

    chips = [
        {"name": name, "value": value, "css": css}
        for name, value, css in [
            ("exit", exit_status or "none", "ok" if exit_status == "Submitted" else "bad"),
            ("api calls", model_stats.get("api_calls", 0), ""),
            ("cost", f"${model_stats.get('instance_cost', 0):.4f}", ""),
            ("messages", len(messages), ""),
            ("turns", step, ""),
            ("non-zero rc", non_zero_rc, "bad" if non_zero_rc else "ok"),
            ("wall time", wall_time, ""),
        ]
    ]

    return _scrub(
        TEMPLATE.render(
            title=path.parent.name,
            css=CSS,
            model=(config.get("model") or {}).get("model_name", "?"),
            source="/".join(path.parts[-4:-1]),
            version=info.get("mini_version", "?"),
            image=(config.get("environment") or {}).get("image", "?"),
            chips=chips,
            prev=prev,
            next=next_,
            config=json.dumps(_redact(config), indent=2, default=str),
            messages=rendered,
            traj_name=path.name,
        ),
        secrets,
    )


def html_name(traj_file: Path) -> str:
    return traj_file.name.removesuffix(".traj.json") + ".html"


def _sibling_href(from_out: Path, to_out: Path) -> str:
    """href from one generated page to another, both mirroring the data/ layout."""
    return quote(str(Path(os.path.relpath(to_out, from_out.parent))).replace("\\", "/"))


def build_traj_html(data_dir: Path, out_root: Path, *, force: bool = False) -> int:
    """Render every trajectory under data_dir into out_root, mirroring the data/ hierarchy.

    Neighbour links stay inside the variant that a trajectory belongs to.
    """
    groups: dict[Path, list[Path]] = {}
    for traj_file in sorted(data_dir.rglob("*.traj.json")):
        groups.setdefault(traj_file.parent.parent, []).append(traj_file)

    # Regenerate when either the trajectory or the page design is newer than the output.
    template_stamp = max(Path(__file__).stat().st_mtime, (Path(__file__).parent / "template-traj.html").stat().st_mtime)
    written = 0
    for group in groups.values():
        outs = [(out_root / f.relative_to(data_dir)).with_name(html_name(f)) for f in group]
        for index, (src, dst) in enumerate(zip(group, outs)):
            if not force and dst.exists() and dst.stat().st_mtime >= max(src.stat().st_mtime, template_stamp):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(
                render_traj_html(
                    src,
                    prev=_sibling_href(dst, outs[index - 1]) if index else None,
                    next_=_sibling_href(dst, outs[index + 1]) if index + 1 < len(outs) else None,
                ),
                encoding="utf-8",
            )
            written += 1
    return written
