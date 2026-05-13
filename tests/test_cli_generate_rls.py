from click.testing import CliRunner

from petraplatform.cli import cli


def test_generate_rls_basic():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["generate-rls", "--schema", "genesis", "--tables", "leads,deals"],
    )
    assert result.exit_code == 0, result.output
    out = result.output
    assert "CREATE OR ALTER FUNCTION rls.fn_tenant_filter" in out
    assert "ALTER TABLE genesis.leads ADD tenant_id" in out
    assert "ALTER TABLE genesis.deals ADD tenant_id" in out
    assert "CREATE INDEX IX_leads_tenant ON genesis.leads(tenant_id)" in out
    assert "CREATE SECURITY POLICY rls.genesis_leads_policy" in out
    assert "CREATE SECURITY POLICY rls.genesis_deals_policy" in out
    # Master bypass na função
    assert "SESSION_CONTEXT(N'is_master')" in out


def test_generate_rls_writes_to_file(tmp_path):
    runner = CliRunner()
    out_file = tmp_path / "rls_petra.sql"
    result = runner.invoke(
        cli,
        [
            "generate-rls",
            "--schema",
            "petra",
            "--tables",
            "patients,meal_plans",
            "--output",
            str(out_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_file.exists()
    content = out_file.read_text()
    assert "petra.patients" in content
    assert "petra.meal_plans" in content


def test_generate_rls_strips_whitespace_in_tables():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["generate-rls", "--schema", "x", "--tables", " a , b , c "],
    )
    assert result.exit_code == 0
    assert "x.a" in result.output and "x.b" in result.output and "x.c" in result.output


def test_generate_rls_empty_tables_fails():
    runner = CliRunner()
    result = runner.invoke(cli, ["generate-rls", "--schema", "x", "--tables", " , "])
    assert result.exit_code != 0
