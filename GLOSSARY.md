# Dungeon DSL

A YAML language for describing dungeons as validated graphs of rooms and doors, rendered as maps for a DM.

## Language

**Dungeon**:
A named graph of Rooms joined by Doors, described in one YAML document.
_Avoid_: Map (reserved for the rendered image), level

**Room**:
An atomic space in a Dungeon; a node of the graph.
_Avoid_: Area, chamber, node

**Door**:
A directed edge between two Rooms, leaving its source Room in a compass direction.
_Avoid_: Exit (the YAML field name, not the concept), passage, edge

**Dungeon Map**:
The rendered SVG drawing of a Dungeon's Rooms and Doors.
_Avoid_: Layout (the placement step that precedes it)

**Playground**:
The public web page where a Dungeon's YAML is edited and its Dungeon Map re-renders live.
_Avoid_: Site, app, editor

**Permalink**:
A URL that carries a Dungeon's YAML itself, so opening it reproduces that Dungeon in the Playground.
_Avoid_: Share link, saved dungeon

**One-way Door**:
A Door from one Room to another with no Door leading back.
_Avoid_: Asymmetric door, unidirectional edge

## Rules

**Problem**:
A place where a Dungeon breaks or strains one of the language's rules.
_Avoid_: Issue, diagnostic, lint, validation error

**Error**:
A Problem that makes a Dungeon invalid, so it can't be drawn.
_Avoid_: Failure, fatal

**Warning**:
A Problem that leaves the Dungeon valid but is probably a mistake.
_Avoid_: Advisory, hint, lint
