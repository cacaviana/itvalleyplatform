from datetime import datetime, timezone
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader, StrictUndefined

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_rls_sql(schema: str, tables: list[str]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    template = env.get_template("rls.sql.jinja")
    return template.render(
        schema=schema,
        tables=tables,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


@click.command(help="Gera o script SQL de RLS multi-tenant para um schema/tabelas.")
@click.option("--schema", required=True, help="Nome do schema (ex: genesis, petra).")
@click.option(
    "--tables",
    required=True,
    help="Tabelas separadas por vírgula (ex: leads,deals,campaigns).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Arquivo de saída. Se omitido, escreve no stdout.",
)
def generate_rls(schema: str, tables: str, output: Path | None) -> None:
    table_list = [t.strip() for t in tables.split(",") if t.strip()]
    if not table_list:
        raise click.UsageError("Pelo menos uma tabela é obrigatória.")

    sql = render_rls_sql(schema=schema, tables=table_list)

    if output:
        output.write_text(sql, encoding="utf-8")
        click.echo(f"RLS gerado em: {output}", err=True)
    else:
        click.echo(sql)
