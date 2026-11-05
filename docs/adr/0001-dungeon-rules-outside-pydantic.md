# Dungeon-level rules run outside pydantic

Pydantic models check only the structure of a Dungeon (types, required fields, allowed values, no unknown keys). Rules that span the whole Dungeon (unique room ids, door targets exist, an entrance exists, every Room is reachable, One-way Door warnings) live in a plain `check(dungeon) -> list[Problem]` function, reached only through `dungeon_dsl.load(text) -> Result`. We did this because `model_validator`s can't emit Warnings, stop at the first failing validator, and can only point errors at precise YAML locations by raising `ValidationError.from_exception_data` from inside a validator, which pydantic-core supports but doesn't document.

## Consequences

- `Dungeon.model_validate()` alone no longer means "valid Dungeon". Every caller (CLI, Playground, a future LLM/MCP loop) must go through `load()`.
- Reporting is two-phase: dungeon-level Problems appear only once structural Errors are fixed.
