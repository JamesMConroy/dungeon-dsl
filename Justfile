example-ascii:
  uv run main.py examples/goblin_warren.yaml | mermaid-ascii -

example-png:
  uv run main.py example/examples/goblin_warren.yaml | mise exec -- mmdc -i - -o out.png -b white

