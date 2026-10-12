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


def test_dense_search_uses_qdrant_1_9_search_api():
    search = DenseSearch.__new__(DenseSearch)

    class FakeEncoder:
        def encode(self, text):
            return [0.1, 0.2]

    class FakePoint:
        payload = {"text": "matching chunk", "source": "doc.pdf"}
        score = 0.91

    class FakeClient:
        def collection_exists(self, collection):
            return True

        def search(self, **kwargs):
            self.kwargs = kwargs
            return [FakePoint()]

    search.client = FakeClient()
    search._encoder = FakeEncoder()

    result = search.search("query", top_k=3, collection="chunks")

    assert result[0].text == "matching chunk"
    assert result[0].score == 0.91
    assert result[0].metadata["source"] == "doc.pdf"
    assert result[0].method == "dense"
    assert search.client.kwargs == {
        "collection_name": "chunks",
        "query_vector": [0.1, 0.2],
        "limit": 3,
        "with_payload": True,
    }


def test_nemo_setup_injects_openrouter_chat_model(monkeypatch):
    from src import phase_c_guard

    calls = {}

    class FakeRailsConfig:
        @staticmethod
        def from_path(path):
            calls["path"] = path
            return "rails-config"

    class FakeLLMRails:
        def __init__(self, config, llm):
            calls["rails"] = (config, llm)

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            calls["chat_kwargs"] = kwargs

    nemoguardrails = types.ModuleType("nemoguardrails")
    nemoguardrails.RailsConfig = FakeRailsConfig
    nemoguardrails.LLMRails = FakeLLMRails
    chat_models = types.ModuleType("langchain_openai.chat_models")
    chat_models.ChatOpenAI = FakeChatOpenAI
    langchain_openai = types.ModuleType("langchain_openai")
    langchain_openai.__path__ = []
    monkeypatch.setitem(sys.modules, "nemoguardrails", nemoguardrails)
    monkeypatch.setitem(sys.modules, "langchain_openai", langchain_openai)
    monkeypatch.setitem(sys.modules, "langchain_openai.chat_models", chat_models)
    monkeypatch.setattr(phase_c_guard, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(phase_c_guard, "GENERATION_MODEL", "google/gemini-test")
    monkeypatch.setattr(phase_c_guard, "OPENROUTER_BASE_URL", "https://router.test/api/v1")

    phase_c_guard.setup_nemo_rails()

    assert calls["chat_kwargs"] == {
        "model": "google/gemini-test",
        "api_key": "test-key",
        "base_url": "https://router.test/api/v1",
        "temperature": 0,
    }
    assert calls["rails"][0] == "rails-config"


def _install_fake_ragas(monkeypatch, metric_rows, *, evaluate_error=None, metrics_hook=None):
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
        setattr(metrics_module, name, types.SimpleNamespace(llm=None, embeddings=None))

    llms_module = types.ModuleType("ragas.llms")
    llms_module.llm_factory = lambda model, base_url: types.SimpleNamespace(
        model=model, base_url=base_url
    )
    embeddings_module = types.ModuleType("ragas.embeddings")
    embeddings_module.HuggingfaceEmbeddings = lambda model_name: types.SimpleNamespace(
        model_name=model_name
    )

    def evaluate(dataset, *, metrics, llm, embeddings):
        if metrics_hook:
            metrics_hook(metrics, llm, embeddings)
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


def test_evaluate_ragas_overrides_stale_shared_metric_evaluators(monkeypatch):
    from src import m4_eval

    monkeypatch.setattr(m4_eval, "OPENROUTER_API_KEY", "configured-for-test")
    metric_names = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
    shared_metrics = {name: types.SimpleNamespace(llm="stale-llm", embeddings="stale-emb") for name in metric_names}
    captured = {}

    def capture(metrics, llm, embeddings):
        captured.update(metrics=metrics, llm=llm, embeddings=embeddings)

    _install_fake_ragas(
        monkeypatch,
        [{"faithfulness": .8, "answer_relevancy": .7, "context_precision": .6, "context_recall": .5}],
        metrics_hook=capture,
    )
    metrics_module = sys.modules["ragas.metrics"]
    for name, metric in shared_metrics.items():
        setattr(metrics_module, name, metric)

    result = m4_eval.evaluate_ragas(["Q"], ["A"], [["C"]], ["GT"])

    assert result["evaluation_status"] == "evaluated"
    assert captured["metrics"] != list(shared_metrics.values())
    assert all(metric.llm is captured["llm"] for metric in captured["metrics"])
    assert all(metric.embeddings is captured["embeddings"] for metric in captured["metrics"])


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
