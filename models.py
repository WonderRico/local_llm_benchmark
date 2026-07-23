from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    command: str
    returncode: int | None = None
    output_len: int | None = None
    timestamp: float | None = None
    had_exception: bool = False
    exception_info: str = ""
    output_preview: str = ""


@dataclass
class TrajectoryStats:
    instance_id: str
    trajectory_format: str | None
    exit_status: str | None = None
    submission: str | None = None
    mini_version: str | None = None
    model_name: str | None = None
    environment_image: str | None = None
    step_limit: int | None = None
    cost_limit: float | None = None

    api_calls: int = 0
    instance_cost: float = 0.0

    total_messages: int = 0
    system_messages: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    tool_messages: int = 0
    exit_messages: int = 0
    other_messages: int = 0

    tool_calls: list[ToolCall] = field(default_factory=list)
    total_tool_calls: int = 0
    multi_tool_call_turns: int = 0
    turns_with_reasoning: int = 0

    total_content_chars: int = 0
    total_reasoning_chars: int = 0

    returncode_0: int = 0
    returncode_non0: int = 0

    timestamps: list[float] = field(default_factory=list)
    wall_time_seconds: float | None = None

    unique_commands: int = 0


@dataclass
class AggregateStats:
    trajectories: list[TrajectoryStats] = field(default_factory=list)

    total: int = 0
    submitted: int = 0
    other_exits: int = 0
    submissions_with_diff: int = 0

    avg_api_calls: float = 0.0
    median_api_calls: float = 0.0
    max_api_calls: int = 0
    min_api_calls: int = 0

    avg_tool_calls: float = 0.0
    median_tool_calls: float = 0.0
    max_tool_calls: int = 0
    min_tool_calls: int = 0

    avg_wall_time: float = 0.0
    median_wall_time: float = 0.0
    max_wall_time: float = 0.0
    min_wall_time: float = 0.0

    avg_content_chars: float = 0.0
    total_content_chars: int = 0

    exit_status_counts: dict[str, int] = field(default_factory=dict)
    model_counts: dict[str, int] = field(default_factory=dict)

    avg_nonzero_returncodes: float = 0.0
    median_nonzero_returncodes: float = 0.0
