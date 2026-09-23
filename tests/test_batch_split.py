from batch import latest_eval, split_variant


def test_split_variant() -> None:
    assert split_variant("DeepSeek-V4-Flash/3107-high-run2_WQQ2KXL_CQBF16") == {
        "base": "DeepSeek-V4-Flash",
        "variant": "3107-high-run2",
        "wq": "Q2KXL",
        "cq": "BF16",
    }
    assert split_variant("GLM-5.2/API") == {"base": "GLM-5.2", "variant": "API", "wq": "", "cq": ""}


def test_latest_eval_prefers_highest_id(tmp_path) -> None:
    for name in ("eval.json", "eval2.json", "eval10.json", "eval_notes.json"):
        (tmp_path / name).write_text("{}")
    assert latest_eval(tmp_path) == tmp_path / "eval10.json"
    (tmp_path / "eval10.json").unlink()
    assert latest_eval(tmp_path) == tmp_path / "eval2.json"
    for name in ("eval2.json", "eval.json", "eval_notes.json"):
        (tmp_path / name).unlink()
    assert latest_eval(tmp_path) is None
