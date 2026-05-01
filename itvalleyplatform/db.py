"""
Helpers de conexão SQL.

Em v0.1.0 o middleware só toca o BANCO DO APP (`APP_SQL_CONNECTION`)
para setar SESSION_CONTEXT — é isso que faz a RLS valer no Azure SQL.

O banco platform (`PLATFORM_SQL_CONNECTION`) é tocado apenas pela CLI
`init-platform` e por endpoints de admin/login, não no request path.

Tudo lazy: se a env não estiver setada, o código loga warning e segue.
"""
import logging

from .config import SETTINGS

logger = logging.getLogger("itvalleyplatform.db")

_warned_no_app_conn = False


def _connect(conn_str: str):
    if not conn_str:
        return None
    try:
        import pyodbc
    except ImportError:
        logger.warning(
            "pyodbc não está instalado — instale com `pip install itvalleyplatform[sql]`. "
            "RLS via SESSION_CONTEXT desativada nesta request."
        )
        return None
    return pyodbc.connect(conn_str, autocommit=True)


def get_app_connection():
    """Conexão pro banco do app (Genesis/CRM/etc). Pode retornar None."""
    return _connect(SETTINGS.APP_SQL_CONNECTION)


def get_platform_connection():
    """Conexão pro banco platform (dbplatform). Pode retornar None."""
    return _connect(SETTINGS.PLATFORM_SQL_CONNECTION)


def set_session_context(tenant_id: str, is_master: bool) -> None:
    """
    Seta SESSION_CONTEXT no banco do APP pra RLS funcionar.
    No-op se APP_SQL_CONNECTION não está configurada.
    """
    global _warned_no_app_conn
    conn = get_app_connection()
    if conn is None:
        if not _warned_no_app_conn:
            logger.warning(
                "APP_SQL_CONNECTION não configurada — SESSION_CONTEXT não foi setado. "
                "RLS no banco do app não vai aplicar até essa env existir."
            )
            _warned_no_app_conn = True
        return
    try:
        cursor = conn.cursor()
        cursor.execute(
            "EXEC sp_set_session_context @key=N'tenant_id', @value=?, @read_only=1",
            tenant_id,
        )
        cursor.execute(
            "EXEC sp_set_session_context @key=N'is_master', @value=?, @read_only=1",
            1 if is_master else 0,
        )
    finally:
        conn.close()
