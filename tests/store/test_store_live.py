"""Store tests against a real Postgres. Needs Docker; skipped from the offline
suite by the `store` marker (see pyproject.toml's pytest markers and the
`not store and not live` deselect used by pre-commit and CI).

Run explicitly with: pytest -m store
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from alembic.config import Config as AlembicConfig
from testcontainers.community.postgres import PostgresContainer

from alembic import command
from scholium import doctor
from scholium.config import Config
from scholium.runs import run_context
from scholium.store import accessors
from scholium.store.db import connection
from scholium.store.records import (
    CandidateRecord,
    LabelRecord,
    PaperEmbeddingRecord,
    PaperRecord,
    ProjectRecord,
    RunRecord,
)

pytestmark = pytest.mark.store

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def pg_dsn() -> str:
    with PostgresContainer("pgvector/pgvector:pg17", driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="module")
def migrated_config(pg_dsn: str) -> Config:
    config = Config(store={"dsn": pg_dsn})
    alembic_cfg = AlembicConfig(str(REPO_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", pg_dsn)
    alembic_cfg.attributes["configure_logger"] = False
    command.upgrade(alembic_cfg, "head")
    return config


def test_migration_creates_pgvector_extension(migrated_config: Config):
    with connection(migrated_config) as conn:
        row = conn.execute(
            __import__("sqlalchemy").text(
                "select extversion from pg_extension where extname = 'vector'"
            )
        ).one_or_none()
    assert row is not None


def test_upsert_paper_inserts_new_row(migrated_config: Config):
    record = PaperRecord(id="doi:10.1/abc", doi="10.1/abc", title="First title", year=2020)
    with connection(migrated_config) as conn:
        accessors.upsert_paper(conn, record)
        fetched = accessors.get_paper(conn, "doi:10.1/abc")
    assert fetched is not None
    assert fetched.title == "First title"
    assert fetched.year == 2020


def test_upsert_paper_never_overwrites_filled_field_with_empty(migrated_config: Config):
    """The rule from CLAUDE.md, tested against a real database: a later
    upsert with an empty title must not blank out a title already stored."""
    paper_id = "doi:10.1/merge-case"
    with connection(migrated_config) as conn:
        accessors.upsert_paper(
            conn, PaperRecord(id=paper_id, doi="10.1/merge-case", title="Real Title", abstract=None)
        )
        accessors.upsert_paper(
            conn,
            PaperRecord(id=paper_id, doi="10.1/merge-case", title="", abstract="A real abstract"),
        )
        fetched = accessors.get_paper(conn, paper_id)
    assert fetched.title == "Real Title"  # not blanked by the empty-string upsert
    assert fetched.abstract == "A real abstract"  # the previously-empty field did fill in


def test_upsert_paper_fills_a_previously_null_field(migrated_config: Config):
    paper_id = "doi:10.1/fill-case"
    with connection(migrated_config) as conn:
        accessors.upsert_paper(conn, PaperRecord(id=paper_id, doi="10.1/fill-case", venue=None))
        accessors.upsert_paper(
            conn, PaperRecord(id=paper_id, doi="10.1/fill-case", venue="NeurIPS")
        )
        fetched = accessors.get_paper(conn, paper_id)
    assert fetched.venue == "NeurIPS"


def test_nearest_papers_orders_by_cosine_distance(migrated_config: Config):
    dim = 768
    with connection(migrated_config) as conn:
        for i, id_ in enumerate(["p1", "p2", "p3"]):
            accessors.upsert_paper(conn, PaperRecord(id=id_, title=f"Paper {i}"))
        base = [1.0] + [0.0] * (dim - 1)
        close = [0.99] + [0.01] * (dim - 1)
        far = [0.0, 1.0] + [0.0] * (dim - 2)
        accessors.upsert_paper_embedding(
            conn, PaperEmbeddingRecord(paper_id="p1", model_name="specter2", vector=base, dim=dim)
        )
        accessors.upsert_paper_embedding(
            conn, PaperEmbeddingRecord(paper_id="p2", model_name="specter2", vector=close, dim=dim)
        )
        accessors.upsert_paper_embedding(
            conn, PaperEmbeddingRecord(paper_id="p3", model_name="specter2", vector=far, dim=dim)
        )
        results = accessors.nearest_papers(conn, base, model_name="specter2", limit=3)
    ordered_ids = [paper_id for paper_id, _ in results]
    assert ordered_ids[0] == "p1"
    assert ordered_ids[1] == "p2"
    assert ordered_ids[2] == "p3"


def test_end_to_end_smoke(migrated_config: Config):
    """Plan section 5.3: search, upsert 10 papers, embed, store, read back."""
    dim = 768
    with connection(migrated_config) as conn:
        project = accessors.create_project(
            conn, ProjectRecord(name=f"smoke-{uuid4().hex[:8]}", problem_statement="test")
        )
        run = accessors.insert_run(conn, RunRecord(project_id=project.id, tool="find"))

        paper_ids = []
        for i in range(10):
            paper_id = f"titlehash:smoke{i:02d}"
            accessors.upsert_paper(
                conn, PaperRecord(id=paper_id, title=f"Smoke test paper {i}", year=2020 + i % 5)
            )
            accessors.upsert_paper_embedding(
                conn,
                PaperEmbeddingRecord(
                    paper_id=paper_id,
                    model_name="specter2",
                    vector=[float(i)] + [0.0] * (dim - 1),
                    dim=dim,
                ),
            )
            accessors.upsert_candidate(
                conn,
                CandidateRecord(
                    project_id=project.id, paper_id=paper_id, run_id=run.id, fusion_score=1.0
                ),
            )
            paper_ids.append(paper_id)

        accessors.upsert_label(
            conn, LabelRecord(project_id=project.id, paper_id=paper_ids[0], label="relevant")
        )
        accessors.finish_run(conn, run.id, status="finished", stats={"candidates": 10})

        fetched = [accessors.get_paper(conn, pid) for pid in paper_ids]

    assert len(fetched) == 10
    assert all(p is not None for p in fetched)
    assert {p.title for p in fetched} == {f"Smoke test paper {i}" for i in range(10)}


def test_run_context_records_finished_run_with_snapshot(migrated_config: Config):
    with run_context(migrated_config, tool="find") as run:
        run.stats["candidates"] = 42
        run_id = run.record.id
    with connection(migrated_config) as conn:
        row = conn.execute(
            __import__("sqlalchemy")
            .text("select status, stats, config_snapshot, git_hash from run where id = :id")
            .bindparams(id=run_id)
        ).one()
    assert row.status == "finished"
    assert row.stats == {"candidates": 42}
    assert row.config_snapshot is not None


def test_run_context_marks_failed_run_on_exception_even_though_the_tools_own_writes_roll_back(
    migrated_config: Config,
):
    """The bug this guards against: the failed-run row must survive even when
    the tool body's own writes, sharing a *different* connection and rolled
    back by that connection's own error handling, do not."""
    run_id = None
    with pytest.raises(RuntimeError), run_context(migrated_config, tool="find") as run:
        run.stats["partial"] = True
        run_id = run.record.id
        # Simulate the tool doing its own substantive DB work on its own
        # connection, which then fails and rolls back that connection's
        # transaction. This must not touch the run row above.
        with connection(migrated_config) as tool_conn:
            accessors.upsert_paper(tool_conn, PaperRecord(id="doi:10.1/rollback-case"))
            raise RuntimeError("boom")
    with connection(migrated_config) as conn:
        row = conn.execute(
            __import__("sqlalchemy")
            .text("select status, stats from run where id = :id")
            .bindparams(id=run_id)
        ).one()
        rolled_back_paper = accessors.get_paper(conn, "doi:10.1/rollback-case")
    assert row.status == "failed"
    assert row.stats == {"partial": True}
    assert rolled_back_paper is None  # the tool's own write really did roll back


def test_doctor_check_store_reports_row_counts_and_last_run(migrated_config: Config):
    with connection(migrated_config) as conn:
        accessors.upsert_paper(conn, PaperRecord(id="doi:10.1/doctor-case", title="X"))
    with run_context(migrated_config, tool="find"):
        pass

    checks = doctor.check_store(migrated_config)
    by_name = {c.name: c for c in checks}
    assert by_name["postgres"].status == doctor.OK
    assert by_name["pgvector"].status == doctor.OK
    assert "paper=" in by_name["store row counts"].detail
    assert "find:" in by_name["last run per tool"].detail
