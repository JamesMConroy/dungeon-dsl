import sys
from enum import Enum

import typer
from typing import Annotated

from dungeon_dsl import Problem, load
from dungeon_dsl.mermaid import render_mermaid
from dungeon_dsl.svg import render_svg

app = typer.Typer()


class Renderers(str, Enum):
    mermaid = ("mermaid",)
    svg = ("svg",)


RENDERERS = {
    "mermaid": render_mermaid,
    "svg": render_svg,
}


def format_problem(filename: str, problem: Problem) -> str:
    line, col = (
        (problem.span.start.line, problem.span.start.col) if problem.span else (1, 1)
    )
    return (
        f"{filename}:{line}:{col}: {problem.severity}: "
        f"{problem.message} [{problem.code}]"
    )


@app.command()
def main(
    dungeon: Annotated[
        typer.FileText, typer.Argument(help="The dungon file to render.")
    ],
    format: Annotated[
        Renderers, typer.Option("--format", "-f", help="The format to output.")
    ] = Renderers.mermaid,
    as_json: Annotated[
        bool, typer.Option("--json", help="Output the load Result as JSON.")
    ] = False,
) -> None:
    result = load(dungeon.read())

    if as_json:
        print(result.model_dump_json(indent=2))
    else:
        # Problems go to stderr so the map on stdout can still be piped.
        for problem in result.problems:
            print(format_problem(dungeon.name, problem), file=sys.stderr)
        if result.dungeon is not None:
            print(RENDERERS[format](result.dungeon))

    if result.dungeon is None:
        sys.exit(1)


if __name__ == "__main__":
    app()
