"""Regression tests for Hiếu's CP0 pipeline integration."""
from __future__ import annotations

import sys
import types

from src.m2_search import DenseSearch


def test_dense_search_falls_back_to_memory_on_connection_error(monkeypatch):
    calls = []

    class FakeQdrantClient:
        def __init__(self, host=None, **kwargs):
            calls.append(host)
            self.host = host

        def get_collections(self):
            if self.host != ":memory:":
                raise RuntimeError("Qdrant connection refused")

    qdrant_module = types.ModuleType("qdrant_client")
    qdrant_module.QdrantClient = FakeQdrantClient
    qdrant_module.__path__ = []
    http_module = types.ModuleType("qdrant_client.http")
    http_module.__path__ = []
    exceptions_module = types.ModuleType("qdrant_client.http.exceptions")

    class ResponseHandlingException(Exception):
        pass

    exceptions_module.ResponseHandlingException = ResponseHandlingException
    monkeypatch.setitem(sys.modules, "qdrant_client", qdrant_module)
    monkeypatch.setitem(sys.modules, "qdrant_client.http", http_module)
    monkeypatch.setitem(sys.modules, "qdrant_client.http.exceptions", exceptions_module)

    search = DenseSearch()

    assert calls == ["localhost", ":memory:"]
    assert search.client.host == ":memory:"
    assert search._encoder is None


def _install_fake_ragas(monkeypatch, metric_rows, *, evaluate_error=None):
    import pandas as pd

    datasets_module = types.ModuleType("datasets")

    class Dataset:
        @staticmethod
        def from_dict(payload):
            return payload

    datasets_module.Dataset = Dataset
    ragas_module = types.ModuleType("ragas")
    metrics_module = types.ModuleType("ragas.metrics")
    for name in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
        setattr(metrics_module, name, object())

    llms_module = types.ModuleType("ragas.llms")
    llms_module.llm_factory = lambda model, base_url: types.SimpleNamespace(
        model=model, base_url=base_url
    )
    embeddings_module = types.ModuleType("ragas.embeddings")
    embeddings_module.HuggingfaceEmbeddings = lambda model_name: types.SimpleNamespace(
        model_name=model_name
    )

    def evaluate(dataset, *, metrics, llm, embeddings):
        if evaluate_error:
            raise evaluate_error
        return types.SimpleNamespace(to_pandas=lambda: pd.DataFrame(metric_rows))

    ragas_module.evaluate = evaluate
    monkeypatch.setitem(sys.modules, "datasets", datasets_module)
    monkeypatch.setitem(sys.modules, "ragas", ragas_module)
    monkeypatch.setitem(sys.modules, "ragas.metrics", metrics_module)
    monkeypatch.setitem(sys.modules, "ragas.llms", llms_module)
    monkeypatch.setitem(sys.modules, "ragas.embeddings", embeddings_module)


def test_evaluate_ragas_reports_models_used_by_evaluator(monkeypatch):
    from src import m4_eval

    model_ids = [
        "google/gemini-3.1-flash-lite-preview",
        "BAAI/bge-m3",
    ]
    monkeypatch.setattr(m4_eval, "OPENROUTER_API_KEY", "configured-for-test")
    monkeypatch.setattr(m4_eval, "GENERATION_MODEL", model_ids[0])
    monkeypatch.setattr(m4_eval, "EMBEDDING_MODEL", model_ids[1])
    _install_fake_ragas(monkeypatch, [{
        "faithfulness": 0.8,
        "answer_relevancy": 0.7,
        "context_precision": 0.6,
        "context_recall": 0.5,
    }])

    result = m4_eval.evaluate_ragas(["Q"], ["A"], [["C"]], ["GT"])

    assert result["evaluation_status"] == "evaluated"
    assert result["metadata"]["evaluator_models"] == model_ids


def test_evaluate_ragas_does_not_claim_success_when_skipped_or_failed(monkeypatch):
    from src import m4_eval

    monkeypatch.setattr(m4_eval, "OPENROUTER_API_KEY", "")
    skipped = m4_eval.evaluate_ragas(["Q"], ["A"], [["C"]], ["GT"])
    assert skipped["evaluation_status"] == "skipped_no_api_key"
    assert skipped["metadata"]["evaluator_models"] == []

    model_ids = ["google/gemini-3.1-flash-lite-preview", "BAAI/bge-m3"]
    monkeypatch.setattr(m4_eval, "OPENROUTER_API_KEY", "configured-for-test")
    monkeypatch.setattr(m4_eval, "GENERATION_MODEL", model_ids[0])
    monkeypatch.setattr(m4_eval, "EMBEDDING_MODEL", model_ids[1])
    _install_fake_ragas(monkeypatch, [], evaluate_error=RuntimeError("provider unavailable"))

    failed = m4_eval.evaluate_ragas(["Q"], ["A"], [["C"]], ["GT"])
    assert failed["evaluation_status"] == "failed"
    assert failed["metadata"]["evaluator_models"] == model_ids


def test_evaluate_ragas_rejects_non_finite_metric_scores(monkeypatch):
    from src import m4_eval

    monkeypatch.setattr(m4_eval, "OPENROUTER_API_KEY", "configured-for-test")
    _install_fake_ragas(monkeypatch, [{
        "faithfulness": float("nan"),
        "answer_relevancy": 0.7,
        "context_precision": 0.6,
        "context_recall": 0.5,
    }])

    result = m4_eval.evaluate_ragas(["Q"], ["A"], [["C"]], ["GT"])

    assert result["evaluation_status"] == "failed"
