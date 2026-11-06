import sys

import yaml
from enum import Enum

import typer
from typing import Annotated
from pydantic import ValidationError

from dungeon_dsl.mermaid import render_mermaid
from dungeon_dsl.models import Dungeon
from dungeon_dsl.svg import render_svg

app = typer.Typer()


class Renderers(str, Enum):
    mermaid = ("mermaid",)
    svg = ("svg",)


RENDERERS = {
    "mermaid": render_mermaid,
    "svg": render_svg,
}


@app.command()
def main(
    dungeon: Annotated[
        typer.FileText, typer.Argument(help="The dungon file to render.")
    ],
    format: Annotated[
        Renderers, typer.Option("--format", "-f", help="The format to output.")
    ] = Renderers.mermaid,
) -> None:

    data = yaml.safe_load(dungeon)

    try:
        dungeon_model = Dungeon.model_validate(data)
    except ValidationError as e:
        print(f"invalid dungeon: {e}", file=sys.stderr)
        sys.exit(1)

    print(RENDERERS[format](dungeon_model))


if __name__ == "__main__":
    app()
