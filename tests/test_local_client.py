import os
import time
from pathlib import Path

import pytest

import src.book_ti.config as cfg
from src.book_ti import local_client


def test_baixar_retorna_mais_recente(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    monkeypatch.setattr(cfg, "INBOX_DIR", inbox)

    antigo = inbox / "antigo.xlsx"
    recente = inbox / "recente.xlsx"
    antigo.write_bytes(b"")
    recente.write_bytes(b"")
    os.utime(antigo, (0, 0))
    os.utime(recente, (time.time(), time.time()))

    resultado = local_client.baixar()
    assert resultado == recente


def test_baixar_levanta_se_inbox_vazia(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    monkeypatch.setattr(cfg, "INBOX_DIR", inbox)

    with pytest.raises(FileNotFoundError, match="Nenhum .xlsx"):
        local_client.baixar()


def test_mover_processado(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    monkeypatch.setattr(cfg, "INBOX_DIR", inbox)

    arquivo = inbox / "planilha.xlsx"
    arquivo.write_bytes(b"")

    destino = local_client.mover_processado(arquivo)

    assert destino == inbox / "processados" / "planilha.xlsx"
    assert destino.exists()
    assert not arquivo.exists()
