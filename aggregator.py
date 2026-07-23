from __future__ import annotations

import statistics

from models import AggregateStats, TrajectoryStats


def aggregate(trajs: list[TrajectoryStats]) -> AggregateStats:
    agg = AggregateStats(trajectories=trajs)
    agg.total = len(trajs)
    if not trajs:
        return agg

    for t in trajs:
        st = t.exit_status or "Unknown"
        agg.exit_status_counts[st] = agg.exit_status_counts.get(st, 0) + 1
        if st == "Submitted":
            agg.submitted += 1
        else:
            agg.other_exits += 1
        if t.submission and t.submission.strip():
            agg.submissions_with_diff += 1
        mn = t.model_name or "Unknown"
        agg.model_counts[mn] = agg.model_counts.get(mn, 0) + 1
        agg.total_content_chars += t.total_content_chars

    def _fill_stats(values: list, agg_obj: AggregateStats, prefix: str) -> None:
        if not values:
            return
        setattr(agg_obj, f"avg_{prefix}", statistics.mean(values))
        setattr(agg_obj, f"median_{prefix}", statistics.median(values))
        setattr(agg_obj, f"max_{prefix}", max(values))
        setattr(agg_obj, f"min_{prefix}", min(values))

    api_calls = [t.api_calls for t in trajs if t.api_calls > 0]
    _fill_stats(api_calls, agg, "api_calls")

    tc_counts = [t.total_tool_calls for t in trajs if t.total_tool_calls > 0]
    _fill_stats(tc_counts, agg, "tool_calls")

    wall_times = [
        t.wall_time_seconds
        for t in trajs
        if t.wall_time_seconds is not None and t.wall_time_seconds > 0
    ]
    _fill_stats(wall_times, agg, "wall_time")

    if trajs:
        agg.avg_content_chars = agg.total_content_chars / len(trajs)

    nzrcs = [t.returncode_non0 for t in trajs if t.returncode_non0 > 0]
    _fill_stats(nzrcs, agg, "nonzero_returncodes")

    return agg
