"""Deterministic synthetic Markdown fixtures. No user data, no LLM."""

from __future__ import annotations

import random

from . import mdstore
from .slp import SpikeEnv

_WORDS = (
    "amber basil cedar delta ember fjord garnet harbor indigo juniper "
    "krypton lumen meadow nectar onyx prism quartz russet saffron topaz "
    "umber violet willow xenon yarrow zephyr anchor bramble copper drift"
).split()

_KINDS = ("fact", "preference", "event")
_USER_TAGS = ("alpha", "beta", "gamma", "delta")
_SYSTEM_TAGS = ("auto", "curated")


def _sentence(rnd: random.Random, marker: str) -> str:
    words = [rnd.choice(_WORDS) for _ in range(rnd.randint(6, 12))]
    words.insert(rnd.randrange(len(words)), marker)
    return " ".join(words) + "."


def init_fixture(
    env: SpikeEnv, pages: int = 5, blocks_per_page: int = 8, seed: int = 1
) -> dict:
    """Write multi-memory synthetic pages; returns fixture statistics.

    Every block carries a unique marker token ``kw<p>x<b>`` so search
    assertions and benchmarks can target one specific memory.
    """
    rnd = random.Random(seed)
    total_blocks = 0
    for p in range(pages):
        blocks = []
        for b in range(blocks_per_page):
            marker = f"kw{p}x{b}"
            block_id = f"blk_p{p}b{b}"
            refs = [f"conv:{p:04d}#{b}"]
            if b > 0:
                refs.append(f"mem:blk_p{p}b{b - 1}")
            blocks.append(
                mdstore.Block(
                    block_id=block_id,
                    status="active",
                    kind=_KINDS[b % len(_KINDS)],
                    user_tags=(_USER_TAGS[b % len(_USER_TAGS)],),
                    system_tags=(_SYSTEM_TAGS[p % len(_SYSTEM_TAGS)],),
                    source_refs=tuple(refs),
                    revision=1,
                    updated=env.now(),
                    content=_sentence(rnd, marker),
                )
            )
            total_blocks += 1
        page = mdstore.Page(title=f"Fixture Topic {p}", blocks=blocks)
        mdstore.atomic_replace(
            env.page_path(f"topic_{p:03d}.md"), mdstore.render_page(page)
        )
    return {"pages": pages, "blocks": total_blocks, "seed": seed}
