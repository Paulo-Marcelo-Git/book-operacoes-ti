"""Localiza a planilha mais recente na pasta local inbox/ e a move após processamento."""
import shutil
from pathlib import Path

from . import config
from .logging_setup import get_logger

log = get_logger()


def baixar() -> Path:
    """Retorna o .xlsx mais recente de INBOX_DIR. Levanta FileNotFoundError se vazio."""
    arquivos = sorted(
        config.INBOX_DIR.glob("*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum .xlsx encontrado em '{config.INBOX_DIR}'. "
            "Deposite a planilha na pasta inbox/ antes de executar."
        )
    alvo = arquivos[0]
    log.info("Planilha selecionada: %s", alvo.name)
    return alvo


def mover_processado(path: Path) -> Path:
    """Move o arquivo para inbox/processados/ após processamento bem-sucedido.

    Se já existir arquivo com mesmo nome, adiciona sufixo de timestamp para evitar sobrescrita.
    """
    from datetime import datetime
    destino_dir = config.INBOX_DIR / "processados"
    destino_dir.mkdir(exist_ok=True)
    destino = destino_dir / path.name
    if destino.exists():
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        stem = path.stem
        suffix = path.suffix
        destino = destino_dir / f"{stem}_{ts}{suffix}"
        log.warning("Arquivo já existe no destino; renomeado para: %s", destino.name)
    shutil.move(str(path), destino)
    log.info("Planilha movida para: %s", destino)
    return destino
