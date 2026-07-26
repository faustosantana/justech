"""Evidence collector — aggregates support per destination without early selection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.analysis_engine.relationship_graph import RelationshipGraph
from app.lottery.numeric_relations.analysis_engine.schemas import (
    CandidateEvidence,
    DerivationPath,
    EdgeType,
)


def _fingerprint(origin: int, dest: int, rel: str, depth: int) -> str:
    return f"{origin}|{dest}|{rel}|{depth}"


def collect_all_evidence(
    graph: RelationshipGraph,
    *,
    catalog: TableCatalog | None = None,
    derivation_paths: list[DerivationPath] | None = None,
) -> dict[int, CandidateEvidence]:
    """
    Collect evidence for every reachable destination.

    Does not decide which candidate is fuerte.
    Deduplicates identical path fingerprints so evidence is not inflated.
    """
    if not graph.complete:
        raise RuntimeError(
            "NO_EARLY_CANDIDATE_SELECTION: graph must be complete before evidence collection"
        )

    cat = catalog or build_catalog()
    observed = set(graph.observed_numbers)
    by_dest: dict[int, CandidateEvidence] = {}
    fps_by_dest: dict[int, set[str]] = defaultdict(set)

    def bucket(n: int) -> CandidateEvidence:
        if n not in by_dest:
            by_dest[n] = CandidateEvidence(candidate_number=n)
        return by_dest[n]

    for e in graph.edges:
        dest = int(e.target.split(":")[1])
        if dest in observed:
            # destination equal to another observed is allowed but tracked
            pass
        origin = int(e.observed_origin) if e.observed_origin is not None else int(
            e.source.split(":")[1]
        )
        fp = _fingerprint(origin, dest, e.relation_type, e.depth)
        ev = bucket(dest)
        if fp in fps_by_dest[dest]:
            ev.same_source_repetitions += 1
            continue
        fps_by_dest[dest].add(fp)
        ev.path_fingerprints.append(fp)
        ev.total_path_count += 1
        if origin not in ev.supporting_observed_numbers:
            ev.supporting_observed_numbers.append(origin)

        if e.relation_type == EdgeType.T1_MOTHER_RELATION.value and e.depth == 0:
            if origin not in ev.table1_sources:
                ev.table1_sources.append(origin)
            ev.direct_path_count += 1
            if dest not in ev.table1_companions:
                ev.table1_companions.append(dest)
        elif e.relation_type == EdgeType.T2_CONFIRMATION.value and e.depth == 0:
            if origin not in ev.table2_sources:
                ev.table2_sources.append(origin)
            if origin not in ev.direct_confirmers:
                ev.direct_confirmers.append(origin)
            ev.direct_path_count += 1
        elif e.relation_type == EdgeType.T2_NEIGHBOR.value and e.depth == 0:
            if origin not in ev.table2_sources:
                ev.table2_sources.append(origin)
            if dest not in ev.table2_neighbors:
                ev.table2_neighbors.append(dest)
            # Observed → neighbor destination (direct T2 signal toward dest)
            ev.direct_path_count += 1
        elif e.relation_type in {
            EdgeType.DERIVATION_LEVEL_1.value,
            EdgeType.DERIVATION_LEVEL_2.value,
        }:
            if origin not in ev.indirect_confirmers:
                ev.indirect_confirmers.append(origin)

    for p in derivation_paths or []:
        ev = bucket(p.destination)
        ev.derivation_paths.append(p.to_dict())

    # Cross / multi-source / independence
    for dest, ev in by_dest.items():
        ev.table1_sources = sorted(set(ev.table1_sources))
        ev.table2_sources = sorted(set(ev.table2_sources))
        ev.direct_confirmers = sorted(set(ev.direct_confirmers))
        ev.supporting_observed_numbers = sorted(set(ev.supporting_observed_numbers))
        ev.cross_table_support = bool(ev.table1_sources and ev.direct_confirmers)
        ev.multi_source_support = len(ev.supporting_observed_numbers) >= 2

        # Independent paths ≈ distinct (origin, relation_family) pairs at depth 0
        families: set[str] = set()
        for fp in ev.path_fingerprints:
            origin_s, _dest_s, rel, depth_s = fp.split("|")
            if depth_s == "0" and rel in {
                EdgeType.T1_MOTHER_RELATION.value,
                EdgeType.T2_CONFIRMATION.value,
            }:
                families.add(f"{origin_s}:{rel}")
        # Also count direct T2 neighbor paths from distinct origins when no T1
        for fp in ev.path_fingerprints:
            origin_s, _d, rel, depth_s = fp.split("|")
            if depth_s == "0" and rel == EdgeType.T2_NEIGHBOR.value:
                families.add(f"{origin_s}:T2_NEIGHBOR")
        ev.independent_path_count = len(families)

        # Ambiguity placeholder filled by discovery/ranker with peer context
        try:
            ev.table2_neighbors = list(cat.get_table2_neighbors(dest, exclude_self=True))
        except KeyError:
            pass

    return by_dest


def attach_historical_profile(
    evidence: CandidateEvidence,
    profile: dict[str, Any] | None,
) -> CandidateEvidence:
    if not profile:
        return evidence
    for k, v in profile.items():
        if hasattr(evidence, k) and v is not None:
            setattr(evidence, k, v)
    return evidence
