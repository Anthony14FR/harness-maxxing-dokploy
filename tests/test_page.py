import re

from conftest import ROOT


def test_children_always_go_through_fill():
    # replaceChildren prints a list as "[object HTMLSpanElement],..." and null as "null": the update button showed it
    page = (ROOT / "page.js").read_text(encoding="utf-8")
    calls = re.findall(r"\.replaceChildren\((?!\))", page)
    assert len(calls) == 1, "call fill(el, ...) instead of el.replaceChildren(...)"
    assert "el.replaceChildren(...kids.flat(Infinity).filter(" in page  # that one call, inside fill()
