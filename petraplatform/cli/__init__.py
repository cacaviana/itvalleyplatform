import click

from .generate_rls import generate_rls
from .init_platform import init_platform


@click.group()
@click.version_option()
def cli() -> None:
    """petraplatform — utilitários de setup multi-tenant."""


cli.add_command(init_platform, name="init-platform")
cli.add_command(generate_rls, name="generate-rls")


__all__ = ["cli"]
