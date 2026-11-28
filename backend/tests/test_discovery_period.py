"""Discovery: le anomalie restano nel periodo della domanda; messaggi chiari quando l'AI non risponde."""
from nexus.agents import llm
from nexus.discovery.core import in_period, query_period


def test_period_from_question_years():
    assert query_period("Il Piano Marshall 1947-1952 e la crescita europea") == [1947, 1952]
    assert query_period("Effetti del 1929 sulle banche") == [1929, 1929]


def test_period_from_events_only_if_narrow():
    assert query_period("Piano Marshall", [1947, 1948, 1951]) == [1947, 1951]
    assert query_period("Storia della moneta", [1259, 2022]) is None
    assert query_period("Domanda senza anni") is None


def test_anomaly_inside_or_outside_period():
    p = [1947, 1952]
    assert in_period("1948-03", p)
    assert in_period("1945–1946", p)        # tocca il margine di 2 anni
    assert not in_period("1259", p)
    assert not in_period("2022-01-01", p)
    assert in_period("", p)                 # senza anni: non si esclude


def test_http_errors_are_explained():
    m = llm._http_message(404, '{"error":{"code":"model_not_found"}}', "llama-3.3-70b-versatile")
    assert "llama-3.3-70b-versatile" in m and "Sistema → Credenziali" in m and "HTTP 404" in m
    assert "temporaneo" in llm._http_message(503, "down")
    assert "URL" in llm._http_message(404, "<html>page</html>")


# --- Filtro del periodo su tutte le anomalie, cronologia compresa (Runner reale) ---------------------

import pytest
from sqlalchemy import select

from nexus.api.schemas_history import RelationIn
from nexus.discovery import anomalies as an
from nexus.discovery.core import Runner
from nexus.models import DiscoveryAnomaly, DiscoverySession, Entity, User
from nexus.services import graph

from .test_discovery import _event


@pytest.fixture
def user(db):
    return db.scalar(select(User))


def _reversed_relation(db, user, effect_year: int, cause_year: int, tag: str):
    """Relazione «causa → effetto» con la causa DOPO l'effetto: chronology_issues la segnala con period «effetto–causa»."""
    effect = _event(db, user, f"Effetto {tag}", effect_year)
    cause = _event(db, user, f"Causa {tag}", cause_year)
    ec, ee = (db.scalar(select(Entity).where(Entity.event_id == x.id)) for x in (cause, effect))
    graph.create_relation(db, user, RelationIn(source_entity_id=ec.id, target_entity_id=ee.id, relation_type="caused",
                                               provenance="user_hypothesis"))


def _run_anomalies(db, user, period):
    sess = DiscoverySession(owner_id=user.id, mode="guided", query="Piano Marshall",
                            scope={"restricted": False, **({"period": period} if period else {})}, limits={"max_items": 60})
    db.add(sess)
    db.commit()
    r = Runner(db, sess, user, None, None)
    r.step_anomalies(0.0)
    db.commit()
    titles = [a.title for a in db.scalars(select(DiscoveryAnomaly).where(DiscoveryAnomaly.session_id == sess.id))]
    return titles, sess.steps[-1]


def test_chronology_issues_follow_the_question_period(db, user):
    _reversed_relation(db, user, 1948, 1950, "dentro")       # 1948–1950: nel periodo 1947–1952
    _reversed_relation(db, user, 1800, 1810, "fuori")        # lontano dal periodo
    _reversed_relation(db, user, 1944, 1945, "bordo-basso")  # tocca 1945 = 1947 − 2: incluso
    _reversed_relation(db, user, 1943, 1944, "oltre-basso")  # finisce nel 1944 < 1945: escluso
    _reversed_relation(db, user, 1954, 1955, "bordo-alto")   # inizia nel 1954 = 1952 + 2: incluso
    _reversed_relation(db, user, 1955, 1956, "oltre-alto")   # inizia nel 1955 > 1954: escluso
    titles, step = _run_anomalies(db, user, [1947, 1952])
    text = " | ".join(titles)
    for tag in ("dentro", "bordo-basso", "bordo-alto"):
        assert f"Causa {tag}" in text, tag
    for tag in ("fuori", "oltre-basso", "oltre-alto"):
        assert f"Causa {tag}" not in text, tag
    assert step["counts"]["outside_period"] == 3
    assert "Escluse 3 anomalie fuori dal periodo" in step["summary"]


def test_without_period_every_chronology_issue_is_kept(db, user):
    _reversed_relation(db, user, 1948, 1950, "a")
    _reversed_relation(db, user, 1800, 1810, "b")
    titles, step = _run_anomalies(db, user, None)
    assert len([t for t in titles if "Ordine temporale" in t]) == 2
    assert "outside_period" not in step["counts"]


def test_anomaly_without_dates_is_kept_with_a_period(db, user, monkeypatch):
    undated = an.AnomalyCandidate(kind="chronology", title="Anomalia senza data", what_changed="", reference="", period="",
                                  data={}, alternatives=[], refs={}, relevance=1.0, verifiability="medium", keys=["senza-data"])
    monkeypatch.setattr(an, "chronology_issues", lambda *a, **k: [undated])
    titles, step = _run_anomalies(db, user, [1947, 1952])
    assert "Anomalia senza data" in titles
    assert "outside_period" not in step["counts"]


def test_query_period_with_many_years_spans_all_of_them():
    # Più anni nella domanda: l'intervallo va dal più piccolo al più grande, quindi non può restringersi
    # rispetto a nessuno degli anni citati (aggiungerne uno lo allarga o lo lascia uguale).
    assert query_period("Piano Marshall 1947, 1948 e 1952") == [1947, 1952]
    assert query_period("Dal 1929 al 1933, confrontato con il 2008") == [1929, 2008]
    one, many = query_period("Crisi del 1929"), query_period("Crisi del 1929 e New Deal del 1933")
    assert many[0] <= one[0] and many[1] >= one[1]
