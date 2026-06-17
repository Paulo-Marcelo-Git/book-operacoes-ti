# Local Inbox — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o acesso ao Google Drive por leitura da pasta local `inbox/`, mantendo o restante do pipeline intacto.

**Architecture:** Um novo módulo `local_client.py` expõe a mesma interface que `drive_client.py` (`baixar()` retorna `Path`), mais `mover_processado()` chamado pelo `pipeline.py` após sucesso. O `drive_client.py` é deletado e todas as referências ao Google Drive são removidas do código e da configuração.

**Tech Stack:** Python stdlib (`pathlib`, `shutil`), `pytest`, `monkeypatch`

## Global Constraints

- Python 3.11+
- Todos os caminhos de arquivo via `pathlib.Path` (nunca strings nuas)
- Nenhuma referência a `google-api`, `google-auth` ou `drive_client` pode permanecer após o plano concluído
- `pytest -q` deve continuar verde após cada tarefa
- Código e comentários em PT-BR; nomes de variáveis em inglês

---

### Task 1: Estrutura de pastas `inbox/` e atualização do `.gitignore`

**Files:**
- Create: `inbox/.gitkeep`
- Create: `inbox/processados/.gitkeep`
- Modify: `.gitignore`

**Interfaces:**
- Produces: pasta `inbox/` disponível para as tarefas seguintes

- [ ] **Step 1: Criar as pastas e os arquivos `.gitkeep`**

```bash
mkdir -p /mnt/c/SRC/GIT/book-operacoes-ti/inbox/processados
touch /mnt/c/SRC/GIT/book-operacoes-ti/inbox/.gitkeep
touch /mnt/c/SRC/GIT/book-operacoes-ti/inbox/processados/.gitkeep
```

- [ ] **Step 2: Atualizar `.gitignore` — adicionar entradas para `inbox/`**

No `.gitignore`, logo após o bloco `# DADOS REAIS`, adicionar:

```
inbox/*.xlsx
inbox/*.xls
inbox/processados/*.xlsx
inbox/processados/*.xls
!inbox/.gitkeep
!inbox/processados/.gitkeep
```

- [ ] **Step 3: Verificar que `pytest -q` continua verde**

```bash
cd /mnt/c/SRC/GIT/book-operacoes-ti && .venv/bin/pytest -q
```

Expected: todos os testes passam, nenhum erro.

- [ ] **Step 4: Commit**

```bash
git add inbox/.gitkeep inbox/processados/.gitkeep .gitignore
git commit -m "feat: cria pasta inbox/ com subpasta processados/ e atualiza .gitignore"
```

---

### Task 2: Atualizar `config.py` — remover `GDRIVE_*`, adicionar `INBOX_DIR`

**Files:**
- Modify: `src/book_ti/config.py`

**Interfaces:**
- Produces: `config.INBOX_DIR: Path` — caminho absoluto para a pasta `inbox/`

- [ ] **Step 1: Editar `src/book_ti/config.py`**

Remover o bloco `# Google Drive` inteiro:
```python
# ---------------------------------------------------------------- Google Drive
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "")
GDRIVE_FILE_PATTERN = os.getenv("GDRIVE_FILE_PATTERN", "*.xlsx")
GDRIVE_SA_JSON = os.getenv("GDRIVE_SA_JSON", "config/service_account.json")
```

Substituir por:
```python
# ------------------------------------------------------------------ Inbox local
INBOX_DIR = BASE_DIR / os.getenv("INBOX_DIR", "inbox")
INBOX_DIR.mkdir(exist_ok=True)
(INBOX_DIR / "processados").mkdir(exist_ok=True)
```

- [ ] **Step 2: Verificar que `pytest -q` continua verde**

```bash
cd /mnt/c/SRC/GIT/book-operacoes-ti && .venv/bin/pytest -q
```

Expected: todos os testes passam.

- [ ] **Step 3: Commit**

```bash
git add src/book_ti/config.py
git commit -m "refactor(config): remove GDRIVE_*, adiciona INBOX_DIR"
```

---

### Task 3: Criar `local_client.py` com testes

**Files:**
- Create: `src/book_ti/local_client.py`
- Create: `tests/test_local_client.py`

**Interfaces:**
- Consumes: `config.INBOX_DIR: Path`
- Produces:
  - `baixar() -> Path` — retorna o `.xlsx` mais recente de `INBOX_DIR`; levanta `FileNotFoundError` se vazio
  - `mover_processado(path: Path) -> Path` — move `path` para `INBOX_DIR/processados/`; retorna destino

- [ ] **Step 1: Escrever os testes em `tests/test_local_client.py`**

```python
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
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

```bash
cd /mnt/c/SRC/GIT/book-operacoes-ti && .venv/bin/pytest tests/test_local_client.py -v
```

Expected: FAIL com `ModuleNotFoundError` ou `ImportError` — `local_client` ainda não existe.

- [ ] **Step 3: Criar `src/book_ti/local_client.py`**

```python
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
    """Move o arquivo para inbox/processados/ após processamento bem-sucedido."""
    destino_dir = config.INBOX_DIR / "processados"
    destino_dir.mkdir(exist_ok=True)
    destino = destino_dir / path.name
    shutil.move(str(path), destino)
    log.info("Planilha movida para: %s", destino)
    return destino
```

- [ ] **Step 4: Rodar os testes para confirmar que passam**

```bash
cd /mnt/c/SRC/GIT/book-operacoes-ti && .venv/bin/pytest tests/test_local_client.py -v
```

Expected:
```
tests/test_local_client.py::test_baixar_retorna_mais_recente PASSED
tests/test_local_client.py::test_baixar_levanta_se_inbox_vazia PASSED
tests/test_local_client.py::test_mover_processado PASSED
3 passed
```

- [ ] **Step 5: Rodar toda a suite**

```bash
cd /mnt/c/SRC/GIT/book-operacoes-ti && .venv/bin/pytest -q
```

Expected: todos os testes passam.

- [ ] **Step 6: Commit**

```bash
git add src/book_ti/local_client.py tests/test_local_client.py
git commit -m "feat: adiciona local_client — lê inbox/ em vez do Google Drive"
```

---

### Task 4: Atualizar `pipeline.py` e deletar `drive_client.py`

**Files:**
- Modify: `src/book_ti/pipeline.py`
- Delete: `src/book_ti/drive_client.py`

**Interfaces:**
- Consumes:
  - `local_client.baixar() -> Path`
  - `local_client.mover_processado(path: Path) -> Path`

- [ ] **Step 1: Editar `src/book_ti/pipeline.py`**

Substituir a linha de imports:
```python
# antes
from . import drive_client, mailer, notifier, render, transform
```
por:
```python
from . import local_client, mailer, notifier, render, transform
```

No corpo da função `run()`, substituir o bloco `if arquivo / else` e adicionar a chamada de mover após o e-mail. O arquivo completo deve ficar assim:

```python
"""Orquestra a rodada: leitura -> transform -> render -> e-mail -> alerta.

Rastreia a etapa atual para que o alerta de erro diga exatamente onde quebrou.
"""
from pathlib import Path

from . import local_client, mailer, notifier, render, transform
from .logging_setup import current_log_path, get_logger

log = get_logger()


def run(no_email: bool = False, no_telegram: bool = False, arquivo: str | None = None):
    """Executa uma rodada completa. Levanta exceção em caso de falha (após alertar)."""
    etapa = "início"
    nome_arquivo = None
    from_inbox = False
    log.info("==== início da rodada ====")
    try:
        if arquivo:
            etapa = "leitura (arquivo local)"
            caminho = Path(arquivo)
            nome_arquivo = caminho.name
            log.info("Usando arquivo local: %s", caminho)
        else:
            etapa = "download"
            caminho = local_client.baixar()
            nome_arquivo = caminho.name
            from_inbox = True

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

        if from_inbox:
            etapa = "mover arquivo"
            local_client.mover_processado(caminho)

        if not no_telegram:
            notifier.sucesso(nome_arquivo, D, n_dest)

        log.info("==== rodada concluída ====")
        return html_path

    except Exception as exc:
        log.exception("FALHA na etapa: %s", etapa)
        if not no_telegram:
            notifier.erro(etapa, nome_arquivo, exc, current_log_path())
        raise
```

- [ ] **Step 2: Deletar `drive_client.py`**

```bash
rm /mnt/c/SRC/GIT/book-operacoes-ti/src/book_ti/drive_client.py
```

- [ ] **Step 3: Rodar toda a suite**

```bash
cd /mnt/c/SRC/GIT/book-operacoes-ti && .venv/bin/pytest -q
```

Expected: todos os testes passam, sem erros de import.

- [ ] **Step 4: Commit**

```bash
git add src/book_ti/pipeline.py
git rm src/book_ti/drive_client.py
git commit -m "refactor(pipeline): substitui drive_client por local_client, move arquivo após sucesso"
```

---

### Task 5: Limpeza — `requirements.txt`, `.env.example` e `CLAUDE.md`

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `CLAUDE.md`

**Interfaces:**
- Produces: repositório sem nenhuma referência ao Google Drive

- [ ] **Step 1: Atualizar `requirements.txt`**

Remover as linhas do Google e deixar o arquivo assim:

```
pandas>=2.0
openpyxl>=3.1
python-dotenv>=1.0
requests>=2.31
APScheduler>=3.10
pytest>=7.4
# Opcional (Fase 6 — snapshot PNG inline no e-mail):
# playwright>=1.40
```

- [ ] **Step 2: Atualizar `.env.example`**

Substituir o bloco `# ---- Google Drive ----` por:

```
# ---- Inbox local ----
INBOX_DIR=inbox          # pasta onde a planilha é depositada diariamente
```

- [ ] **Step 3: Atualizar `CLAUDE.md` — seção 2.3 e seção 10**

Na **seção 2.3**, substituir o título e o conteúdo:

```markdown
### 2.3. Acesso à planilha: pasta local `inbox/`
O arquivo `.xlsx` é depositado manualmente na pasta `inbox/` às 08:00.
O pipeline executa às 09:00 e lê o arquivo mais recente (`mtime`).
Após processamento bem-sucedido, o arquivo é movido para `inbox/processados/`.
Se `inbox/` estiver vazia, o pipeline falha na etapa "download" com `FileNotFoundError`.
```

Na **seção 10** (`.env.example`), remover as linhas `GDRIVE_*` e adicionar:
```
# Inbox local
INBOX_DIR=inbox
```

- [ ] **Step 4: Confirmar ausência de referências ao Drive**

```bash
grep -r "drive_client\|GDRIVE\|google-api\|google-auth\|service_account\|googleapiclient" \
  /mnt/c/SRC/GIT/book-operacoes-ti/src \
  /mnt/c/SRC/GIT/book-operacoes-ti/tests \
  /mnt/c/SRC/GIT/book-operacoes-ti/requirements.txt \
  /mnt/c/SRC/GIT/book-operacoes-ti/.env.example \
  2>/dev/null
```

Expected: nenhuma saída.

- [ ] **Step 5: Rodar toda a suite uma última vez**

```bash
cd /mnt/c/SRC/GIT/book-operacoes-ti && .venv/bin/pytest -q
```

Expected: todos os testes passam.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example CLAUDE.md
git commit -m "chore: remove dependências e referências ao Google Drive, documenta inbox/"
```
