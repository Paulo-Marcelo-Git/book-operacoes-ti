"""Gera o book HTML final injetando o dicionário D no template."""
import json
from datetime import datetime

from . import config
from .logging_setup import get_logger

log = get_logger()

MARCADOR_DADOS = "/*__DATA__*/{}"
MARCADOR_DATA = "__GERADO_EM__"


def gerar(D: dict, template_path=None, output_dir=None):
    template_path = template_path or config.TEMPLATE_PATH
    output_dir = output_dir or config.OUTPUT_DIR

    html = template_path.read_text(encoding="utf-8")
    if MARCADOR_DADOS not in html:
        raise ValueError(f"Marcador {MARCADOR_DADOS!r} não encontrado no template.")

    html = html.replace(MARCADOR_DADOS, json.dumps(D, ensure_ascii=False))
    html = html.replace(MARCADOR_DATA, datetime.now().strftime("%d/%m/%Y %H:%M"))

    destino = output_dir / f"book_{datetime.now():%Y-%m-%d}.html"
    destino.write_text(html, encoding="utf-8")
    log.info("Book gerado: %s", destino)
    return destino
