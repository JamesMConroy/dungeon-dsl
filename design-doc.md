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

1. SVG Map
   - Rooms as boxes positioned by size/logical layout
   - Doors as lines between rooms with direction labels (n/s/e/w)
   - Color coding by size (tiny=small, large=big) and light level
   - Secret doors shown as dashed lines (or hidden toggle)
   - Encounters shown as icons/badges inside room boxes
   - Hover reveals room name and quick stats

2. Room Detail Cards
   - HTML/text view of room description, encounters, treasures, features
   - Formatted for reading aloud (DM perspective)
   - Links to connected rooms
   - Encounter stat blocks (name, quantity, CR, notes)

# EXAMPLE YAML

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
