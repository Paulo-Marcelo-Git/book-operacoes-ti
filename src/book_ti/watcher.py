"""Modo watcher: monitora inbox/ em loop e processa cada .xlsx que aparecer.

Uso:
    python run.py --watch
    python run.py --watch --intervalo 30 --no-email --no-telegram
"""
import time

from . import config, pipeline
from .logging_setup import get_logger

log = get_logger()

DEFAULT_INTERVALO = 60  # segundos entre cada verificação


def iniciar(intervalo: int = DEFAULT_INTERVALO, no_email: bool = False, no_telegram: bool = False):
    """Loop infinito: verifica inbox/ a cada `intervalo` segundos e processa novos .xlsx."""
    log.info("Watcher iniciado — monitorando '%s' a cada %ds. Ctrl+C para parar.", config.INBOX_DIR, intervalo)
    while True:
        arquivos = sorted(
            config.INBOX_DIR.glob("*.xlsx"),
            key=lambda p: p.stat().st_mtime,
        )
        if arquivos:
            for xlsx in arquivos:
                log.info("Novo arquivo detectado: %s", xlsx.name)
                try:
                    pipeline.run(no_email=no_email, no_telegram=no_telegram, arquivo=str(xlsx))
                except Exception:
                    # erro já foi logado e alertado dentro do pipeline; continua o loop
                    log.warning("Rodada falhou para '%s'; watcher continua aguardando.", xlsx.name)
        else:
            log.debug("inbox/ vazia, aguardando %ds...", intervalo)

        time.sleep(intervalo)
