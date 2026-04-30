"""
Helper de conexão SQL — usado só pra setar SESSION_CONTEXT (RLS).
A conexão é lazy: só inicializa se PLATFORM_SQL_CONNECTION estiver setada.
"""
import logging
from typing import Optional

from .config import SETTINGS

logger = logging.getLogger("itvalleyplatform.db")

_warned_no_conn = False


def _get_connection():
    if not SETTINGS.PLATFORM_SQL_CONNECTION:
        return None
    try:
        import pyodbc  # lazy import — só obriga pyodbc se for usar SQL
    except ImportError:
        logger.warning(
            "pyodbc não está instalado — instale com `pip install itvalleyplatform[sql]`. "
            "RLS via SESSION_CONTEXT desativada nesta request."
        )
        return None
    return pyodbc.connect(SETTINGS.PLATFORM_SQL_CONNECTION, autocommit=True)


def set_session_context(tenant_id: str, is_master: bool) -> None:
    """
    Seta SESSION_CONTEXT no SQL pra RLS funcionar. No-op se SQL não está configurado
    (dev local ou testes sem DB).
    """
    global _warned_no_conn
    conn = _get_connection()
    if conn is None:
        if not _warned_no_conn:
            logger.warning(
                "PLATFORM_SQL_CONNECTION não configurada — SESSION_CONTEXT não foi setado. "
                "RLS no banco não vai funcionar até essa env existir."
            )
            _warned_no_conn = True
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
