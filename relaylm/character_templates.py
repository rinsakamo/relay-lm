"""CW-A5 public template registry facade."""
from __future__ import annotations

from relaylm.character_creation import (
    TEMPLATE_REGISTRY_SCHEMA_VERSION,
    CharacterTemplateRecord,
    get_character_template,
    list_character_templates,
)

__all__ = [
    "TEMPLATE_REGISTRY_SCHEMA_VERSION",
    "CharacterTemplateRecord",
    "get_character_template",
    "list_character_templates",
]
