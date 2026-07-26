"""Configurable derivation engine (depth capped at 2)."""

from __future__ import annotations

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.analysis_engine.relationship_graph import RelationshipGraph
from app.lottery.numeric_relations.analysis_engine.schemas import (
    DerivationPath,
    EdgeType,
    NodeType,
    new_id,
)


def _path_fingerprint(route: list[int], types: list[str]) -> str:
    return "→".join(f"{a}:{t}" for a, t in zip(route[:-1], types)) + f"→{route[-1]}"


def apply_derivations(
    graph: RelationshipGraph,
    *,
    catalog: TableCatalog | None = None,
    max_depth: int = 2,
    max_paths: int = 500,
) -> list[DerivationPath]:
    """
    Expand direct T1 destinations by +1 / +2 hops using T2 neighbors and
    T1 mother relations. Depth hard-capped at 2. Fan-out limited.
    """
    cat = catalog or build_catalog()
    depth_cap = max(0, min(int(max_depth), 2))
    paths: list[DerivationPath] = []
    seen_fp: set[str] = set()

    if depth_cap == 0:
        graph.mark_complete()
        return paths

    # Seeds: only direct T1 mother destinations (official geometry axis)
    seeds: list[tuple[int, int, list[int], list[str], list[str]]] = []
    for e in graph.edges:
        if e.depth != 0:
            continue
        if e.relation_type != EdgeType.T1_MOTHER_RELATION.value:
            continue
        src = int(e.source.split(":")[1])
        tgt = int(e.target.split(":")[1])
        origin = int(e.observed_origin) if e.observed_origin is not None else src
        seeds.append((origin, tgt, [src, tgt], [e.relation_type], ["table1"]))

    def _record(
        origin: int,
        current: int,
        dest: int,
        route: list[int],
        rel_types: list[str],
        tables: list[str],
        level: int,
        rel: str,
        table: str,
    ) -> bool:
        if len(paths) >= max_paths:
            return False
        if dest in route:
            return True
        new_route = route + [dest]
        new_types = rel_types + [rel]
        new_tables = tables + [table]
        fp = _path_fingerprint(new_route, new_types)
        independent = fp not in seen_fp
        if not independent:
            return True
        seen_fp.add(fp)
        edge_type = (
            EdgeType.DERIVATION_LEVEL_1 if level == 1 else EdgeType.DERIVATION_LEVEL_2
        )
        graph.add_edge(
            current,
            dest,
            edge_type,
            table_type=table,
            observed_origin=origin,
            depth=level,
            direct_or_indirect="indirect",
            source_node_type=NodeType.DERIVED,
            target_node_type=NodeType.DERIVED,
            route=new_route,
        )
        paths.append(
            DerivationPath(
                path_id=new_id("der"),
                route=new_route,
                observed_origin=origin,
                tables_used=new_tables,
                relation_types=new_types,
                depth=level,
                destination=dest,
                hops=len(new_route) - 1,
                independent=independent,
                reuses_nodes=len(new_route) != len(set(new_route)),
                forms_cycle=False,
            )
        )
        return True

    # Level 1: from each T1 destination, take T2 neighbors (bounded)
    level1_nodes: list[tuple[int, int, list[int], list[str], list[str]]] = []
    for origin, tgt, route, types, tables in seeds:
        neighbors = cat.get_table2_neighbors(tgt, exclude_self=True)[:8]
        for dest in neighbors:
            ok = _record(
                origin, tgt, dest, route, types, tables, 1, EdgeType.T2_NEIGHBOR.value, "table2"
            )
            if not ok:
                break
            level1_nodes.append(
                (origin, dest, route + [dest], types + [EdgeType.T2_NEIGHBOR.value], tables + ["table2"])
            )
        if len(paths) >= max_paths:
            break

    # Level 2: one more hop via T1 mother of level-1 node (bounded)
    if depth_cap >= 2:
        for origin, cur, route, types, tables in level1_nodes[:200]:
            comps = cat.get_table1_companions(cur)[:5]
            for dest in comps:
                if not _record(
                    origin,
                    cur,
                    dest,
                    route,
                    types,
                    tables,
                    2,
                    EdgeType.T1_MOTHER_RELATION.value,
                    "table1",
                ):
                    break
            if len(paths) >= max_paths:
                break

    graph.mark_complete()
    return paths


def derivation_depth_penalty(depth: int) -> float:
    return {0: 0.0, 1: 2.0, 2: 5.0}.get(int(depth), 8.0)
