"""Directed relationship graph — built fully before candidate discovery."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.analysis_engine.input_normalizer import unique_observed
from app.lottery.numeric_relations.analysis_engine.schemas import (
    ENGINE_VERSION,
    TABLE_VERSION,
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
    new_id,
)


class RelationshipGraph:
    """Auditable directed graph. Discovery must wait until ``complete`` is True."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._edge_keys: set[str] = set()
        self.complete: bool = False
        self.observed_numbers: list[int] = []
        self.engine_version = ENGINE_VERSION
        self.table_version = TABLE_VERSION

    def node_key(self, number: int, role: str = "n") -> str:
        return f"{role}:{int(number)}"

    def ensure_node(self, number: int, node_type: NodeType | str, **meta: Any) -> str:
        key = self.node_key(number)
        if key not in self.nodes:
            nt = node_type.value if isinstance(node_type, NodeType) else str(node_type)
            self.nodes[key] = GraphNode(
                node_id=key, number=int(number), node_type=nt, meta=dict(meta)
            )
        else:
            self.nodes[key].meta.update(meta)
        return key

    def add_edge(
        self,
        source_number: int,
        target_number: int,
        relation_type: EdgeType | str,
        *,
        table_type: str | None,
        observed_origin: int | None,
        depth: int,
        direct_or_indirect: str,
        source_node_type: NodeType | str | None = None,
        target_node_type: NodeType | str | None = None,
        date: str | None = None,
        lottery: str | None = None,
        position: str | None = None,
        **meta: Any,
    ) -> GraphEdge | None:
        rt = relation_type.value if isinstance(relation_type, EdgeType) else str(relation_type)
        src = self.ensure_node(
            source_number, source_node_type or NodeType.RELATED_T1
        )
        tgt = self.ensure_node(
            target_number, target_node_type or NodeType.RELATED_T1
        )
        key = f"{src}|{tgt}|{rt}|{observed_origin}|{depth}"
        if key in self._edge_keys:
            return None
        self._edge_keys.add(key)
        edge = GraphEdge(
            evidence_id=new_id("ev"),
            source=src,
            target=tgt,
            relation_type=rt,
            table_type=table_type,
            observed_origin=observed_origin,
            depth=int(depth),
            direct_or_indirect=direct_or_indirect,
            date=date,
            lottery=lottery,
            position=position,
            meta=dict(meta),
        )
        self.edges.append(edge)
        return edge

    def mark_complete(self) -> None:
        self.complete = True

    def edges_of_type(self, *types: str) -> list[GraphEdge]:
        wanted = set(types)
        return [e for e in self.edges if e.relation_type in wanted]

    def outgoing(self, number: int) -> list[GraphEdge]:
        key = self.node_key(number)
        return [e for e in self.edges if e.source == key]

    def incoming(self, number: int) -> list[GraphEdge]:
        key = self.node_key(number)
        return [e for e in self.edges if e.target == key]

    def to_dict(self) -> dict[str, Any]:
        return {
            "complete": self.complete,
            "observed_numbers": list(self.observed_numbers),
            "engine_version": self.engine_version,
            "table_version": self.table_version,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }


def build_complete_relationship_graph(
    observed_numbers: list[int],
    *,
    catalog: TableCatalog | None = None,
    derivation_depth: int = 2,
    date: str | None = None,
    lottery: str | None = None,
    position: str | None = None,
) -> RelationshipGraph:
    """
    Build the FULL relationship graph for ALL observed numbers.

    Does NOT select candidates. Candidate discovery must run only after
    ``graph.complete`` is True.
    """
    cat = catalog or build_catalog()
    graph = RelationshipGraph()
    observed = unique_observed(observed_numbers)
    graph.observed_numbers = list(observed)

    for o in observed:
        graph.ensure_node(o, NodeType.OBSERVED, role="observed")

        # --- Tabla 1 mother relations (o as mother code) ---
        companions = list(cat.get_table1_companions(o))
        for c in companions:
            graph.add_edge(
                o,
                c,
                EdgeType.T1_MOTHER_RELATION,
                table_type="table1",
                observed_origin=o,
                depth=0,
                direct_or_indirect="direct",
                source_node_type=NodeType.OBSERVED,
                target_node_type=NodeType.RELATED_T1,
                date=date,
                lottery=lottery,
                position=position,
            )
            graph.add_edge(
                o,
                c,
                EdgeType.T1_COMPANION,
                table_type="table1",
                observed_origin=o,
                depth=0,
                direct_or_indirect="direct",
                source_node_type=NodeType.OBSERVED,
                target_node_type=NodeType.COMPANION_T1,
                date=date,
                lottery=lottery,
                position=position,
            )

        # --- Tabla 2 neighbors of observed ---
        neighbors = list(cat.get_table2_neighbors(o, exclude_self=True))
        for n in neighbors:
            graph.add_edge(
                o,
                n,
                EdgeType.T2_NEIGHBOR,
                table_type="table2",
                observed_origin=o,
                depth=0,
                direct_or_indirect="direct",
                source_node_type=NodeType.OBSERVED,
                target_node_type=NodeType.NEIGHBOR_T2,
                date=date,
                lottery=lottery,
                position=position,
            )

        # --- T2 confirmation edges: observed confirmer → T1 destination ---
        # For each T1 destination of ANY generator, if this observed is neighbor of dest
        for gen in observed:
            for cand in cat.get_table1_companions(gen):
                t2_of_cand = set(cat.get_table2_neighbors(cand, exclude_self=True))
                if o in t2_of_cand and o != gen:
                    graph.add_edge(
                        o,
                        cand,
                        EdgeType.T2_CONFIRMATION,
                        table_type="table2",
                        observed_origin=o,
                        depth=0,
                        direct_or_indirect="direct",
                        source_node_type=NodeType.OBSERVED,
                        target_node_type=NodeType.RELATED_T2,
                        date=date,
                        lottery=lottery,
                        position=position,
                        confirmed_via_generator=gen,
                    )
                    graph.add_edge(
                        gen,
                        cand,
                        EdgeType.CROSS_CONFIRMATION,
                        table_type="table1+table2",
                        observed_origin=gen,
                        depth=0,
                        direct_or_indirect="direct",
                        source_node_type=NodeType.OBSERVED,
                        target_node_type=NodeType.CANDIDATE,
                        date=date,
                        lottery=lottery,
                        position=position,
                        confirmer=o,
                    )

    # Multi-source support markers (still not selecting winners)
    dest_sources: dict[int, set[int]] = {}
    for e in graph.edges:
        if e.relation_type in {
            EdgeType.T1_MOTHER_RELATION.value,
            EdgeType.T2_CONFIRMATION.value,
            EdgeType.T2_NEIGHBOR.value,
        }:
            tgt = int(e.target.split(":")[1])
            if e.observed_origin is not None:
                dest_sources.setdefault(tgt, set()).add(int(e.observed_origin))
    for dest, sources in dest_sources.items():
        if len(sources) >= 2:
            for src in sources:
                graph.add_edge(
                    src,
                    dest,
                    EdgeType.MULTI_SOURCE_SUPPORT,
                    table_type="cross",
                    observed_origin=src,
                    depth=0,
                    direct_or_indirect="direct",
                    source_node_type=NodeType.OBSERVED,
                    target_node_type=NodeType.CANDIDATE,
                    supporting_sources=sorted(sources),
                )

    # Derivations appended by derivation_engine (caller may also call it).
    # Mark incomplete until derivations applied OR depth==0.
    if derivation_depth <= 0:
        graph.mark_complete()
    return graph
