"""Coda persistente della War Room: presa in carico unica, ripresa dopo un'interruzione, tentativi, tempo massimo."""

from datetime import timedelta

import pytest

from nexus.agents import workflow
from nexus.database.base import utcnow
from nexus.models import ResearchRun, User
from nexus.services import jobs


@pytest.fixture
def env(client):
    app = client.app
    client.post("/api/documents", files={"file": ("bw.txt", b"Bretton Woods fixed the dollar to gold at 35 dollars an ounce in 1944.\n" * 3)},
                data={"title": "Bretton Woods", "category": "source_material"})
    return app.state.database, app.state.settings


def _new_run(db, **kw) -> ResearchRun:
    u = db.query(User).first()
    run = ResearchRun(owner_id=u.id, question="Che cosa decise Bretton Woods sul dollaro e l'oro?", mode="local", **kw)
    db.add(run)
    db.commit()
    return run


def test_run_is_claimed_once_and_completes(env):
    database, settings = env
    with database.session_factory() as db:
        rid = _new_run(db).id
        assert jobs.claim(db, rid) is not None
        assert jobs.claim(db, rid) is None  # già presa: nessuna doppia esecuzione
        db.get(ResearchRun, rid).status = "queued"
        db.commit()
    assert jobs.process(database, settings, rid)
    with database.session_factory() as db:
        run = db.get(ResearchRun, rid)
        assert run.status == "awaiting_approval" and run.attempts == 2  # la prima presa in carico conta come tentativo
        assert run.checkpoint_phases == ["plan", "research", "analysis", "skeptic"]


def test_interrupted_run_resumes_from_checkpoint(env, monkeypatch):
    database, settings = env
    with database.session_factory() as db:
        rid = _new_run(db).id
    # Primo tentativo: il server «cade» durante l'analisi (dopo piano e ricerca salvati).
    calls = {"plan": 0}
    real_plan, real_analysis = workflow.Runner.plan, workflow.Runner.analysis

    def counting_plan(self):
        calls["plan"] += 1
        return real_plan(self)

    def crash(self, evidence):
        raise KeyboardInterrupt  # simula l'arresto del processo: niente gestione degli errori

    monkeypatch.setattr(workflow.Runner, "plan", counting_plan)
    monkeypatch.setattr(workflow.Runner, "analysis", crash)
    with pytest.raises(KeyboardInterrupt):
        jobs.process(database, settings, rid)
    with database.session_factory() as db:
        run = db.get(ResearchRun, rid)
        assert run.status == "running" and run.checkpoint_phases == ["plan", "research"]
        steps_before = len(run.steps)
        assert jobs.requeue_interrupted(db) == 1  # riavvio del server
    monkeypatch.setattr(workflow.Runner, "analysis", real_analysis)
    assert jobs.process(database, settings, rid)
    with database.session_factory() as db:
        run = db.get(ResearchRun, rid)
        assert run.status == "awaiting_approval" and run.attempts == 2
        assert calls["plan"] == 1  # la pianificazione non è stata ripetuta
        assert len(run.steps) > steps_before and [s.ordinal for s in run.steps] == list(range(1, len(run.steps) + 1))


def test_stale_running_run_is_taken_over(env):
    database, settings = env
    with database.session_factory() as db:
        rid = _new_run(db, status="running", heartbeat_at=utcnow() - timedelta(seconds=jobs.LEASE_SECONDS + 5)).id
    assert jobs.process(database, settings)  # il worker la trova da solo
    with database.session_factory() as db:
        assert db.get(ResearchRun, rid).status == "awaiting_approval"


def test_temporary_errors_are_retried_then_fail(env, monkeypatch):
    database, settings = env
    with database.session_factory() as db:
        rid = _new_run(db).id

    def boom(self):
        raise workflow.RetryableError("servizio non raggiungibile")

    monkeypatch.setattr(workflow.Runner, "plan", boom)
    assert jobs.process(database, settings, rid)
    with database.session_factory() as db:
        run = db.get(ResearchRun, rid)
        assert run.status == "queued" and "nuovo tentativo" in run.error
        run.next_attempt_at = None
        db.commit()
    for _ in range(jobs.MAX_ATTEMPTS):
        jobs.process(database, settings, rid)
        with database.session_factory() as db:
            run = db.get(ResearchRun, rid)
            if run.status == "queued":
                run.next_attempt_at = None
                db.commit()
    with database.session_factory() as db:
        run = db.get(ResearchRun, rid)
        assert run.status == "failed" and f"{jobs.MAX_ATTEMPTS} tentativi" in run.error


def test_run_over_time_limit_is_closed(env):
    database, settings = env
    with database.session_factory() as db:
        run = _new_run(db)
        run.created_at = utcnow() - jobs.RUN_TIMEOUT - timedelta(minutes=1)
        db.commit()
        rid = run.id
    jobs.process(database, settings, rid)
    with database.session_factory() as db:
        run = db.get(ResearchRun, rid)
        assert run.status == "failed" and "Tempo massimo" in run.error


def test_api_run_reports_queue_state(client):
    client.post("/api/documents", files={"file": ("bw.txt", b"Bretton Woods fixed the dollar to gold in 1944.\n" * 3)},
                data={"title": "BW", "category": "source_material"})
    r = client.post("/api/research/runs", json={"question": "Bretton Woods e il dollaro"})
    assert r.status_code == 202
    run = client.get(f"/api/research/runs/{r.json()['id']}").json()
    assert run["status"] == "awaiting_approval" and run["attempts"] == 1 and "analysis" in run["checkpoint_phases"]
