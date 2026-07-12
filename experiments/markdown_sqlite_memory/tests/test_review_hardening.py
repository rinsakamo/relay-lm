"""Regression coverage for independent PR review hardening findings."""

import argparse
import sqlite3

import pytest

from mdsqlite_spike import cache, cli, mdstore, ops, search, slp
from mdsqlite_spike.slp import Candidate


def _block(**overrides):
    values = dict(
        block_id="blk_review",
        status="active",
        kind="fact",
        revision=1,
        updated="2026-07-13T00:00:00+00:00",
        content="review fixture",
    )
    values.update(overrides)
    return mdstore.Block(**values)


def test_noncanonical_page_is_rejected_before_lossy_normalization():
    text = mdstore.render_page(mdstore.Page(title="Review", blocks=[_block()]))
    edited = text.replace("# Review\n", "# Review\n\nuser-authored prose\n", 1)

    with pytest.raises(mdstore.MarkdownSyntaxError, match="lossy"):
        mdstore.parse_page(edited, "review.md")


def test_render_rejects_metadata_and_reserved_marker_injection():
    with pytest.raises(mdstore.MarkdownSyntaxError, match="single line"):
        mdstore.render_block(_block(kind="fact\n- status: hidden"))

    with pytest.raises(mdstore.MarkdownSyntaxError, match="leading/trailing"):
        mdstore.render_block(_block(user_tags=(" padded ",)))

    with pytest.raises(mdstore.MarkdownSyntaxError, match="reserved"):
        mdstore.render_block(
            _block(content="safe\n<!-- relaymem-spike:end -->\nunsafe")
        )


def test_atomic_replace_handles_short_writes_and_cleans_temp(tmp_path, monkeypatch):
    real_write = mdstore.os.write

    def short_write(fd, data):
        return real_write(fd, data[:3])

    monkeypatch.setattr(mdstore.os, "write", short_write)
    target = tmp_path / "pages" / "short-write.md"
    mdstore.atomic_replace(target, "abcdefghijk\n")

    assert target.read_text(encoding="utf-8") == "abcdefghijk\n"
    assert not list(target.parent.glob("*.spike-tmp"))


def test_japanese_query_filters_instead_of_degrading_to_all_rows(seeded_env):
    result = slp.apply_candidate(
        seeded_env,
        Candidate(
            candidate_id="review-japanese",
            page="japanese.md",
            content="私はコーヒーが好きです。",
        ),
    )
    assert result.outcome == "applied"

    conn = seeded_env.open_cache()
    hits = search.execute_search(
        conn, search.plan_search("コーヒー"), count_usage=False
    )
    conn.close()

    assert [hit.block_id for hit in hits] == [result.block_id]


def test_non_token_query_matches_none_and_terms_are_length_bounded(seeded_env):
    conn = seeded_env.open_cache()
    assert search.execute_search(
        conn, search.plan_search("!!!"), count_usage=False
    ) == []
    conn.close()

    plan = search.SearchPlan(terms=("x" * 10_000,)).bounded()
    assert len(plan.terms[0]) == search.MAX_TERM_LENGTH


def test_fts_quotes_and_page_prefix_wildcards_are_literal(seeded_env):
    conn = seeded_env.open_cache()
    assert search.execute_search(
        conn,
        search.SearchPlan(terms=('kw0x1" OR *',)),
        count_usage=False,
    ) == []
    assert search.execute_search(
        conn,
        search.plan_search("", page_prefix="topic_00_"),
        count_usage=False,
    ) == []
    conn.close()


@pytest.mark.parametrize(
    "page",
    ("../outside.md", "/tmp/outside.md", "notes.txt", r"..\outside.md"),
)
def test_cli_rejects_page_paths_outside_the_markdown_root(page):
    with pytest.raises(argparse.ArgumentTypeError):
        cli._validated_page_rel(page)

    assert cli._validated_page_rel("nested/notes.md") == "nested/notes.md"


def test_cache_rejects_invalid_schema_metadata(tmp_path):
    db_path = tmp_path / "bad-cache.db"
    conn = cache.open_cache(db_path)
    conn.execute(
        "UPDATE schema_meta SET value = 'not-an-integer' "
        "WHERE key = 'schema_version'"
    )
    conn.close()

    with pytest.raises(cache.CacheCorruptError, match="invalid schema_version"):
        cache.open_cache(db_path)

    # The failed opener released its handle; the corrupt cache can be removed
    # and rebuilt instead of remaining locked by a leaked connection.
    db_path.unlink()


def test_ops_rejects_unsupported_and_invalid_schema_versions(tmp_path):
    db_path = tmp_path / "bad-ops.db"
    conn = ops.connect(db_path)
    conn.execute(
        "UPDATE schema_meta SET value = '0' WHERE key = 'schema_version'"
    )
    conn.close()

    with pytest.raises(ops.OpsSchemaVersionError, match="older than supported"):
        ops.connect(db_path)

    raw = sqlite3.connect(db_path)
    raw.execute(
        "UPDATE schema_meta SET value = 'not-an-integer' "
        "WHERE key = 'schema_version'"
    )
    raw.commit()
    raw.close()

    with pytest.raises(ops.OpsSchemaVersionError, match="invalid version"):
        ops.connect(db_path)

    # Both rejected open attempts close their connections.
    db_path.unlink()
