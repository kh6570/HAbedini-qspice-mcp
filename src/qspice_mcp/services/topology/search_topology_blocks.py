"""Service performing keyword search across bundled topology blocks."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.topology._catalog import list_topology_index_entries


@dataclass(frozen=True, slots=True)
class TopologyBlockMatch:
    """One ranked keyword-search hit for a topology block."""

    block_id: str
    title: str
    category: str
    summary: str
    tags: tuple[str, ...]
    score: int
    matched_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopologyBlockSearchResult:
    """Keyword-search result set for one query."""

    query: str
    matches: tuple[TopologyBlockMatch, ...]


SERVICE_SPEC = ServiceSpec(
    name="search_topology_blocks",
    title="Search Topology Blocks",
    summary="Keyword-search bundled topology blocks by id, title, summary, category, and tags.",
    phase="implemented",
    read_only=True,
)


def _query_terms(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(term for term in query.lower().split() if term))


def search_topology_blocks(query: str) -> TopologyBlockSearchResult:
    """Return topology blocks matching any whitespace-separated keyword in ``query``."""

    normalized_query = query.strip()
    if not normalized_query:
        raise ValidationError("query must not be empty.")
    terms = _query_terms(normalized_query)

    matches: list[TopologyBlockMatch] = []
    for entry in list_topology_index_entries():
        haystacks = {
            "id": entry.block_id.lower().replace("_", " "),
            "title": entry.title.lower(),
            "summary": entry.summary.lower(),
            "category": entry.category.lower().replace("_", " "),
            "tags": " ".join(tag.lower() for tag in entry.tags),
        }
        combined = " ".join(haystacks.values())
        matched_terms = tuple(term for term in terms if term in combined)
        if not matched_terms:
            continue
        score = sum(combined.count(term) for term in matched_terms)
        matches.append(
            TopologyBlockMatch(
                block_id=entry.block_id,
                title=entry.title,
                category=entry.category,
                summary=entry.summary,
                tags=entry.tags,
                score=score,
                matched_terms=matched_terms,
            )
        )

    matches.sort(key=lambda match: (-match.score, match.block_id))
    return TopologyBlockSearchResult(query=normalized_query, matches=tuple(matches))


__all__ = [
    "SERVICE_SPEC",
    "TopologyBlockMatch",
    "TopologyBlockSearchResult",
    "search_topology_blocks",
]
