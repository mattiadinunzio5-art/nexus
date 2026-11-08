from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from nexus.core.config import Settings
from nexus.main import create_app


import os
import uuid

# Con NEXUS_TEST_PG (es. postgresql://postgres@localhost:5432/postgres) ogni test usa un database
# PostgreSQL nuovo, come nella versione online; altrimenti SQLite.
PG = os.environ.get("NEXUS_TEST_PG")


@pytest.fixture
def db_url(tmp_path):
    if not PG:
        yield f"sqlite:///{tmp_path / 'test.db'}"
        return
    from sqlalchemy import create_engine, text

    from nexus.database.session import normalize_url

    name = f"t_{uuid.uuid4().hex[:12]}"
    admin = create_engine(normalize_url(PG), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"CREATE DATABASE {name}"))
    yield PG.rsplit("/", 1)[0] + "/" + name
    with admin.connect() as c:
        c.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
    admin.dispose()


@pytest.fixture
def settings(tmp_path, db_url) -> Settings:
    return Settings(
        env="test",
        database_url=db_url,
        auto_migrate=True,
        data_dir=tmp_path / "data",
        secret_key="test-secret-key-for-unit-tests-only",
    )


@pytest.fixture
def client(settings):
    app = create_app(settings)
    with TestClient(app) as c:  # esegue lifespan: migrazioni + bootstrap
        yield c


@pytest.fixture
def db(client):
    with client.app.state.database.session_factory() as session:
        yield session
