# Book Operações de TI

Pipeline diário que lê uma planilha de chamados da pasta `inbox/`, gera um **book
HTML interativo** (dashboard) e o envia por **e-mail**, com **alertas no Telegram**
a cada execução (sucesso/erro).

Arquitetura completa: ver [`CLAUDE.md`](CLAUDE.md).

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # preencha os valores
```

No `.env`, configure em especial:
- `EMAIL_PASS` — App Password de 16 dígitos do Gmail (não a senha da conta).
- `TELEGRAM_TOKEN` — token do @BotFather (opcional; deixe em branco para desativar alertas).

---

## Fluxo de dados

```
08:00 — depositar *.xlsx em inbox/
09:00 — scheduler dispara pipeline
         inbox/ → transform → book HTML → e-mail → inbox/processados/
                                                  → alerta Telegram
```

---

## Como rodar

```bash
# rodada completa agora
python run.py

# gerar o book local sem enviar nada (ótimo para testar)
python run.py --no-email --no-telegram

# usar um xlsx específico em vez do mais recente em inbox/
python run.py --arquivo caminho/da/planilha.xlsx

# validar só o transform (KPIs no terminal)
python -m src.book_ti.transform --arquivo tests/fixtures/sample.xlsx --dry-run

# testar só o alerta Telegram
python -c "from src.book_ti import notifier; notifier.send('teste ✅')"

# rodar os testes
pytest -q
```

### Agendamento diário (09:00)

```bash
# modo residente (APScheduler)
python -m src.book_ti.scheduler

# modo watcher (processa qualquer .xlsx que aparecer em inbox/)
python run.py --watch
```

**Cron WSL/Linux:**
```
0 9 * * * cd /caminho/book-operacoes-ti && /caminho/.venv/bin/python run.py >> logs/cron.log 2>&1
```

---

## Personalização

- **Keywords monitoradas**: edite `KEYWORDS` em `src/book_ti/transform.py`.
- **Colunas da planilha**: edite `COLUNAS` em `src/book_ti/config.py` (mapeamento letra → campo).
- **Horário de execução**: `SCHEDULE_HOUR` / `SCHEDULE_MINUTE` no `.env`.

---

## Segurança

Os segredos ficam **apenas no `.env`** (ignorado pelo git). Nunca commitar `.env`.

```bash
# confirme que o .env não aparece no git
git check-ignore .env     # deve listar o arquivo
git status                # .env não deve aparecer
```
