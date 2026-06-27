"""Pure-stdlib lexical (TF-IDF) retrieval index over the bundled topology corpus.

This module builds a small TF-IDF index whose corpus, per topology block, is the
union of the catalog index fields, the manifest detail (summary, control notes,
ports, parameters, design equations) and the clean-room blueprint document. It is
lexical retrieval only — no neural embeddings or external model weights — so it
stays offline and clean-room friendly.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import cache

from qspice_mcp.core.exceptions import QSpiceError
from qspice_mcp.services.topology._catalog import (
    list_topology_index_entries,
    load_topology_manifest,
    read_topology_document,
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# Corpus field names, kept stable so callers can surface ``matched_fields``.
_FIELD_ID = "id"
_FIELD_TITLE = "title"
_FIELD_SUMMARY = "summary"
_FIELD_CATEGORY = "category"
_FIELD_TAGS = "tags"
_FIELD_CONTROL_NOTES = "control_notes"
_FIELD_PORTS = "ports"
_FIELD_PARAMETERS = "parameters"
_FIELD_DESIGN_EQUATIONS = "design_equations"
_FIELD_BLUEPRINT = "blueprint"


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into alphanumeric tokens (splits hyphens/underscores)."""

    return _TOKEN_PATTERN.findall(text.lower())


def _join_object_list(entries: object, keys: tuple[str, ...]) -> str:
    """Flatten a manifest list-of-objects field into a single searchable string."""

    if not isinstance(entries, list):
        return ""
    parts: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for key in keys:
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value)
    return " ".join(parts)


@dataclass(frozen=True, slots=True)
class _BlockDocument:
    """One topology block flattened into searchable per-field text."""

    block_id: str
    title: str
    category: str
    summary: str
    tags: tuple[str, ...]
    field_tokens: dict[str, tuple[str, ...]]
    term_frequencies: dict[str, int]


@dataclass(frozen=True, slots=True)
class TopologyIndexHit:
    """One ranked retrieval hit produced by the topology search index."""

    block_id: str
    title: str
    category: str
    summary: str
    tags: tuple[str, ...]
    score: float
    matched_terms: tuple[str, ...]
    matched_fields: tuple[str, ...]


def _build_block_document(
    block_id: str, title: str, category: str, summary: str, tags: tuple[str, ...]
) -> _BlockDocument:
    """Assemble the per-field token map for one topology block."""

    field_text: dict[str, str] = {
        _FIELD_ID: block_id.replace("_", " "),
        _FIELD_TITLE: title,
        _FIELD_CATEGORY: category.replace("_", " "),
        _FIELD_SUMMARY: summary,
        _FIELD_TAGS: " ".join(tags),
    }
    try:
        manifest = load_topology_manifest(block_id)
    except QSpiceError:
        manifest = {}
    control_notes = manifest.get("control_notes")
    field_text[_FIELD_CONTROL_NOTES] = control_notes if isinstance(control_notes, str) else ""
    field_text[_FIELD_PORTS] = _join_object_list(
        manifest.get("ports"), ("name", "role", "description")
    )
    field_text[_FIELD_PARAMETERS] = _join_object_list(
        manifest.get("parameters"), ("name", "description", "unit")
    )
    field_text[_FIELD_DESIGN_EQUATIONS] = _join_object_list(
        manifest.get("design_equations"), ("name", "expression", "description")
    )
    document_name = manifest.get("document")
    blueprint_text = ""
    if isinstance(document_name, str) and document_name.strip():
        try:
            blueprint_text = read_topology_document(block_id, document_name)
        except QSpiceError:
            blueprint_text = ""
    field_text[_FIELD_BLUEPRINT] = blueprint_text

    field_tokens: dict[str, tuple[str, ...]] = {}
    term_frequencies: dict[str, int] = {}
    for field, text in field_text.items():
        tokens = _tokenize(text)
        field_tokens[field] = tuple(tokens)
        for token in tokens:
            term_frequencies[token] = term_frequencies.get(token, 0) + 1
    return _BlockDocument(
        block_id=block_id,
        title=title,
        category=category,
        summary=summary,
        tags=tags,
        field_tokens=field_tokens,
        term_frequencies=term_frequencies,
    )


@dataclass(frozen=True, slots=True)
class _SearchIndex:
    """Immutable TF-IDF index over all topology blocks."""

    documents: tuple[_BlockDocument, ...]
    idf: dict[str, float]
    doc_vectors: dict[str, dict[str, float]]
    doc_norms: dict[str, float]


def _compute_idf(documents: tuple[_BlockDocument, ...]) -> dict[str, float]:
    total = len(documents)
    document_frequency: dict[str, int] = {}
    for document in documents:
        for token in document.term_frequencies:
            document_frequency[token] = document_frequency.get(token, 0) + 1
    return {
        token: math.log((total + 1) / (frequency + 1)) + 1.0
        for token, frequency in document_frequency.items()
    }


def _tfidf_vector(term_frequencies: dict[str, int], idf: dict[str, float]) -> dict[str, float]:
    return {
        token: count * idf.get(token, 0.0)
        for token, count in term_frequencies.items()
        if idf.get(token, 0.0) > 0.0
    }


def _vector_norm(vector: dict[str, float]) -> float:
    return math.sqrt(sum(weight * weight for weight in vector.values()))


@cache
def build_topology_search_index() -> _SearchIndex:
    """Build (and memoize) the TF-IDF index over the bundled topology corpus."""

    documents = tuple(
        _build_block_document(
            entry.block_id, entry.title, entry.category, entry.summary, entry.tags
        )
        for entry in list_topology_index_entries()
    )
    idf = _compute_idf(documents)
    doc_vectors: dict[str, dict[str, float]] = {}
    doc_norms: dict[str, float] = {}
    for document in documents:
        vector = _tfidf_vector(document.term_frequencies, idf)
        doc_vectors[document.block_id] = vector
        doc_norms[document.block_id] = _vector_norm(vector)
    return _SearchIndex(
        documents=documents,
        idf=idf,
        doc_vectors=doc_vectors,
        doc_norms=doc_norms,
    )


def clear_search_index_cache() -> None:
    """Clear the memoized search index (kept in sync with the topology root cache)."""

    build_topology_search_index.cache_clear()


def _matched_fields(document: _BlockDocument, query_tokens: set[str]) -> tuple[str, ...]:
    matched: list[str] = []
    for field, tokens in document.field_tokens.items():
        if query_tokens.intersection(tokens):
            matched.append(field)
    return tuple(matched)


def search_topology_index(
    query_tokens: tuple[str, ...], *, limit: int
) -> tuple[TopologyIndexHit, ...]:
    """Rank topology blocks against ``query_tokens`` by TF-IDF cosine similarity."""

    index = build_topology_search_index()
    query_tf: dict[str, int] = {}
    for token in query_tokens:
        query_tf[token] = query_tf.get(token, 0) + 1
    query_vector = _tfidf_vector(query_tf, index.idf)
    query_norm = _vector_norm(query_vector)
    query_token_set = set(query_tokens)

    hits: list[TopologyIndexHit] = []
    for document in index.documents:
        matched_terms = tuple(
            token for token in dict.fromkeys(query_tokens) if token in document.term_frequencies
        )
        if not matched_terms:
            continue
        doc_vector = index.doc_vectors[document.block_id]
        doc_norm = index.doc_norms[document.block_id]
        if query_norm <= 0.0 or doc_norm <= 0.0:
            score = 0.0
        else:
            dot = sum(weight * doc_vector.get(token, 0.0) for token, weight in query_vector.items())
            score = dot / (query_norm * doc_norm)
        hits.append(
            TopologyIndexHit(
                block_id=document.block_id,
                title=document.title,
                category=document.category,
                summary=document.summary,
                tags=document.tags,
                score=round(score, 6),
                matched_terms=matched_terms,
                matched_fields=_matched_fields(document, query_token_set),
            )
        )

    hits.sort(key=lambda hit: (-hit.score, hit.block_id))
    if limit > 0:
        hits = hits[:limit]
    return tuple(hits)


__all__ = [
    "TopologyIndexHit",
    "build_topology_search_index",
    "clear_search_index_cache",
    "search_topology_index",
]
