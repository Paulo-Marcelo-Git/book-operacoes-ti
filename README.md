# Book Operações de TI

Pipeline diário que baixa a planilha de chamados do Google Drive, gera um **book
HTML interativo** (dashboard) e o envia por **e-mail**, com **alertas no Telegram**
a cada execução (sucesso/erro).

Visão de arquitetura completa: ver [`CLAUDE.md`](CLAUDE.md).

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # e preencha os valores
```

No `.env`, preencha em especial:
- `EMAIL_PASS` — App Password de 16 dígitos do Gmail (não a senha da conta).
- `TELEGRAM_TOKEN` — token do @BotFather.
- `GDRIVE_SA_JSON` — coloque o `service_account.json` em `config/`.

A **pasta do Drive precisa estar compartilhada** com o e-mail da service account
(acesso de leitor).

---

## Como rodar

```bash
# rodada completa agora (Drive -> book -> e-mail -> alerta Telegram)
python run.py

# gerar o book local sem enviar nada (ótimo para testar)
python run.py --no-email --no-telegram

# usar um xlsx local em vez do Drive
python run.py --arquivo caminho/da/planilha.xlsx

# só validar o transform (KPIs no terminal)
python -m src.book_ti.transform --arquivo tests/fixtures/sample.xlsx --dry-run

# testar só o alerta do Telegram
python -c "from src.book_ti import notifier; notifier.send('teste ✅')"

# rodar os testes
pytest -q
```

### Agendamento diário (09:00)
- **Residente:** `python -m src.book_ti.scheduler`
- **Cron (WSL/Linux):**
  ```
  0 9 * * * cd /caminho/book-operacoes-ti && /caminho/.venv/bin/python run.py >> logs/cron.log 2>&1
  ```

---

## 🔒 Segurança — antes do primeiro `git push`

Os segredos **nunca** vão para o repositório. Tudo fica no `.env` (ignorado pelo git).

Checklist:
1. Confirme que o `.env`, o `service_account.json` e os `.xlsx` **não** aparecem:
   ```bash
   git status            # nada de .env / *.xlsx / service_account.json
   git check-ignore .env config/service_account.json   # deve listar os dois
   ```
2. O `TELEGRAM_TOKEN` foi exposto durante o desenvolvimento — **revogue no @BotFather**
   (`/revoke`) e gere um novo, usando-o apenas no `.env` local.
3. O book gerado (`output/`) contém nomes reais e também é ignorado pelo git.

Só o `.env.example` (placeholders) vai para o repositório.
