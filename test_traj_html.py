import html
import json
import re
from pathlib import Path

import traj_html

API_KEY = "s&<x>" + "s" * 19  # credentials can contain HTML-significant characters
API_BASE = "https://private-host.example.com/v1"


def _traj(data_dir: Path, model: str, variant: str, instance: str, *, command: str = "ls") -> Path:
    path = data_dir / model / variant / instance / f"{instance}.traj.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "instance_id": instance,
                "info": {
                    "config": {"model": {"model_kwargs": {"api_key": API_KEY, "api_base": API_BASE}}},
                    "model_stats": {"api_calls": 2},
                },
                "messages": [
                    {
                        "role": "assistant",
                        "content": "looking",
                        "reasoning_content": "think",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "bash",
                                    "arguments": json.dumps({"command": command}),
                                }
                            }
                        ],
                    },
                    {
                        "role": "tool",
                        "extra": {"returncode": 1, "raw_output": f"boom {API_KEY}"},
                    },
                    {"role": "exit", "extra": {"exit_status": "Submitted"}, "content": "diff --git"},
                ],
            }
        )
    )
    return path


def test_redacts_credentials_and_renders_every_step(tmp_path):
    _traj(tmp_path / "data", "M1", "v1", "inst-a", command='echo "<secret>&co"')

    assert traj_html.build_traj_html(tmp_path / "data", tmp_path / "html_traj") == 1

    page = (tmp_path / "html_traj" / "M1" / "v1" / "inst-a" / "inst-a.html").read_text()
    assert API_KEY not in page and html.escape(API_KEY) not in page and API_BASE not in page
    assert "<pre>boom [redacted]</pre>" in page
    assert "turn 1 · output 1" in page and "rc 1" in page
    assert "&lt;secret&gt;&amp;co" in page
    assert "diff --git" in page


def test_neighbour_links_stay_inside_the_variant(tmp_path):
    data = tmp_path / "data"
    _traj(data, "M1", "v1", "inst-a")
    _traj(data, "M1", "v1", "inst-b")
    _traj(data, "M2", "v2", "inst-c")

    traj_html.build_traj_html(data, tmp_path / "html_traj")

    page_b = Path(tmp_path / "html_traj/M1/v1/inst-b/inst-b.html").read_text()
    assert "../inst-a/inst-a.html" in page_b and "inst-c" not in page_b
    assert "previous instance" not in (Path(tmp_path / "html_traj/M2/v2/inst-c/inst-c.html").read_text())


def test_traj_links_only_enabled_for_local_hosts():
    import generate

    matches = re.compile(generate.TRAJ_HOST_RE).match
    assert all(matches(h) for h in ("192.168.1.20", "127.0.0.1", "localhost"))
    assert not any(matches(h) for h in ("localhost.evil.com", "bench.example.com", "10.0.0.5", ""))
