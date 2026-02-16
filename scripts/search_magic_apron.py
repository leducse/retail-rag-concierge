#!/usr/bin/env python3
"""
Magic Apron — Day 2: Grounded Search (RAG) with Vertex AI

Supports two backends (set env to choose):
• RAG Engine (ragCorpora): set MAGIC_APRON_RAG_CORPUS to the full resource name.
  Example: projects/magic-apron-poc/locations/us-east5/ragCorpora/6917529027641081856
• Discovery Engine (data store): set MAGIC_APRON_DATA_STORE_ID + VERTEX_LOCATION.
"""

from __future__ import annotations

import os
from typing import Any

# --- Defaults (set via env) ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
LOCATION = os.environ.get("VERTEX_LOCATION", "global")
DATA_STORE_ID = os.environ.get("MAGIC_APRON_DATA_STORE_ID", "")
RAG_CORPUS = os.environ.get("MAGIC_APRON_RAG_CORPUS", "")


def _search_via_rag_engine(
    user_query: str,
    rag_corpus: str,
    project_id: str,
    location: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """Use Vertex AI RAG Engine (ragCorpora) + Gemini for grounded answer."""
    import vertexai
    from vertexai import rag
    from vertexai.generative_models import GenerativeModel, Tool

    vertexai.init(project=project_id, location=location)
    rag_retrieval_config = rag.RagRetrievalConfig(top_k=top_k)
    rag_retrieval_tool = Tool.from_retrieval(
        retrieval=rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[rag.RagResource(rag_corpus=rag_corpus)],
                rag_retrieval_config=rag_retrieval_config,
            ),
        ),
    )
    model = GenerativeModel(model_name="gemini-2.0-flash-001", tools=[rag_retrieval_tool])
    response = model.generate_content(user_query)
    out: dict[str, Any] = {"summary_text": None, "citations": [], "results": []}
    if response and response.text:
        out["summary_text"] = response.text
    if response and getattr(response, "candidates", None):
        for c in response.candidates:
            if getattr(c, "grounding_metadata", None) and getattr(c.grounding_metadata, "grounding_chunks", None):
                for chunk in c.grounding_metadata.grounding_chunks:
                    rc = getattr(chunk, "retrieved_context", None)
                    if rc is not None:
                        out["citations"].append(_serialize_retrieved_context(rc))
                    else:
                        out["citations"].append(str(chunk))
    return out


def _serialize_retrieved_context(rc: Any) -> dict[str, Any] | str:
    """Convert Vertex AI RetrievedContext (protobuf) to JSON-serializable dict."""
    try:
        d: dict[str, Any] = {}
        for attr in ("uri", "title", "text", "document_name"):
            if hasattr(rc, attr):
                val = getattr(rc, attr, None)
                if val is not None and not isinstance(val, (dict, list)):
                    d[attr] = str(val)
        return d if d else str(rc)
    except Exception:
        return str(rc)


def _search_via_discovery_engine(
    user_query: str,
    project_id: str,
    location: str,
    data_store_id: str,
    summary_result_count: int = 5,
) -> dict[str, Any]:
    """Use Discovery Engine (Vertex AI Search) data store for grounded search."""
    from google.cloud import discoveryengine_v1 as discoveryengine

    client = discoveryengine.SearchServiceClient()
    serving_config = client.serving_config_path(
        project=project_id,
        location=location,
        data_store=data_store_id,
        serving_config="default_search",
    )
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=user_query,
        content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                max_snippet_count=5,
                return_snippet=True,
            ),
            summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=summary_result_count,
                include_citations=True,
            ),
        ),
    )
    response = client.search(request=request)
    out: dict[str, Any] = {"summary_text": None, "citations": [], "results": []}
    if hasattr(response, "summary") and response.summary:
        if hasattr(response.summary, "summary_text"):
            out["summary_text"] = response.summary.summary_text
        if getattr(response.summary, "summary_with_metadata", None):
            sm = response.summary.summary_with_metadata
            if hasattr(sm, "summary"):
                out["summary_text"] = getattr(sm, "summary", None) or out["summary_text"]
            if getattr(sm, "citations", None):
                out["citations"] = list(sm.citations) if hasattr(sm.citations, "__iter__") else []
    for result in getattr(response, "results", []) or []:
        doc = getattr(result, "document", None)
        if doc and getattr(doc, "derived_struct_data", None):
            out["results"].append({"id": getattr(doc, "id", None), "snippet": doc.derived_struct_data})
    return out


def _location_from_rag_corpus(rag_corpus: str) -> str:
    """Extract location from projects/PROJECT/locations/LOCATION/ragCorpora/ID."""
    parts = rag_corpus.split("/")
    for i, p in enumerate(parts):
        if p == "locations" and i + 1 < len(parts):
            return parts[i + 1]
    return "us-central1"


def search_magic_apron(
    user_query: str,
    project_id: str | None = None,
    location: str | None = None,
    data_store_id: str | None = None,
    rag_corpus: str | None = None,
    summary_result_count: int = 5,
) -> dict[str, Any]:
    """
    Run a grounded search. Uses RAG Engine if MAGIC_APRON_RAG_CORPUS is set,
    otherwise Discovery Engine (MAGIC_APRON_DATA_STORE_ID).
    Returns summary_text, citations, and results.
    """
    project_id = project_id or PROJECT_ID
    location = location or LOCATION
    data_store_id = data_store_id or DATA_STORE_ID
    rag_corpus = rag_corpus or RAG_CORPUS

    if rag_corpus:
        if not project_id:
            raise ValueError("Set GOOGLE_CLOUD_PROJECT when using MAGIC_APRON_RAG_CORPUS")
        loc = location if location != "global" else _location_from_rag_corpus(rag_corpus)
        return _search_via_rag_engine(user_query, rag_corpus, project_id, loc, top_k=summary_result_count)
    if data_store_id and project_id:
        return _search_via_discovery_engine(
            user_query, project_id, location, data_store_id, summary_result_count
        )
    raise ValueError(
        "Set either MAGIC_APRON_RAG_CORPUS (RAG Engine) or "
        "GOOGLE_CLOUD_PROJECT + MAGIC_APRON_DATA_STORE_ID (Discovery Engine)."
    )


if __name__ == "__main__":
    import json
    q = "What do I need to fix a leaky faucet and which aisle?"
    print("Query:", q)
    try:
        result = search_magic_apron(q)
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print("Error (set GOOGLE_CLOUD_PROJECT, MAGIC_APRON_DATA_STORE_ID, and ADC):", e)
