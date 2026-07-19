import argparse
import sys

import yaml
from pydantic import ValidationError

from dungeon_dsl.mermaid import render_mermaid
from dungeon_dsl.models import Dungeon

RENDERERS = {
    "mermaid": render_mermaid,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a dungeon YAML file")
    parser.add_argument("dungeon", help="path to dungeon YAML file")
    parser.add_argument(
        "-f", "--format",
        choices=sorted(RENDERERS),
        default="mermaid",
        help="output format (default: mermaid)",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    with open(args.dungeon) as f:
        data = yaml.safe_load(f)

    try:
        dungeon = Dungeon.model_validate(data)
    except ValidationError as e:
        print(f"invalid dungeon: {e}", file=sys.stderr)
        sys.exit(1)

    print(RENDERERS[args.format](dungeon))


if __name__ == "__main__":
    main()
