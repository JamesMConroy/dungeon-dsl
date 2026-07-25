# DUNGEON DSL DESIGN DOCUMENT

## OVERVIEW

YAML schema for describing connected dungeon spaces. Validates graph integrity,
enforces room/door consistency. Renders as SVG map + detail cards. LLM fills
descriptions/encounters; human controls connectivity and balance.

Core insight: Dungeons are graphs. LLMs hallucinate room counts and door targets.
A schema that enforces the graph structure lets LLMs add flavor without breaking
topology.

## CORE CONCEPTS

Room
  Atomic space. Must have ID, name, description, size.
  May have encounters, treasure, hazards, doors, terrain.

Door
  Edge between rooms. Source room ID, target room ID, direction, type, state.
  Validates: source/target exist, direction is cardinal or diagonal.

Encounter
  Creature/NPC/trap. Room-scoped. Quantity, type, challenge level.

Feature
  Room decoration. Secret door, trap, environmental hazard. Tied to specific room.

Hazard
  Environmental danger. Acid pool, unstable floor. Room-scoped.

## SCHEMA

Root
  type: dungeon
  name: string
  level: int (floor number, optional)
  dimensions: {width: int, height: int} (optional, for layout hints)
  theme: string (optional, "underdark" | "tomb" | "fortress" etc., flavor only)
  rooms: [Room]
  connections: [Connection] (optional, explicit edge list if rooms don't define doors)

Room
  id: string (required, unique within dungeon)
  name: string (required)
  description: string (required)
  size: "tiny" | "small" | "medium" | "large" | "vast" (default "medium")
  terrain: string (stone_floor, dirt, water, sand, etc.)
  exits: [Door] (optional, doors defined here or in connections)
  encounters: [Encounter] (optional)
  features: [Feature] (optional)
  treasure: [TreasureItem] (optional)
  light: "dark" | "dim" | "bright" (default "dark")

Door
  id: string (optional, for reference)
  target: string (room ID, required)
  direction: "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw" (required)
  type: "wooden" | "stone" | "iron" | "secret" | "archway" (default "wooden")
  state: "open" | "closed" | "locked" | "barred" (default "closed")
  dc: int (optional, lock difficulty)

Connection
  (Alternative to exits-in-rooms; explicit edge definition)
  from: string (room ID)
  to: string (room ID)
  direction_from: cardinal/diagonal
  direction_to: opposite direction
  type: door type
  state: door state

Encounter
  type: "creature" | "npc" | "trap" | "hazard" (required)
  name: string (required)
  quantity: int (default 1)
  cr: float (challenge rating, optional)
  alignment: string (optional)
  notes: string (optional, custom behavior)

Feature
  name: string (required)
  type: "secret_door" | "trap" | "statue" | "altar" | "chest" | "furniture" (required)
  description: string
  is_hidden: bool (default false)
  dc: int (optional, perception DC to notice)

TreasureItem
  name: string
 quantity: int (default 1)
  rarity: "common" | "uncommon" | "rare" | "very_rare" | "legendary"

## VALIDATION RULES

1. Room IDs must be unique
2. All door target room IDs must exist in rooms array
3. Doors must specify valid cardinal/diagonal directions
4. No orphan rooms (all must be reachable from entrance)
   - Exception: explicitly isolated rooms with isolation: true flag
5. Door connectivity must be bidirectional or explicitly asymmetric
   - If room A has door to B, B should have door back to A
   - Or declared in connections with bidirectional: false
6. Challenge rating (CR) optional but if present, should be within reasonable range (0-30)
7. No duplicate encounter names within room
8. Secret doors must have is_hidden: true
9. Trap DCs should be 8-20 (advisory, not enforced)
10. Dungeon must have at least one room tagged entrance: true

## RENDERING CONTRACT

Three outputs:

1. Mermaid flowchart
    - Rooms as nodes
    - Doors as edges with labels (direction, type, state)
    - Color nodes by size/light level
    - Dashed lines for secret doors

2. SVG Map
   - Rooms as boxes positioned by size/logical layout
   - Doors as lines between rooms with direction labels (n/s/e/w)
   - Color coding by size (tiny=small, large=big) and light level
   - Secret doors shown as dashed lines (or hidden toggle)
   - Encounters shown as icons/badges inside room boxes
   - Hover reveals room name and quick stats

3. Room Detail Cards
   - HTML/text view of room description, encounters, treasures, features
   - Formatted for reading aloud (DM perspective)
   - Links to connected rooms
   - Encounter stat blocks (name, quantity, CR, notes)

4. Interactive HTML view (planned)
   - Embed the SVG inline in the HTML DOM — never via `<img>`, which strips
     all hover/click interactivity
   - render_room stamps class="room" and data-room-id={room.id} on each
     room's `<g>`
   - Hover: pure CSS (.room:hover rect { fill: ... }); pointer-events: none
     on the hatch group and the number label so the room rect is the sole
     hit-target (no flicker crossing tick marks)
   - Click: one delegated listener on the `<svg>`; e.target.closest('.room')
     → look up data-room-id → show detail panel
   - Room details shipped as a `<script type="application/json">` blob keyed
     by room id (not hidden pre-rendered divs)
   - Legend entries also carry data-room-id → symmetric hover highlight
     (hover legend line ↔ highlight room)
   - Standalone out.svg carries its own `<style>` element, so hover highlight
     works opening the raw file in a browser; the click/detail panel is
     HTML-page-only

## EXAMPLE YAML

``` yaml
type: dungeon
name: "Goblin Warren"
level: 1
theme: "goblin_lair"
rooms:
  - id: entrance
    name: "Grand Hall"
    description: "A cavernous chamber with a vaulted ceiling. Bones litter the floor. The smell of smoke and poorly cooked meat hangs in the air."
    size: large
    terrain: stone_floor
    light: dim
    entrance: true
    exits:
      - target: corridor_north
        direction: n
        type: archway
        state: open
      - target: treasure_room
        direction: e
        type: wooden
        state: closed
        dc: 10
    encounters:
      - type: creature
        name: Goblin Shaman
        quantity: 1
        cr: 1
      - type: creature
        name: Goblin
        quantity: 4
        cr: 0.125
    features:
      - name: Ceremonial Fire
        type: altar
        description: "Flickering flames in a stone brazier. Still warm."
    treasure:
      - name: Gold Coins
        quantity: 50
        rarity: common

  - id: corridor_north
    name: "North Passage"
    description: "A narrow tunnel. Torches in wall sconces flicker. Fresh air suggests openness ahead."
    size: small
    terrain: stone_floor
    light: dim
    exits:
      - target: entrance
        direction: s
        type: archway
        state: open
      - target: throne_room
        direction: n
        type: wooden
        state: locked
        dc: 12
    features:
      - name: Pit Trap
        type: trap
        description: "Covered pit, 20ft deep. DC 15 Perception to notice the weak boards."
        is_hidden: true
        dc: 15

  - id: throne_room
    name: "Goblin Throne"
    description: "A grand chamber with a crude throne of piled bones and tattered cloth. Goblin nobility feast at a long table."
    size: large
    terrain: stone_floor
    light: bright
    exits:
      - target: corridor_north
        direction: s
        type: wooden
        state: locked
        dc: 12
      - target: escape_tunnel
        direction: n
        type: secret
        state: hidden
        is_hidden: true
    encounters:
      - type: creature
        name: Goblin Chief
        quantity: 1
        cr: 2
      - type: creature
        name: Goblin Elite Guard
        quantity: 5
        cr: 0.25
    treasure:
      - name: Gem-Encrusted Crown
        quantity: 1
        rarity: rare
      - name: Gold Coins
        quantity: 200
        rarity: common

  - id: treasure_room
    name: "Storage Chamber"
    description: "Barrels and crates stacked haphazardly. The smell of rotting food and ale is overwhelming."
    size: medium
    terrain: dirt
    light: dark
    exits:
      - target: entrance
        direction: w
        type: wooden
        state: closed
        dc: 8
    encounters:
      - type: creature
        name: Giant Rat
        quantity: 3
        cr: 0.125
    treasure:
      - name: Trade Goods
        quantity: 10
        rarity: common

  - id: escape_tunnel
    name: "Hidden Escape Route"
    description: "A narrow natural cavern. Water drips from the ceiling. A faint breeze suggests the exit is near."
    size: small
    terrain: water
    light: dark
    exits:
      - target: throne_room
        direction: s
        type: secret
        state: hidden
        is_hidden: true
    features:
      - name: Collapse Risk
        type: hazard
        description: "Unstable ceiling. Loud noises attract attention; DC 15 Stealth to pass quietly."
```

## CONNECTIVITY CHECK

Entrance → Corridor North → Throne Room
Entrance → Treasure Room
Throne Room → Escape Tunnel

All rooms connected. Graph is acyclic. Valid.

## ROOM SIZES (implementation notes)

Phase 1 — sub-cell sizes (in progress)
  - SIZE_DIMS lookup: size string -> (w, h) px within one cell.
    Must cover every schema value incl. "vast" (Room.size is an
    unvalidated string; a missing key is a render-time KeyError).
    large/vast stay placeholders until multi-cell lands.
  - Center rooms in their cells: offset = (CELL - w) / 2 per axis.
    Then every room's midline is CELL/2 on both axes, so corridor
    coordinates stay constant across size pairs. Without centering,
    corridors must aim at the overlap interval of the two facing wall
    spans (source midline alone can miss a smaller target's wall).
  - Door math must resolve ROLES per axis, not min/max coordinates:
    "west room's east wall" needs the west room's dims, and either
    endpoint can be the west room. Applies to straight + diagonal.
  - Diagonal L margins: clamp corner offset to min(24, w/3) so small
    walls keep a sane opening window.

Phase 2 — multi-cell footprints
  - Placement grows w, h in cells; blocked-cells becomes rect checks.
  - Door anchor picks the footprint column/row nearest the target;
    corridors center on the SHARED span of the two facing walls.
  - THE TRAP: _insert_gap assumes 1x1 rooms (nothing can straddle an
    insertion line). A 2x2 room across the line breaks the "freed
    column is clear" invariant. Escalation ladder:
      1. pick an insertion line that cuts no footprint (may need the
         other axis, or two lines)
      2. shift straddlers too; bounded retry loop re-checks the cell
      3. real rect-packing with adjacency constraints (last resort)
    Corridor-path and diagonal corner reservations get the same
    straddle question.

## COMPACT MAPS (implementation notes)

  - Inter-room distance is currently an accident of constants:
    CELL(140) - room(100x80) = 40px horizontal / 60px vertical gaps.
    Invert it: gap becomes the configured value, cell pitch derived
    per axis (cell_w = room_w + gap, cell_h = room_h + gap).
  - Config surface: RenderOptions dataclass (also the future home of
    room dims, DOOR_WIDTH, hatch params) exposed via a YAML `style:`
    block on the dungeon. Compactness is authorial: it belongs in the
    shared artifact, not a CLI flag.
  - The two-layer paint order (hatch under floors) already handles
    gap -> 0: interior rock disappears under adjacent floors and
    hatching survives only on the exterior perimeter. No
    "which walls are exterior" computation needed.
  - Flush-door mode: below a small gap threshold (~4px) a corridor
    degenerates; render a doorway instead (DOOR_WIDTH white punch
    through the shared wall + glyph). Also guards the div-by-zero in
    render_corridor / hatch_edge on zero-length edges.
  - At gap 0 the shared wall is two 2px strokes = 4px chunky wall;
    ship it (classic look) before inventing shared-wall dedup.
  - Small nonzero gaps: straight corridors become stubs (fine, reads
    as a thick doorway); scale diagonal L margins with gap when it
    looks cramped, not before.

## IMPLEMENTATION CHECKLIST

[ ] Pydantic models for all component types
[ ] Validator for room connectivity (graph traversal)
[ ] Validator for door references (target exists)
[ ] Validator for bidirectional door consistency (advisory warning)
[ ] YAML → JSON serialization
[ ] SVG renderer (rooms as rects, doors as lines, layout algorithm)
   [ ] Positional layout (size-based or grid-based)
   [ ] Color coding (size, light, isolation)
   [ ] Door direction labels
   [ ] Encounter badges
   [ ] Hover/tooltip support
   [ ] Secret door toggle (show/hide dashed lines)
[ ] Card view renderer (HTML room detail cards)
[ ] LLM feedback loop (validate, report errors at domain level)

## FUTURE EXTENSIONS

- Factions/politics (goblin vs kobold territory)
- NPC relationship graph
- Loot tables (random treasure generation)
- Difficulty curve tracking (CR per room → XP calc)
- Multi-level dungeons (level linking)
- Procedural generation mode (fill in missing encounters)
