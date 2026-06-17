"""Orquestra a rodada: download -> transform -> render -> e-mail -> alerta.

Rastreia a etapa atual para que o alerta de erro diga exatamente onde quebrou.
"""
from pathlib import Path

from . import drive_client, mailer, notifier, render, transform
from .logging_setup import current_log_path, get_logger

log = get_logger()


def run(no_email: bool = False, no_telegram: bool = False, arquivo: str | None = None):
    """Executa uma rodada completa. Levanta exceção em caso de falha (após alertar)."""
    etapa = "início"
    nome_arquivo = None
    log.info("==== início da rodada ====")
    try:
        if arquivo:
            etapa = "leitura (arquivo local)"
            caminho = Path(arquivo)
            nome_arquivo = caminho.name
            log.info("Usando arquivo local: %s", caminho)
        else:
            etapa = "download"
            caminho = drive_client.baixar()
            nome_arquivo = caminho.name

        etapa = "transform"
        D = transform.build_from_file(caminho)
        log.info("transform ok: total=%s inc=%s sol=%s sla=%s res=%s",
                 D["total"], D["inc_total"], D["sol_total"], D["sla_total"], D["res_total"])

        etapa = "render"
        html_path = render.gerar(D)

        n_dest = 0
        if no_email:
            log.info("--no-email: envio de e-mail pulado.")
        else:
            etapa = "email"
            n_dest = mailer.enviar(html_path, D)

        if not no_telegram:
            notifier.sucesso(nome_arquivo, D, n_dest)

        log.info("==== rodada concluída ====")
        return html_path

    except Exception as exc:
        log.exception("FALHA na etapa: %s", etapa)
        if not no_telegram:
            notifier.erro(etapa, nome_arquivo, exc, current_log_path())
        raise
