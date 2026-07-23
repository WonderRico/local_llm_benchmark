from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models import ToolCall, TrajectoryStats


def _parse_tool_output(msg: dict[str, Any]) -> dict[str, Any]:
    return msg.get("extra", {})


def _extract_model_name_from_path(path: Path, stats: TrajectoryStats) -> TrajectoryStats:
    if "data" not in path.parts:
        return stats
    try:
        data_idx = path.parts.index("data")
        if len(path.parts) > data_idx + 2:
            m_name = path.parts[data_idx + 1]
            v_dir = path.parts[data_idx + 2]
            stats.model_name = f"{m_name} ({v_dir})"
    except (IndexError, ValueError):
        pass
    return stats


def _extract_commands_from_tool_calls(tool_calls_list: list[dict]) -> list[str]:
    commands: list[str] = []
    for tc in tool_calls_list:
        func = tc.get("function", {})
        try:
            args = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}
        cmd = args.get("command", "")
        if cmd:
            commands.append(cmd)
    return commands


def parse_trajectory(path: Path) -> TrajectoryStats:
    with path.open() as f:
        raw = json.load(f)

    is_new_format = isinstance(raw, dict) and "trajectory_format" in raw

    if is_new_format:
        info = raw.get("info", {})
        messages = raw.get("messages", [])
        stats = TrajectoryStats(
            instance_id=raw.get("instance_id", ""),
            trajectory_format=raw.get("trajectory_format"),
            exit_status=info.get("exit_status"),
            submission=info.get("submission"),
            mini_version=info.get("mini_version"),
            model_name=info.get("config", {}).get("model", {}).get("model_name"),
            environment_image=info.get("config", {})
            .get("environment", {})
            .get("image"),
            step_limit=info.get("config", {}).get("agent", {}).get("step_limit"),
            cost_limit=info.get("config", {}).get("agent", {}).get("cost_limit"),
            api_calls=info.get("model_stats", {}).get("api_calls", 0),
            instance_cost=info.get("model_stats", {}).get("instance_cost", 0.0),
        )
    else:
        messages = raw
        stats = TrajectoryStats(
            instance_id=path.stem,
            trajectory_format=None,
        )

    stats = _extract_model_name_from_path(path, stats)

    stats.total_messages = len(messages)
    commands: list[str] = []
    tool_calls: list[ToolCall] = []

    for msg in messages:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", ""))
        stats.total_content_chars += len(content)

        if role == "system":
            stats.system_messages += 1
        elif role == "user":
            stats.user_messages += 1
        elif role == "assistant":
            stats.assistant_messages += 1
            rc = msg.get("reasoning_content", "")
            if rc:
                stats.turns_with_reasoning += 1
                stats.total_reasoning_chars += len(rc)
            tc_list = msg.get("tool_calls", [])
            if tc_list:
                stats.total_tool_calls += len(tc_list)
                if len(tc_list) > 1:
                    stats.multi_tool_call_turns += 1
                cmds = _extract_commands_from_tool_calls(tc_list)
                commands.extend(cmds)
                for cmd in cmds:
                    tool_calls.append(ToolCall(command=cmd))
        elif role == "tool":
            stats.tool_messages += 1
            tool_data = _parse_tool_output(msg)
            rc = tool_data.get("returncode")
            if rc == 0:
                stats.returncode_0 += 1
            elif rc is not None:
                stats.returncode_non0 += 1
            ts = tool_data.get("timestamp")
            if ts is not None:
                stats.timestamps.append(ts)
            stats.total_content_chars += len(tool_data.get("raw_output", ""))

            if tool_calls:
                last = tool_calls[-1]
                last.returncode = tool_data.get("returncode")
                raw_output = tool_data.get("raw_output", "")
                last.output_len = len(raw_output)
                last.timestamp = tool_data.get("timestamp")
                exc = tool_data.get("exception_info", "")
                last.had_exception = bool(exc)
                last.exception_info = exc
                if last.returncode is not None and last.returncode != 0:
                    last.output_preview = raw_output[:500].replace("\n", " ")
        elif role == "exit":
            stats.exit_messages += 1
        else:
            stats.other_messages += 1

    if stats.timestamps:
        stats.wall_time_seconds = stats.timestamps[-1] - stats.timestamps[0]

    stats.unique_commands = len(set(commands))
    stats.tool_calls = tool_calls
    return stats


def parse_dir(path: Path, recursive: bool = False) -> list[TrajectoryStats]:
    pattern = "**/*.traj.json" if recursive else "*.traj.json"
    return [parse_trajectory(f) for f in sorted(path.glob(pattern))]
