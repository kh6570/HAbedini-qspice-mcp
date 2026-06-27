"""Service performing lexical (TF-IDF) retrieval across bundled topology blocks."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.topology._search_index import _tokenize, search_topology_index

_DEFAULT_LIMIT = 10


@dataclass(frozen=True, slots=True)
class TopologyBlockMatch:
    """One ranked retrieval hit for a topology block."""

    block_id: str
    title: str
    category: str
    summary: str
    tags: tuple[str, ...]
    score: float
    matched_terms: tuple[str, ...]
    matched_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopologyBlockSearchResult:
    """Retrieval result set for one query."""

    query: str
    matches: tuple[TopologyBlockMatch, ...]


SERVICE_SPEC = ServiceSpec(
    name="search_topology_blocks",
    title="Search Topology Blocks",
    summary=(
        "Lexical TF-IDF search over bundled topology blocks across id, title, summary, "
        "category, tags, control notes, ports, parameters, equations, and blueprint text."
    ),
    phase="implemented",
    read_only=True,
)


def search_topology_blocks(query: str, limit: int = _DEFAULT_LIMIT) -> TopologyBlockSearchResult:
    """Rank bundled topology blocks against ``query`` by TF-IDF cosine relevance.

    The corpus for each block spans the catalog index fields plus the manifest detail
    (control notes, ports, parameters, design equations) and the clean-room blueprint
    document, so a term that appears only in the blueprint still matches. ``score`` is a
    cosine similarity in ``[0, 1]``; ``matched_fields`` reports where query terms landed.
    """

    normalized_query = query.strip()
    if not normalized_query:
        raise ValidationError("query must not be empty.")
    query_tokens = tuple(_tokenize(normalized_query))
    effective_limit = limit if limit and limit > 0 else _DEFAULT_LIMIT

    hits = search_topology_index(query_tokens, limit=effective_limit)
    matches = tuple(
        TopologyBlockMatch(
            block_id=hit.block_id,
            title=hit.title,
            category=hit.category,
            summary=hit.summary,
            tags=hit.tags,
            score=hit.score,
            matched_terms=hit.matched_terms,
            matched_fields=hit.matched_fields,
        )
        for hit in hits
    )
    return TopologyBlockSearchResult(query=normalized_query, matches=matches)


__all__ = [
    "SERVICE_SPEC",
    "TopologyBlockMatch",
    "TopologyBlockSearchResult",
    "search_topology_blocks",
]
