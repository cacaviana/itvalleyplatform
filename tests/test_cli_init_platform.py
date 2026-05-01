from click.testing import CliRunner

from itvalleyplatform.cli import cli
from itvalleyplatform.cli.init_platform import DEFAULT_PRODUCTS


def test_init_platform_basic():
    runner = CliRunner()
    result = runner.invoke(cli, ["init-platform"])
    assert result.exit_code == 0, result.output
    out = result.output

    # Schema + todas as tabelas esperadas
    assert "CREATE SCHEMA platform" in out
    for table in [
        "platform.tenants",
        "platform.users",
        "platform.tenant_users",
        "platform.products",
        "platform.tenant_products",
        "platform.permissions",
        "platform.role_permissions",
        "platform.audit_logs",
    ]:
        assert table in out, f"missing table {table}"

    # Idempotência: tudo embrulhado em IF NOT EXISTS
    assert "IF NOT EXISTS" in out

    # Seeds
    assert "it-valley" in out
    for p in DEFAULT_PRODUCTS:
        assert p["slug"] in out

    # Constraints/segurança
    assert "password_hash NVARCHAR(500)  NOT NULL" in out
    assert "UQ_platform_users_email UNIQUE (email)" in out
    assert "UQ_platform_tenants_slug UNIQUE (slug)" in out

    # FK explícita
    assert "FK_platform_tenant_users_tenant FOREIGN KEY" in out
    assert "FK_platform_tenant_products_product FOREIGN KEY" in out


def test_init_platform_writes_to_file(tmp_path):
    runner = CliRunner()
    out_file = tmp_path / "platform_init.sql"
    result = runner.invoke(cli, ["init-platform", "--output", str(out_file)])
    assert result.exit_code == 0, result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "CREATE SCHEMA platform" in content
    assert "INSERT INTO platform.products" in content
