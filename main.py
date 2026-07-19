import sys

import yaml
from pydantic import ValidationError

from dungeon_dsl.mermaid import render_mermaid
from dungeon_dsl.models import Dungeon


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: main.py <dungeon.yaml>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path) as f:
        data = yaml.safe_load(f)

    try:
        dungeon = Dungeon.model_validate(data)
    except ValidationError as e:
        print(f"invalid dungeon: {e}", file=sys.stderr)
        sys.exit(1)

    print(render_mermaid(dungeon))


if __name__ == "__main__":
    main()
