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
:root {
  --bg: #fff; --bg-alt: #f6f7f9; --bg-code: #f3f4f6; --fg: #1a1a2e; --fg-dim: #6b7280;
  --border: #e3e6ea; --accent: #6c5ce7; --ok: #16803c; --bad: #c62828; --warn: #b26a00;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15151f; --bg-alt: #1e1e2e; --bg-code: #232334; --fg: #e6e6f0; --fg-dim: #9aa0b4;
    --border: #2e2e42; --accent: #a695ff; --ok: #4ade80; --bad: #ff6b6b; --warn: #f6c453;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 14px/1.55 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 0 20px 80px; }
header { position: sticky; top: 0; z-index: 10; background: var(--bg); border-bottom: 1px solid var(--border); padding: 14px 0 12px; }
header .wrap { padding-bottom: 0; }
h1 { font-size: 1.15rem; margin: 0 0 6px; }
h1 code { font-size: 1rem; color: var(--accent); }
.meta { color: var(--fg-dim); font-size: 0.82rem; overflow-wrap: anywhere; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.chip { border: 1px solid var(--border); background: var(--bg-alt); border-radius: 999px; padding: 2px 10px; font-size: 0.78rem; }
.chip b { font-weight: 600; }
.ok { color: var(--ok); } .bad { color: var(--bad); } .warn { color: var(--warn); }
.nav { margin-top: 10px; font-size: 0.82rem; display: flex; justify-content: space-between; gap: 12px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
h2 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); margin: 26px 0 10px; }
details { border: 1px solid var(--border); border-radius: 8px; background: var(--bg-alt); margin: 0; }
summary { cursor: pointer; padding: 8px 12px; font-size: 0.85rem; color: var(--fg-dim); }
details[open] summary { border-bottom: 1px solid var(--border); }
pre { margin: 0; padding: 10px 12px; overflow: auto; max-height: 560px; background: var(--bg-code); font: 12.5px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; white-space: pre-wrap; overflow-wrap: anywhere; border-radius: 0 0 8px 8px; }
.msg { border: 1px solid var(--border); border-left: 4px solid var(--fg-dim); border-radius: 8px; margin: 0 0 10px; background: var(--bg); scroll-margin-top: 140px; }
.msg > .head { display: flex; align-items: baseline; gap: 10px; padding: 7px 12px; border-bottom: 1px solid var(--border); background: var(--bg-alt); border-radius: 4px 8px 0 0; }
.role { font-weight: 650; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
.turn { color: var(--fg-dim); font-size: 0.78rem; }
.head .spacer { flex: 1; }
.small { color: var(--fg-dim); font-size: 0.76rem; }
.msg .inner { padding: 10px 12px; display: grid; gap: 8px; }
.r-assistant { border-left-color: var(--accent); }
.r-tool { border-left-color: var(--warn); }
.r-user { border-left-color: #2b6cb0; }
.r-system { border-left-color: var(--fg-dim); }
.r-exit { border-left-color: var(--ok); }
.cmd { background: var(--bg-code); border-radius: 6px; padding: 8px 10px; font: 12.5px/1.5 ui-monospace, Menlo, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
.rc { font-weight: 650; }
footer { margin-top: 30px; color: var(--fg-dim); font-size: 0.76rem; }
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

    written = 0
    for group in groups.values():
        outs = [(out_root / f.relative_to(data_dir)).with_name(html_name(f)) for f in group]
        for index, (src, dst) in enumerate(zip(group, outs)):
            if not force and dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
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
