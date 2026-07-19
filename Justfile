flowchart-ascii:
  uv run main.py examples/goblin_warren.yaml | mermaid-ascii -

flowchart-png:
  uv run main.py examples/goblin_warren.yaml | mise exec -- mmdc -i - -o out.png -b white

