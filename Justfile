list:
  just -l

examples format="svg":
  for e in examples/*.yaml ; do uv run dungeon-dsl $e -f {{format}} > ${e%%\.*}.svg ; done


example-svg:
  uv run dungeon-dsl examples/goblin_warren.yaml -f svg > out.svg

flowchart-ascii:
  uv run dungeon-dsl examples/goblin_warren.yaml | mermaid-ascii -

flowchart-png:
  uv run dungeon-dsl examples/goblin_warren.yaml | mise exec -- mmdc -i - -o out.png -b white

