"""Alertas via Telegram Bot API. Nunca derruba o pipeline; no-op se sem credenciais."""
import requests

from . import config
from .logging_setup import get_logger

log = get_logger()

_API = "https://api.telegram.org/bot{token}/sendMessage"


def _ativo() -> bool:
    return bool(config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID)


def send(texto: str) -> bool:
    """Envia uma mensagem. Retorna True se enviou, False caso contrário (sem levantar erro)."""
    if not _ativo():
        log.info("Telegram desativado (token/chat vazios) — alerta ignorado.")
        return False
    try:
        resp = requests.post(
            _API.format(token=config.TELEGRAM_TOKEN),
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": texto,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:                       # nunca propaga: alerta não pode abortar a rodada
        log.warning("Falha ao enviar alerta Telegram: %s", e)
        return False


def sucesso(nome_arquivo: str, D: dict, n_destinatarios: int) -> None:
    send(
        "✅ <b>Book Operações de TI</b>\n"
        f"Arquivo: {nome_arquivo}\n"
        f"Linhas: {D['total']}\n"
        f"Incidentes: {D['inc_total']} | Solicitações: {D['sol_total']} | "
        f"SLA viol.: {D['sla_total']}\n"
        f"E-mail enviado a {n_destinatarios} destinatário(s)."
    )


def erro(etapa: str, nome_arquivo, exc: Exception, log_path: str) -> None:
    send(
        "❌ <b>Book Operações de TI — FALHA</b>\n"
        f"Etapa: {etapa}\n"
        f"Arquivo: {nome_arquivo or '—'}\n"
        f"Erro: {type(exc).__name__}: {str(exc)[:300]}\n"
        f"Log: {log_path}"
    )
