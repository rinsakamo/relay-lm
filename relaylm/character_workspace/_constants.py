"""CW-A1 Character Workspace constants."""
from __future__ import annotations

SCHEMA_VERSION = "relaylm.character_workspace.v0"
MAX_SOURCE_FILE_BYTES = 512 * 1024
MAX_MANIFEST_ENTRIES = 4096

REQUIRED_SOURCE_FILENAMES = (
    "SOUL.md",
    "STYLE.md",
    "EMOTION.md",
    "SCENE.md",
    "RELATIONSHIP.md",
    "MEMORY.md",
    "BOUNDARY.md",
)
OPTIONAL_SOURCE_FILENAMES = ("LORE.md",)

LOWERCASE_WORKSPACE_DIRECTORIES = (
    "relationships",
    "relationships/_inbox",
    "scenes",
    "scenes/_inbox",
    "memory",
    "memory/people",
    "memory/projects",
    "memory/topics",
    "memory/episodes",
    "memory/inbox",
    "memory/forgotten",
)
PROPOSAL_DIRECTORIES = (
    "proposals/soul",
    "proposals/style",
    "proposals/emotion",
    "proposals/scene",
    "proposals/relationship",
    "proposals/memory",
    "proposals/boundary",
)
INTERNAL_DIRECTORIES = (
    ".relaylm/sources/conversations",
    ".relaylm/sources/corrections",
    ".relaylm/sources/imports",
    ".relaylm/state",
    ".relaylm/build",
    ".relaylm/indexes",
    ".relaylm/projections",
    ".relaylm/audit",
    ".relaylm/queue",
)
RESERVED_DIRECTORY_PATHS = (
    *LOWERCASE_WORKSPACE_DIRECTORIES,
    "proposals",
    *PROPOSAL_DIRECTORIES,
    ".relaylm",
    ".relaylm/sources",
    *INTERNAL_DIRECTORIES,
)
INTERNAL_STATE_FILES = (
    ".relaylm/state/scene_state.json",
    ".relaylm/state/emotion_state.json",
    ".relaylm/state/relationship_state_cache.json",
)
INTERNAL_BUILD_FILES = (
    ".relaylm/build/character_manifest.json",
    ".relaylm/build/style_projection.json",
    ".relaylm/build/emotion_projection.json",
    ".relaylm/build/scene_units.jsonl",
    ".relaylm/build/relationship_projection.json",
    ".relaylm/build/memory_units.jsonl",
    ".relaylm/build/context_projection.json",
    ".relaylm/build/links.jsonl",
)
PROPOSAL_DOMAINS = frozenset({"soul", "style", "emotion", "scene", "relationship", "memory", "boundary"})
SOURCE_KIND_BY_FILENAME = {
    filename: filename.removesuffix(".md").lower()
    for filename in REQUIRED_SOURCE_FILENAMES + OPTIONAL_SOURCE_FILENAMES
}
