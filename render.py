from __future__ import annotations

from models import ToolCall, TrajectoryStats, AggregateStats


def format_duration(s: float) -> str:
    if s < 60:
        return f"{s:.1f}s"
    m = int(s // 60)
    r = s - m * 60
    return f"{m}m {r:.0f}s"


def render_single(stats: TrajectoryStats) -> str:
    lines = [
        f"Instance: {stats.instance_id}",
        f"Format: {stats.trajectory_format or 'legacy'}",
        f"Exit: {stats.exit_status or 'N/A'}",
        f"Model: {stats.model_name or 'N/A'}",
        f"API calls: {stats.api_calls}",
        (
            f"Messages: {stats.total_messages} (system={stats.system_messages}, "
            f"user={stats.user_messages}, assistant={stats.assistant_messages}, "
            f"tool={stats.tool_messages}, exit={stats.exit_messages})"
        ),
        f"Tool calls: {stats.total_tool_calls}",
        f"  Multi-tool-call turns: {stats.multi_tool_call_turns}",
        f"  Return code 0: {stats.returncode_0}, non-zero: {stats.returncode_non0}",
        f"  Unique commands: {stats.unique_commands}",
        f"Turns with reasoning: {stats.turns_with_reasoning}",
        f"Content: {stats.total_content_chars:,} chars (reasoning: {stats.total_reasoning_chars:,})",
    ]
    if stats.wall_time_seconds:
        lines.append(f"Wall time: {format_duration(stats.wall_time_seconds)}")
    if stats.submission:
        lines.append(f"Submission length: {len(stats.submission)} chars")
    return "\n".join(lines)


def render_aggregate(agg: AggregateStats) -> str:
    lines = [
        f"Total trajectories: {agg.total}",
        f"Submitted: {agg.submitted}, Other exits: {agg.other_exits}",
        f"Submissions with diff: {agg.submissions_with_diff}",
        "",
        "Exit statuses:",
    ]
    for st, c in sorted(agg.exit_status_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {st}: {c}")
    lines.append("")
    if agg.model_counts:
        lines.append("Models:")
        for m, c in sorted(agg.model_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {m}: {c}")
        lines.append("")
    if agg.avg_api_calls:
        lines.append(
            f"API calls: avg={agg.avg_api_calls:.1f}, median={agg.median_api_calls:.0f}, "
            f"min={agg.min_api_calls}, max={agg.max_api_calls}"
        )
    if agg.avg_tool_calls:
        lines.append(
            f"Tool calls: avg={agg.avg_tool_calls:.1f}, median={agg.median_tool_calls:.0f}, "
            f"min={agg.min_tool_calls}, max={agg.max_tool_calls}"
        )
    if agg.avg_wall_time:
        lines.append(
            f"Wall time: avg={format_duration(agg.avg_wall_time)}, "
            f"median={format_duration(agg.median_wall_time)}, "
            f"min={format_duration(agg.min_wall_time)}, "
            f"max={format_duration(agg.max_wall_time)}"
        )
    lines.append(
        f"Content: avg={agg.avg_content_chars:,.0f} chars/trajectory, "
        f"total={agg.total_content_chars:,} chars"
    )
    if agg.avg_nonzero_returncodes:
        lines.append(
            f"Non-zero return codes: avg={agg.avg_nonzero_returncodes:.1f}, "
            f"median={agg.median_nonzero_returncodes:.0f}"
        )
    return "\n".join(lines)


def render_table(trajs: list[TrajectoryStats]) -> str:
    lines = [
        f"Trajectories ({len(trajs)} total)",
        (
            f"{'Instance':<50} {'Exit':<15} {'API':<8} {'Tools':<8} "
            f"{'Messages':<10} {'Wall Time':<12} {'Non-Zero RC'}"
        ),
        "-" * 120,
    ]
    for t in trajs:
        wt = format_duration(t.wall_time_seconds) if t.wall_time_seconds else "-"
        lines.append(
            f"{t.instance_id:<50} {t.exit_status or '-':<15} {str(t.api_calls):<8} "
            f"{str(t.total_tool_calls):<8} {str(t.total_messages):<10} {wt:<12} "
            f"{str(t.returncode_non0)}"
        )
    return "\n".join(lines)


def _classify_failure(preview: str) -> str:
    pv_lower = preview.lower()

    if "traceback" in pv_lower:
        for exc_name in (
            "syntaxerror",
            "attributeerror",
            "keyerror",
            "importerror",
            "modulenotfounderror",
            "valueerror",
            "typeerror",
            "filenotfounderror",
            "unicodeencodeerror",
            "unicodedecodeerror",
            "assertionerror",
            "permissionerror",
            "ioerror",
            "unsupportedoperationerror",
            "fileexistserror",
            "isadirectoryerror",
            "notadirectoryerror",
        ):
            if exc_name in pv_lower:
                return exc_name.capitalize().replace("error", "Error")
        return "Traceback(other)"

    if "not found" in pv_lower or "no such file" in pv_lower or "no such directory" in pv_lower:
        return "File/dir not found"
    if "permission denied" in pv_lower:
        return "Permission denied"
    if "syntax error" in pv_lower:
        return "Shell syntax error"
    if not preview.strip():
        return "grep/no-match (empty output)"
    if "fail:" in pv_lower or "failure" in pv_lower:
        return "Test failure"
    if "error" in pv_lower:
        return "Error(other)"
    return "Other"


def render_failures(trajs: list[TrajectoryStats]) -> str:
    failures: list[tuple[str, str, int, str, str]] = []
    for t in trajs:
        for tc in t.tool_calls:
            if tc.returncode is not None and tc.returncode != 0:
                failures.append(
                    (t.instance_id, tc.command, tc.returncode, tc.exception_info, tc.output_preview)
                )

    lines = [f"{len(failures)} non-zero return codes across {len(trajs)} trajectories\n"]

    reason_counts: dict[str, int] = {}
    for _, _, _, _, preview in failures:
        reason = _classify_failure(preview)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    lines.append("Reason    Count")
    lines.append("-" * 30)
    for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
        lines.append(f"{reason:<20} {count}")
    lines.append("")

    per_traj: dict[str, int] = {}
    for t in trajs:
        n = sum(1 for tc in t.tool_calls if tc.returncode is not None and tc.returncode != 0)
        if n > 0:
            per_traj[t.instance_id] = n

    ranked = sorted(per_traj.items(), key=lambda x: -x[1])
    lines.append(
        f"Non-zero return codes per trajectory ({len(ranked)} of {len(trajs)} had errors)"
    )
    lines.append(f"{'Instance':<50} {'Errors'}")
    lines.append("-" * 60)
    for inst, cnt in ranked:
        lines.append(f"{inst:<50} {cnt}")
    return "\n".join(lines)


def render_commands(trajs: list[TrajectoryStats], top: int = 20) -> str:
    cmd_counts: dict[str, int] = {}
    for t in trajs:
        for tc in t.tool_calls:
            cmd_counts[tc.command] = cmd_counts.get(tc.command, 0) + 1

    ranked = sorted(cmd_counts.items(), key=lambda x: -x[1])[:top]
    lines = [
        f"Top {len(ranked)} commands ({len(cmd_counts)} unique across {len(trajs)} trajectories)",
        f"{'#':<5} {'Count':<8} Command",
        "-" * 80,
    ]
    for i, (cmd, c) in enumerate(ranked, 1):
        lines.append(f"{i:<5} {c:<8} {cmd}")
    return "\n".join(lines)
