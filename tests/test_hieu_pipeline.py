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
