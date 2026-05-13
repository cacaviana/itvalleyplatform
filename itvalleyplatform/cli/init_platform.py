from datetime import datetime, timezone
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader, StrictUndefined

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

DEFAULT_PRODUCTS = [
    {"slug": "genesis",  "name": "Genesis",  "description": "CRM com IA conversacional em WhatsApp/SMS, multilingue"},
    {"slug": "quanto",   "name": "Quanto",   "description": "Quoting conversacional — cliente descreve, recebe quote assinavel"},
    {"slug": "vitrine",  "name": "Vitrine",  "description": "Geracao de carrosseis e posts para LinkedIn/IG/FB"},
    {"slug": "polaris",  "name": "Polaris",  "description": "Scripts de Reels/Shorts + analise de competidor + trending topics"},
    {"slug": "calenda",  "name": "Calenda",  "description": "Qualificacao visual + agendamento conversacional via WhatsApp"},
]


def render_platform_init_sql(products: list[dict] | None = None) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    template = env.get_template("platform_init.sql.jinja")
    return template.render(
        products=products or DEFAULT_PRODUCTS,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


@click.command(help="Gera o DDL completo do schema platform.* (banco dbplatform).")
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Arquivo de saída. Se omitido, escreve no stdout.",
)
def init_platform(output: Path | None) -> None:
    sql = render_platform_init_sql()
    if output:
        output.write_text(sql, encoding="utf-8")
        click.echo(f"DDL platform.* gerada em: {output}", err=True)
        click.echo(
            "Próximo passo:\n"
            "  sqlcmd -S srvmasterclass.database.windows.net -d dbplatform "
            "-U adminitvalley -P <senha> -i " + str(output),
            err=True,
        )
    else:
        click.echo(sql)
