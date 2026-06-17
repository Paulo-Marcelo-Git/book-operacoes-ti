# Design: Substituição do Google Drive por pasta local `inbox/`

**Data:** 2026-06-17
**Status:** Aprovado

---

## Contexto

O projeto atualmente baixa a planilha `.xlsx` do Google Drive via Service Account (`drive_client.py`).
A nova abordagem elimina essa dependência: o usuário deposita o arquivo manualmente na pasta `inbox/`
às 08:00, e o pipeline executa às 09:00 lendo dali.

---

## O que muda

### 1. Nova pasta `inbox/`

```
inbox/
├── .gitkeep
└── processados/
    └── .gitkeep
```

- `inbox/*.xlsx` e `inbox/processados/*.xlsx` entram no `.gitignore`.
- As pastas ficam no repositório via `.gitkeep`.

### 2. `src/book_ti/local_client.py` (novo — substitui `drive_client.py`)

Duas funções públicas:

**`baixar() -> Path`**
- Busca `*.xlsx` em `INBOX_DIR` (padrão: `inbox/`).
- Se nenhum arquivo encontrado: lança `FileNotFoundError` com mensagem clara.
- Se um ou mais arquivos: retorna o `Path` do mais recente por data de modificação (`mtime`).

**`mover_processado(path: Path) -> Path`**
- Move o arquivo para `INBOX_DIR/processados/`.
- Retorna o novo caminho.
- Chamado pelo `pipeline.py` após envio de e-mail bem-sucedido.

### 3. `src/book_ti/pipeline.py` (atualizado)

- Troca `from . import drive_client` por `from . import local_client`.
- Após `mailer.enviar(html, D)` (sucesso): chama `local_client.mover_processado(xlsx)`.
- A variável `etapa_atual` já cobre "download" — nenhuma lógica de erro muda.

### 4. `src/book_ti/config.py` (atualizado)

- Remove variáveis `GDRIVE_*`.
- Adiciona `INBOX_DIR = Path(os.getenv("INBOX_DIR", "inbox"))`.

### 5. `.env.example` (atualizado)

- Remove bloco `# Google Drive`.
- Adiciona `INBOX_DIR=inbox`.

### 6. `requirements.txt` (limpeza)

Remove:
- `google-api-python-client`
- `google-auth`
- `google-auth-httplib2`
- `google-auth-oauthlib`

### 7. `drive_client.py` (removido)

Arquivo deletado do repositório.

---

## O que NÃO muda

- `transform.py`, `render.py`, `mailer.py`, `notifier.py`, `scheduler.py`, `run.py`
- `tests/test_transform.py` e `tests/fixtures/sample.xlsx`
- Lógica de agendamento (09:00 via APScheduler)
- Interface de `baixar()` para o `pipeline.py` (retorna caminho do arquivo)

---

## Fluxo após a mudança

```
08:00 — usuário deposita *.xlsx em inbox/
09:00 — scheduler dispara pipeline
         local_client.baixar()         → pega o mais recente de inbox/
         transform.build(df)           → agrega dados
         render.gerar(D)               → gera book HTML
         mailer.enviar(html, D)        → envia e-mail
         local_client.mover_processado() → move para inbox/processados/
         notifier.sucesso(...)         → alerta Telegram
```

---

## Critérios de sucesso

- `pytest -q` continua verde (nenhum teste toca o Drive ou o `local_client`).
- `python run.py` com um `.xlsx` em `inbox/` executa o pipeline completo.
- Após execução, o arquivo está em `inbox/processados/` e não mais em `inbox/`.
- Se `inbox/` estiver vazia, o pipeline falha na etapa "download" com mensagem clara e alerta Telegram.
- Nenhuma referência a `google-api`, `google-auth` ou `drive_client` permanece no código.
