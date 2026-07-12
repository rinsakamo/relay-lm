"""Markdown syntax round-trip and durability primitives."""

import pytest

from mdsqlite_spike import mdstore


def make_block(block_id="blk_test01", **overrides):
    defaults = dict(
        status="active",
        kind="fact",
        user_tags=("alpha", "beta"),
        system_tags=("auto",),
        source_refs=("conv:0001#3", "mem:blk_other1"),
        revision=2,
        updated="2026-07-12T00:00:01+00:00",
        content="The amber harbor holds a cedar anchor.",
    )
    defaults.update(overrides)
    return mdstore.Block(block_id=block_id, **defaults)


def test_render_parse_roundtrip():
    page = mdstore.Page(
        title="Round Trip",
        blocks=[make_block(), make_block("blk_test02", user_tags=(), content="Second.\n\nTwo paragraphs.")],
    )
    text = mdstore.render_page(page)
    reparsed = mdstore.parse_page(text)
    assert mdstore.render_page(reparsed) == text
    assert reparsed.title == "Round Trip"
    assert [b.block_id for b in reparsed.blocks] == ["blk_test01", "blk_test02"]
    assert reparsed.blocks[0].user_tags == ("alpha", "beta")
    assert reparsed.blocks[1].content == "Second.\n\nTwo paragraphs."


def test_rendering_is_deterministic():
    page = mdstore.Page(title="Det", blocks=[make_block()])
    assert mdstore.render_page(page) == mdstore.render_page(page)


def test_content_key_normalizes_case_and_whitespace():
    a = make_block(content="The  Amber   Harbor.")
    b = make_block(content="the amber harbor.")
    assert a.content_key() == b.content_key()
    assert a.normalized_text() == "the amber harbor."


def test_parse_rejects_duplicate_block_ids():
    text = mdstore.render_page(
        mdstore.Page(title="X", blocks=[make_block(), make_block()])
    )
    with pytest.raises(mdstore.MarkdownSyntaxError):
        mdstore.parse_page(text)


def test_parse_rejects_unterminated_block():
    text = mdstore.render_page(mdstore.Page(title="X", blocks=[make_block()]))
    truncated = text.rsplit("<!-- relaymem-spike:end -->", 1)[0]
    with pytest.raises(mdstore.MarkdownSyntaxError):
        mdstore.parse_page(truncated)


def test_atomic_replace_and_digest(tmp_path):
    target = tmp_path / "pages" / "topic.md"
    assert mdstore.file_digest(target) == mdstore.EMPTY_DIGEST
    mdstore.atomic_replace(target, "hello\n")
    assert target.read_text() == "hello\n"
    assert mdstore.file_digest(target) == mdstore.text_digest("hello\n")
    mdstore.atomic_replace(target, "world\n")
    assert target.read_text() == "world\n"
    assert not list(tmp_path.glob("**/*.spike-tmp"))


def test_syntax_is_labelled_experimental():
    text = mdstore.render_page(mdstore.Page(title="X", blocks=[make_block()]))
    assert "experimental" in text.splitlines()[0]
