"""doc_synth: target selection and batch-result merging."""


from codescope.indexer import doc_synth
from codescope.indexer.scip_parser import SymbolRecord


def rec(qname, kind="Function", doc="", file="fastapi/x.py"):
    return SymbolRecord(
        id=qname, name=qname.split(".")[-1], qualified_name=qname, kind=kind,
        file=file, start_line=1, end_line=2, doc=doc, signature="",
    )


def test_pick_targets_filters_docs_kinds_and_paths():
    symbols = [
        rec("fastapi.a"),                             # yes
        rec("fastapi.b", doc="documented"),           # no: has doc
        rec("fastapi.c", kind="Variable"),            # no: kind
        rec("docs_src.d", file="docs_src/d.py"),      # no: path
    ]
    assert [s.qualified_name for s in doc_synth.pick_targets(symbols)] == ["fastapi.a"]


def test_synthesize_merges_batches(monkeypatch, tmp_path):
    symbols = [rec(f"fastapi.f{i}") for i in range(45)]  # 3 batches of 20

    def fake_batch(batch, repo_root, model):
        return {s.id: f"doc for {s.name}" for s in batch}

    monkeypatch.setattr(doc_synth, "_run_batch", fake_batch)
    out = doc_synth.synthesize(symbols, repo_root=tmp_path)
    assert len(out) == 45
    assert out["fastapi.f7"] == "doc for f7"


def test_snippet_fixed_window(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("\n".join(f"line{i}" for i in range(100)))
    s = SymbolRecord(id="x", name="x", qualified_name="m.x", kind="Function",
                     file="m.py", start_line=10, end_line=5, doc="", signature="")
    snip = doc_synth._snippet(tmp_path, s)
    assert snip.startswith("line9")
    assert len(snip.splitlines()) == doc_synth.SNIPPET_LINES
