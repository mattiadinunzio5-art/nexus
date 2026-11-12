"""Knowledge Graph: entità, relazioni con provenienza, esplorazione con NetworkX."""

from __future__ import annotations

import networkx as nx
from sqlalchemy import func, or_, select, union_all
from sqlalchemy.orm import Session

from ..api.schemas_history import EntityIn, GraphNode, GraphOut, PathOut, RelationIn, RelationOut
from ..core import library
from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..models import Document, DocumentChunk, Entity, Relation, Source, User
from ..research.citations import format_citation
from . import activity

PROVENANCE_LABEL = {
    "sourced": "Documentata",
    "user_hypothesis": "Ipotesi dell'utente",
    "ai_hypothesis": "Ipotesi generata dall'AI — da verificare",
}


def relation_out(db: Session, r: Relation) -> RelationOut:
    out = RelationOut.model_validate(r)
    if r.source_id:
        s = db.get(Source, r.source_id)
        out.evidence_label = format_citation(s) if s else "Fonte eliminata"
    elif r.chunk_id:
        c = db.get(DocumentChunk, r.chunk_id)
        out.evidence_label = f"{c.document.title}, {c.locator}" if c else "Passaggio eliminato"
    else:
        out.evidence_label = PROVENANCE_LABEL[r.provenance]
    return out


def get_entity(db: Session, user: User, entity_id: int, own: bool = False) -> Entity:
    return library.access(db, user, db.get(Entity, entity_id), own, "Entità non trovata.")


def list_entities(db: Session, user: User, q: str | None = None, entity_type: str | None = None, limit: int = 500) -> list[Entity]:
    stmt = select(Entity).where(Entity.owner_id.in_(library.visible_owner_ids(db, user)))
    if q:
        stmt = stmt.where(Entity.name.ilike(f"%{q}%"))
    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
    return list(db.scalars(stmt.order_by(Entity.name).limit(limit)))


def create_entity(db: Session, user: User, data: EntityIn, is_demo: bool = False) -> Entity:
    if data.entity_type == "event":
        raise ValidationFailedError("Le entità di tipo evento si creano dall'archivio storico.")
    if data.document_id is not None:
        d = db.get(Document, data.document_id)
        if d is None or d.owner_id != user.id:
            raise ValidationFailedError("Documento inesistente.")
    from ..discovery.kg import find_entity

    dup = find_entity(db, user, data.name, data.entity_type) or next(
        (x for a in data.aliases if (x := find_entity(db, user, a, data.entity_type))), None)
    if dup:
        raise ValidationFailedError(f"Entità già presente nel grafo: «{dup.name}» (#{dup.id}). Usa quella o aggiungi un alias.",
                                    details={"existing_id": dup.id})
    e = Entity(owner_id=user.id, is_demo=is_demo, **data.model_dump())
    db.add(e)
    db.flush()
    activity.record(db, user=user, actor="user", action="entity.create", entity_type="entity", entity_id=e.id,
                    summary=f"Creata l'entità «{e.name}» ({e.entity_type})")
    db.commit()
    db.refresh(e)
    return e


def update_entity(db: Session, user: User, entity_id: int, data: EntityIn) -> Entity:
    e = get_entity(db, user, entity_id, own=True)
    if e.event_id is not None:
        raise ValidationFailedError("Questa entità rappresenta un evento: modificala dalla scheda evento.")
    from ..discovery.kg import find_entity

    dup = find_entity(db, user, data.name, data.entity_type, exclude_id=e.id)
    if dup:
        raise ValidationFailedError(f"Esiste già un'entità con questo nome: «{dup.name}» (#{dup.id}).", details={"existing_id": dup.id})
    for k, v in data.model_dump().items():
        setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return e


def delete_entity(db: Session, user: User, entity_id: int, confirm: bool) -> None:
    e = get_entity(db, user, entity_id, own=True)
    if e.event_id is not None:
        raise ValidationFailedError("Questa entità rappresenta un evento: eliminala dall'archivio storico.")
    if not confirm:
        raise ConfirmationRequiredError("Eliminare un'entità e le sue relazioni richiede conferma (confirm=true).")
    db.delete(e)
    activity.record(db, user=user, actor="user", action="entity.delete", entity_type="entity", entity_id=entity_id,
                    summary=f"Eliminata l'entità «{e.name}»")
    db.commit()


def _check_evidence(db: Session, user: User, source_id: int | None, chunk_id: int | None) -> None:
    if source_id is not None:
        s = db.get(Source, source_id)
        if s is None or not library.can_read(db, user, s.owner_id):
            raise ValidationFailedError("Fonte inesistente.")
    if chunk_id is not None:
        c = db.get(DocumentChunk, chunk_id)
        if c is None or c.owner_id != user.id:
            raise ValidationFailedError("Passaggio di documento inesistente.")


def create_relation(db: Session, user: User, data: RelationIn, *, ai_run_id: int | None = None, provenance_override: str | None = None) -> Relation:
    get_entity(db, user, data.source_entity_id)
    get_entity(db, user, data.target_entity_id)
    _check_evidence(db, user, data.source_id, data.chunk_id)
    values = data.model_dump()
    if provenance_override:
        values["provenance"] = provenance_override
    dup = db.scalar(
        select(Relation).where(
            Relation.owner_id == user.id, Relation.source_entity_id == data.source_entity_id,
            Relation.target_entity_id == data.target_entity_id, Relation.relation_type == data.relation_type,
            Relation.provenance == values["provenance"],
        )
    )
    if dup:
        raise ValidationFailedError("Relazione già presente.")
    r = Relation(owner_id=user.id, ai_run_id=ai_run_id, **values)
    db.add(r)
    db.flush()
    activity.record(db, user=user, actor="ai" if ai_run_id else "user", action="relation.create", entity_type="relation", entity_id=r.id,
                    summary=f"Nuova relazione «{r.relation_type}» ({PROVENANCE_LABEL[r.provenance]})")
    db.commit()
    db.refresh(r)
    return r


def delete_relation(db: Session, user: User, relation_id: int) -> None:
    r = db.get(Relation, relation_id)
    if r is None or r.owner_id != user.id:
        raise NotFoundError("Relazione non trovata.")
    db.delete(r)
    activity.record(db, user=user, actor="user", action="relation.delete", entity_type="relation", entity_id=relation_id,
                    summary="Eliminata una relazione del grafo")
    db.commit()


def relations_of(db: Session, user: User, entity_id: int) -> list[Relation]:
    return list(
        db.scalars(
            select(Relation).where(
                Relation.owner_id.in_(library.visible_owner_ids(db, user)),
                or_(Relation.source_entity_id == entity_id, Relation.target_entity_id == entity_id),
            )
        )
    )


MAX_EDGES = 4000  # limite di relazioni caricate per una vista (la Biblioteca può contenerne centinaia di migliaia)


def _rel_filter(db: Session, user: User, relation_types: list[str] | None, provenance: list[str] | None):
    conds = [Relation.owner_id.in_(library.visible_owner_ids(db, user))]
    if relation_types:
        conds.append(Relation.relation_type.in_(relation_types))
    if provenance:
        conds.append(Relation.provenance.in_(provenance))
    return conds


def _neighbourhood(db: Session, user: User, focus: int, depth: int, conds, max_nodes: int) -> set[int]:
    """Visita in ampiezza fatta con query SQL, senza caricare l'intero grafo in memoria."""
    seen, frontier = {focus}, {focus}
    for _ in range(max(0, depth)):
        if not frontier or len(seen) >= max_nodes:
            break
        rows = db.execute(
            select(Relation.source_entity_id, Relation.target_entity_id)
            .where(*conds, or_(Relation.source_entity_id.in_(frontier), Relation.target_entity_id.in_(frontier)))
            .limit(MAX_EDGES)
        ).all()
        nxt = set()
        for a, b in rows:
            for n in (a, b):
                if n not in seen and len(seen) + len(nxt) < max_nodes:
                    nxt.add(n)
        seen |= nxt
        frontier = nxt
    return seen


def _top_by_degree(db: Session, user: User, conds, limit: int) -> list[int]:
    ends = union_all(
        select(Relation.source_entity_id.label("e")).where(*conds),
        select(Relation.target_entity_id.label("e")).where(*conds),
    ).subquery()
    return [r[0] for r in db.execute(select(ends.c.e).group_by(ends.c.e).order_by(func.count().desc()).limit(limit))]


def _graph(db: Session, user: User, relation_types: list[str] | None, provenance: list[str] | None, nodes: set[int] | None = None):
    g = nx.MultiDiGraph()
    conds = _rel_filter(db, user, relation_types, provenance)
    stmt = select(Relation).where(*conds)
    if nodes is not None:
        stmt = stmt.where(Relation.source_entity_id.in_(nodes), Relation.target_entity_id.in_(nodes))
    rels = list(db.scalars(stmt.limit(MAX_EDGES)))
    ids = set(nodes or ()) | {r.source_entity_id for r in rels} | {r.target_entity_id for r in rels}
    entities = {e.id: e for e in db.scalars(select(Entity).where(Entity.id.in_(ids)))} if ids else {}
    for e in entities.values():
        g.add_node(e.id)
    for r in rels:
        if r.source_entity_id in entities and r.target_entity_id in entities:
            g.add_edge(r.source_entity_id, r.target_entity_id, key=r.id)
    return g, entities, {r.id: r for r in rels}


def explore(
    db: Session, user: User, *, focus: int | None, depth: int, relation_types: list[str] | None,
    provenance: list[str] | None, entity_types: list[str] | None, max_nodes: int = 300,
) -> GraphOut:
    conds = _rel_filter(db, user, relation_types, provenance)
    owners = library.visible_owner_ids(db, user)
    if focus is not None:
        get_entity(db, user, focus)
        keep = _neighbourhood(db, user, focus, depth, conds, max_nodes)
    else:
        # Senza focus: le entità più collegate (fino al limite); se non ci sono relazioni, le prime entità.
        keep = set(_top_by_degree(db, user, conds, max_nodes))
        if not keep:
            keep = set(db.scalars(select(Entity.id).where(Entity.owner_id.in_(owners)).order_by(Entity.id).limit(max_nodes)))
    g, entities, rels = _graph(db, user, relation_types, provenance, keep)
    keep = {n for n in keep if n in entities}
    if entity_types:
        keep = {n for n in keep if entities[n].entity_type in entity_types or n == focus}
    keep = set(sorted(keep, key=lambda n: -g.degree(n))[:max_nodes])
    sub = g.subgraph(keep)
    simple = nx.Graph(sub.to_undirected())
    pos = nx.spring_layout(simple, seed=42, k=None) if len(simple) > 1 else {n: (0.0, 0.0) for n in simple}
    btw = nx.betweenness_centrality(simple) if 2 < len(simple) <= 400 else {n: 0.0 for n in simple}
    nodes = [
        GraphNode(id=n, name=entities[n].name, entity_type=entities[n].entity_type, x=float(pos[n][0]), y=float(pos[n][1]),
                  degree=int(sub.degree(n)), betweenness=round(float(btw.get(n, 0.0)), 4), is_focus=n == focus)
        for n in sub.nodes
    ]
    edge_rels = [rels[k] for _, _, k in sub.edges(keys=True)]
    src_ids = {r.source_id for r in edge_rels if r.source_id}
    # Una sola query per le fonti delle relazioni (niente N+1 sul database remoto); la lista le tiene nella identity map.
    loaded = list(db.scalars(select(Source).where(Source.id.in_(src_ids)))) if src_ids else []
    edges = [relation_out(db, r) for r in edge_rels]
    del loaded
    stats = {
        "entities": db.scalar(select(func.count(Entity.id)).where(Entity.owner_id.in_(owners))) or 0,
        "relations": db.scalar(select(func.count(Relation.id)).where(*conds)) or 0,
        "shown_nodes": len(nodes), "shown_edges": len(edges),
        "components": nx.number_connected_components(simple) if len(simple) else 0,
        "by_provenance": {p: sum(1 for e in edges if e.provenance == p) for p in PROVENANCE_LABEL},
    }
    return GraphOut(nodes=nodes, edges=edges, stats=stats)


def path(db: Session, user: User, a: int, b: int, max_depth: int = 6, max_visited: int = 20000) -> PathOut:
    """Percorso più breve con visita in ampiezza via SQL (limitata in profondità e nodi visitati)."""
    get_entity(db, user, a)
    get_entity(db, user, b)
    conds = _rel_filter(db, user, None, None)
    parent: dict[int, tuple[int, int] | None] = {a: None}
    frontier = {a}
    for _ in range(max_depth):
        if b in parent or not frontier or len(parent) > max_visited:
            break
        rows = db.execute(
            select(Relation.id, Relation.source_entity_id, Relation.target_entity_id)
            .where(*conds, or_(Relation.source_entity_id.in_(frontier), Relation.target_entity_id.in_(frontier)))
            .order_by(Relation.id)
        ).all()
        nxt = set()
        for rid, u, v in rows:
            for x, y in ((u, v), (v, u)):
                if x in frontier and y not in parent:
                    parent[y] = (x, rid)
                    nxt.add(y)
        frontier = nxt
    if b not in parent:
        return PathOut(found=False, entity_ids=[], relations=[])
    nodes, rel_ids, cur = [b], [], b
    while parent[cur] is not None:
        prev, rid = parent[cur]
        rel_ids.append(rid)
        nodes.append(prev)
        cur = prev
    nodes.reverse()
    rel_ids.reverse()
    rels = {r.id: r for r in db.scalars(select(Relation).where(Relation.id.in_(rel_ids)))}
    return PathOut(found=True, entity_ids=nodes, relations=[relation_out(db, rels[r]) for r in rel_ids])
