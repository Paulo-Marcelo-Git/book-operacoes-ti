"""Logging double-sink: console (INFO) + arquivo diário (DEBUG)."""
import logging
import sys
from datetime import date

from . import config

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def current_log_path() -> str:
    """Caminho do arquivo de log do dia."""
    return str(config.LOG_DIR / f"book_{date.today().isoformat()}.log")


def get_logger(name: str = "book_ti") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:          # evita handlers duplicados em re-importação
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(_FMT)

    import os
    console_level = logging.DEBUG if os.getenv("LOG_LEVEL", "").upper() == "DEBUG" else logging.INFO
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(fmt)

    arquivo = logging.FileHandler(current_log_path(), encoding="utf-8")
    arquivo.setLevel(logging.DEBUG)
    arquivo.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(arquivo)
    return logger
