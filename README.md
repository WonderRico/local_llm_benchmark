# Trajectory Parser & Benchmark Analyzer

Parse, aggregate, and visualize benchmark trajectories from [mini-swe-agent](https://github.com/swe-agent/mini-swe-agent) runs on the SWE-bench Verified dataset.

This tool processes `.traj.json` files — the full trace of an agentic session (messages, tool calls, timestamps, exceptions) — into structured statistics and generates interactive HTML dashboards for comparing LLMs across models, quantization strategies, inference engines, and hardware configurations.

-> Mainly Vibe coded, only with local models

## Architecture

The pipeline flows in four stages:

```
data/  ──>  parser.py  ──>  aggregator.py  ──>  render.py  ──>  results/
                          │                   │                │
                          │                   │         ┌─────┘
                          │                   │         v
                          │                   │    batch.py
                          │                   │         │
                          │                   │         v
                          │                   │    generate.py (detail)
                          │                   │         │
                          │                   │         v
                          │                   │    benchmark-detail.html
                          │
                   data.csv + text.md  ──>  dashboard_lib.py
                                            generate.py (main)
                                                   │
                                                   v
                                            benchmark-main.html
```

Both pages are produced by the single `generate.py` entry point.

## Modules

### `models.py` — Data Models

Two core dataclasses:

- **`ToolCall`**: A single tool invocation with command, return code, output length, timestamp, and exception info.
- **`TrajectoryStats`**: Statistics for one trajectory — message counts by role (system/user/assistant/tool/exit), tool call counts, content/reasoning character totals, return code breakdown, wall time, multi-tool-call turns, and unique commands.
- **`AggregateStats`**: Aggregated statistics across many trajectories — totals, averages/medians/mins/maxes for API calls, tool calls, wall time, content chars, and non-zero return codes, plus exit status and model counts.

### `parser.py` — Trajectory Parsing

Parses `.traj.json` files in two formats:

- **New format** (dictionary with `trajectory_format`, `info`, `messages` keys): extracts config (model, environment image, step/cost limits), model stats (API calls, cost), and full message enumeration.
- **Legacy format** (raw message array): falls back to filename-based instance ID, no format marker.

Message classification:
- `system` / `user` / `assistant` / `tool` / `exit` / `other`
- Extracts reasoning content from assistant messages
- Parses tool call arguments from assistant messages to extract commands
- Reads tool output (return code, raw output, timestamps, exception info)

Directory parsing supports recursive globbing (`**/*.traj.json`) for deeply nested data directories.

### `aggregator.py` — Aggregation

Produces `AggregateStats` from a list of `TrajectoryStats`:

- Counts exit statuses (Submitted vs other)
- Tracks models and submissions with diffs
- Computes avg/median/max/min for: API calls, tool calls, wall time, non-zero return codes
- Tracks total content characters

### `render.py` — Text Rendering

Four render functions for terminal/CLI output:

- **`render_single`**: One trajectory — instance ID, format, exit status, model, message breakdown, tool call stats, reasoning chars, wall time.
- **`render_aggregate`**: Summary across all trajectories — totals, exit status distribution, model counts, averages.
- **`render_table`**: Tabular view — instance ID, exit status, API calls, tool calls, messages, wall time, non-zero return codes.
- **`render_failures`**: Error analysis — classifies non-zero return codes into categories (Traceback, AttributeError, ImportError, FileNotFound, etc.) and ranks trajectories by error count.
- **`render_commands`**: Most-used commands ranked by frequency.

Failure classification (in `_classify_failure`): inspects output preview text for Python tracebacks, filesystem errors, permission denied, test failures, etc.

### `batch.py` — Batch Processing

Walks `data/` directory organized as `data/{model}/{variant}/**/*.traj.json` and for each variant:

1. Parses all trajectories (recursive)
2. Generates `summary.txt`, `table.txt`, `failures.txt`
3. Copies `eval.json` (SWE-bench evaluation results) if present

Output mirrors the input structure under `results/`.

### `dashboard_lib.py` — Shared Library

Shared utilities for both dashboards:

- **`parse_csv`**: Parses `data.csv` with 21-column benchmark records (base, model name, params, quantization, engine, GPU count, score, duration, requests, tokens, cost, etc.)
- Handles European number format (comma as decimal separator)
- Converts duration strings (`HH:MM:SS` or `MM:SS`) to seconds
- **`render_markdown`**: Converts `text.md` (benchmark analysis prose) to sanitized HTML via Python-Markdown + Bleach
- **`render_html`**: Reads any Jinja2 template, renders it with the given context, writes the output HTML
- **`render_dashboard`**: Combines CSV data + markdown + `template-main.html` into `benchmark-main.html`
- Defines the shared path constants (`data.csv`, `text.md`, `results/`, templates, output files)

### `generate.py` — Single Entry Point

One script produces both pages from the shared library. The detail page:

- Parses summary/table/failures text back into structured dictionaries (re-parses the text output generated by `render.py`)
- Reads `eval.json` for resolved/unresolved/empty-patch/error instance lists
- Groups by model → variant
- Computes derived metrics (total tools, total API calls, total non-zero return codes)
- Injects JSON data into `template-detail.html` (Plotly.js) via `dashboard_lib.render_html`

## Data Format

### Trajectory Files (`.traj.json`)

Located under `data/{model}/{variant}/`:

```
data/
  Qwen3.6-27B/
    SGLANG-1GPU_WQBF16_CQFP8/
      django__django-13128.traj.json
      django__django-12406.traj.json
      ...
```

Each file contains a session trace with messages, tool calls, timestamps, and reasoning content.

### Eval Results (`eval.json`)

SWE-bench evaluation per variant — lists submitted, resolved, unresolved, empty-patch, and error instances.

### CSV (`data.csv`)

Main benchmark index with columns:

| Column | Description |
|---|---|
| `base` | Model family |
| `model name` | Variant display name |
| `Total Params (B)` | Total parameter count |
| `Active Params (B)` | Active (expert) parameter count |
| `model size (GB)` | Memory footprint |
| `Weights Quantization` | Weight quantization format |
| `KV cache quantization` | KV-Cache quantization format |
| `engine` | Inference engine (SGLANG, vLLM, llama.cpp) |
| `Nb GPU` | GPU count |
| `License` | Model license |
| `Model ref` | Unique run identifier |
| `Score /100` | SWE-bench score |
| `Duration` | Total run time |
| `Requests` | Number of HTTP requests |
| `req/pts` | Requests per point scored |
| `in Mtok` | Input tokens (millions) |
| `out Mtok` | Output tokens (millions) |
| `total TG/s` | Total token generation rate |
| `parallel tasks` | Parallelism level |
| `TG/s per task` | Per-task token generation rate |
| `total cost $` | Estimated cost (API $ or local power cost) |

### Markdown (`text.md`)

Benchmark analysis in prose — preamble, disclaimers, technical setup, hall of fame, model-by-model observations, quantization impact analysis, and context size benchmarks.

## Templates

- **`template-main.html`**: Jinja2 template for the main dashboard (Plotly.js charts, dark/light mode, interactive table with column sorting and filtering)
- **`template-detail.html`**: Jinja2 template for the detailed comparison report (per-model variant drill-down with failure analysis and instance status)

## Generated Outputs

| File | Description |
|---|---|
| `results/{model}/{variant}/summary.txt` | Aggregate statistics per variant |
| `results/{model}/{variant}/table.txt` | Per-instance table |
| `results/{model}/{variant}/failures.txt` | Failure analysis |
| `results/{model}/{variant}/eval.json` | Copied eval results |
| `benchmark-main.html` | Main benchmark dashboard |
| `benchmark-detail.html` | Interactive comparison report |

## Usage

```bash
# Generate both pages (default)
python generate.py

# Generate a single page
python generate.py main      # benchmark-main.html only
python generate.py detail    # benchmark-detail.html only

# Reuse existing results/ instead of regenerating them from data/
python generate.py detail --skip-batch
```

`generate.py detail` is self-contained — unless `--skip-batch` is given it regenerates `results/` from the raw `data/` trajectories (via `batch.py`) before building the HTML.

## Dependencies

- Python 3.10+
- `jinja2` — Template rendering
- `bleach` — HTML sanitization
- `markdown` — Markdown to HTML conversion
- `json` — JSON parsing (stdlib)

The HTML dashboards load Plotly.js from CDN.
