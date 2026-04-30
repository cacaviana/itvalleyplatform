import click

from .generate_rls import generate_rls


@click.group()
@click.version_option()
def cli() -> None:
    """itvalleyplatform — utilitários de setup multi-tenant."""


cli.add_command(generate_rls, name="generate-rls")


__all__ = ["cli"]
