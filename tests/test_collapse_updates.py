from dashboard_lib import collapse_updates

HTML = (
    "<h2>Hall of fame</h2><p>intro</p><h3>update A</h3><ul><li>x</li></ul>"
    "<h3>update B</h3><p>y</p><h2>About Score</h2><h3>not folded</h3>"
)


def test_newest_open_and_rest_closed():
    out = collapse_updates(HTML)
    assert "<details open><summary>update A</summary><ul><li>x</li></ul></details>" in out
    assert "<details><summary>update B</summary><p>y</p></details>" in out
    assert out.endswith("<h2>About Score</h2><h3>not folded</h3>")  # other sections untouched
