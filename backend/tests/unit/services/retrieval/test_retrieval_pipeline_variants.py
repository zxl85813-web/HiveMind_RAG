from app.services.retrieval.pipeline import RetrievalPipeline


def _step_names(steps):
    return [s.__class__.__name__ for s in steps]


def test_resolve_steps_default_contains_graph_and_compression():
    pipeline = RetrievalPipeline()

    names = _step_names(pipeline._resolve_steps("default"))

    assert "GraphRetrievalStep" in names
    assert "ContextualCompressionStep" in names


def test_resolve_steps_ab_no_graph_removes_graph_step():
    pipeline = RetrievalPipeline()

    names = _step_names(pipeline._resolve_steps("ab_no_graph"))

    assert "GraphRetrievalStep" not in names
    assert "ContextualCompressionStep" in names


def test_resolve_steps_ab_no_compress_removes_compression_step():
    pipeline = RetrievalPipeline()

    names = _step_names(pipeline._resolve_steps("ab_no_compress"))

    assert "GraphRetrievalStep" in names
    assert "ContextualCompressionStep" not in names
