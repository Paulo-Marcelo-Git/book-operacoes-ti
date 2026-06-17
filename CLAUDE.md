# CLAUDE.md — Book Operações de TI (ETL diário → Dashboard → E-mail)

> Documento de contexto e arquitetura para o Claude Code / desenvolvimento.
> Mantenha este arquivo atualizado conforme o projeto evolui.

---

## 1. Objetivo

Aplicação Python que **todos os dias às 09:00**:

1. Lê uma planilha (`.xlsx`) da **pasta local `inbox/`**;
2. Processa os dados com **pandas** e produz as agregações da operação de TI;
3. Injeta esses dados em um **template HTML** (o "Book", já desenhado) gerando um dashboard interativo;
4. **Envia por e-mail** um resumo KPI (corpo) + o Book completo (anexo).

Stack alinhado ao padrão já usado no FlowETL: `pandas`, `APScheduler`, logging *double-sink* (console + arquivo).

---

## 2. Decisões de arquitetura (importante ler antes de codar)

### 2.1. O anexo recebido é o ALVO, não a origem
O arquivo `Book___Operações_de_TI.html` é o **dashboard renderizado** (mock). Ele define:
- O **layout** (6 páginas: Total, Grupo, Analista, Ofensores, Keywords, Solicitantes);
- O **objeto de dados `D`** que o Python precisa produzir (schema na seção 5).

Ele **não** é a planilha de origem. A origem real (`Operações_de_TI_-_GERAL_Áreas_*.xlsx`) já foi
localizada e inspecionada na pasta do Drive — schema, colunas e números-alvo confirmados (seções 5–7).

### 2.2. Gráficos em `<script>` NÃO renderizam dentro de e-mail
O Book monta SVG via JavaScript no `window.onload`. Outlook/Gmail **removem `<script>`**. Portanto:

- **Corpo do e-mail** = HTML *email-safe* (tabelas com CSS inline, sem JS) com os KPIs principais.
- **Anexo** = o Book interativo completo (`.html`), que abre no navegador com todos os gráficos.
- **Fase 2 (opcional)** = snapshot PNG do Book via Playwright (headless) embutido inline (`cid:`) para preview visual no corpo.

### 2.3. Acesso à planilha: pasta local `inbox/`
O arquivo `.xlsx` é depositado manualmente na pasta `inbox/` às 08:00.
O pipeline executa às 09:00 e lê o arquivo mais recente (`mtime`).
Após processamento bem-sucedido, o arquivo é movido para `inbox/processados/`.
Se `inbox/` estiver vazia, o pipeline falha na etapa "download" com `FileNotFoundError`.

### 2.4. Renderização do template: injeção por marcador (não Jinja)
O template tem muito JavaScript com `{` e `}`. Usar Jinja exigiria escapar tudo. Mais simples e robusto:
- No template, trocar `const D = {...};` por `const D = /*__DATA__*/{};`
- No Python: `template.replace("/*__DATA__*/{}", json.dumps(D, ensure_ascii=False))`

### 2.5. Agendamento: dois modos
- **APScheduler** (`BlockingScheduler` + `CronTrigger hour=9 minute=0`) — processo residente, igual ao FlowETL.
- **One-shot + cron do sistema** (WSL: `crontab`; Windows: Agendador de Tarefas) — mais simples e resiliente para um job 1x/dia.

O entrypoint `run.py` executa **uma rodada** (one-shot). O `scheduler.py` só envelopa o `run.py` no horário. Assim qualquer um dos dois modos funciona sem reescrever a lógica.

---

## 3. Stack técnico

| Camada | Biblioteca |
|---|---|
| Leitura planilha | `pandas`, `openpyxl` |
| Render HTML | string injection + `json` (stdlib) |
| E-mail | `smtplib` + `email` (stdlib) — *default*; Gmail API como alternativa |
| Alertas | Telegram Bot API via `requests` (POST `sendMessage`) |
| Agendamento | `APScheduler` (modo residente) |
| Config | `python-dotenv` |
| Log | `logging` (double-sink) |
| Snapshot (fase 2) | `playwright` (opcional) |

Python 3.11+.

---

## 4. Estrutura do projeto

```
book-operacoes-ti/
├── CLAUDE.md                  # este arquivo
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── templates/
│   └── book_template.html     # o mock, com o marcador /*__DATA__*/
├── output/                    # books gerados por data (GITIGNORED)
├── logs/                      # logs diários (GITIGNORED)
├── src/
│   └── book_ti/
│       ├── __init__.py
│       ├── config.py          # carrega .env + mapeamento de colunas
│       ├── logging_setup.py   # double-sink (console + arquivo)
│       ├── local_client.py    # lê o xlsx mais recente de inbox/ e move após processamento
│       ├── transform.py       # pandas DataFrame -> dict D
│       ├── render.py          # injeta D no template -> HTML final
│       ├── mailer.py          # monta corpo email-safe + anexa book + envia
│       ├── notifier.py        # alertas Telegram (sucesso / erro)
│       ├── pipeline.py        # orquestra: download -> transform -> render -> send -> alerta
│       └── scheduler.py       # APScheduler chamando pipeline às 09:00
├── tests/
│   ├── test_transform.py      # valida agregações com fixture
│   └── fixtures/
│       └── sample.xlsx        # amostra real (baixar do Drive 1x para os testes)
└── run.py                     # entrypoint one-shot: roda 1 pipeline e sai
```

`.gitignore` deve conter: `.env`, `output/`, `logs/`, `__pycache__/`, `*.pyc`.

---

## 5. Mapeamento de colunas (planilha → campos) — ✅ CONFIRMADO

Validado contra a planilha real `Operações_de_TI_-_GERAL_Áreas_*.xlsx` (1.595 linhas, 18 colunas,
`header=0`). Header completo (letra / índice pandas / nome real):

| Letra | Índice | Nome real do header | Usado para |
|---|---|---|---|
| A | 0 | `#` | — |
| B | 1 | `Unnamed: 1` (vazia) | — |
| C | 2 | `Hora da solicitação` | — |
| D | 3 | `Hora de encerramento` | — |
| **E** | 4 | `Sla Violado.` | **SLA Violado** (`== 'Sim'`) |
| F | 5 | `Reabrir contador` | — |
| G | 6 | `Data de conclusão` | — |
| **H** | 7 | `Tipo de Registro de Serviço` | **Tipo** (`Incidente` / `Solicitação`) |
| **I** | 8 | `Descrição` | **Keywords** (NF, Estoque, Pedido) |
| **J** | 9 | `Legenda` | **Status** (`== 'Resolvido'`) |
| K | 10 | `Categoria` | — |
| **L** | 11 | `Subcategoria` | **Ofensores** |
| M | 12 | `Categoria de terceiro nível` | — |
| N | 13 | `Título` | — |
| **O** | 14 | `Usuário Solicitante` | **Top 10 solicitantes** |
| **P** | 15 | `Grupo solucionador` | **Divisão por grupo** |
| **Q** | 16 | `Analista responsável` | **Divisão por analista** |
| R | 17 | `Prioridade` | — |

> O mapeamento fica em `config.py` lendo por **letra** (robusto a mudança de ordem). Atenção: a coluna **B é vazia** (`Unnamed: 1`) — por isso o acesso posicional/por letra é mais seguro que por nome.

### Valores distintos confirmados (define a lógica do transform)
- **E `Sla Violado.`**: `Sim` (64) ou vazio/NaN (1.531). → SLA violado quando `== 'Sim'`.
- **H `Tipo de Registro de Serviço`**: `Incidente` (1.248), `Solicitação` (347).
- **J `Legenda`**: `Resolvido` (1.589), `Cancelar` (4), `Mesclagem fechada` (1), `Reopened by End User` (1). → "Resolvidos" = `== 'Resolvido'`.

Todos batem exatamente com os KPIs do mock (Inc 1.248 / Sol 347 / SLA 64 / Resolvido 1.589 / Total 1.595).

---

## 6. Schema do objeto `D` (saída do transform — contrato com o template)

`transform.py` deve produzir **exatamente** esta estrutura (extraída do mock):

```python
D = {
  "total": int,
  "sla_total": int,         # count(E == 'Sim')
  "inc_total": int,         # count(H == 'Incidente')
  "sol_total": int,         # count(H == 'Solicitação')
  "res_total": int,         # count(J == 'Resolvido')

  "grupos": [               # group by Coluna P
    {"grupo": str, "total": int, "sla": int, "inc": int, "sol": int}
  ],

  "analistas": [            # group by Coluna Q, ordenado por total desc
    {"analista": str, "total": int, "sla": int, "inc": int, "sol": int, "grupo": str}
  ],

  "subcat_matrix": [        # group by Coluna L x Coluna P, top 15 por total
    {"sub": str, "total": int, "por_grupo": {"<grupo>": int, ...}}
  ],

  "grupos_list": [str, ...],          # lista distinta de grupos (Coluna P)

  "keywords": [             # busca na Coluna I, quebrado por Coluna P
    {"keyword": "Nota Fiscal / NF", "total": int, "por_grupo": {...}},
    {"keyword": "Estoque",          "total": int, "por_grupo": {...}},
    {"keyword": "Pedido",           "total": int, "por_grupo": {...}}
  ],

  "top_solicitantes": [     # group by Coluna O, top 10 por total
    {"solicitante": str, "total": int, "sla": int, "inc": int, "sol_count": int}
  ]
}
```

---

## 7. Lógica de transformação (`transform.py`)

```
1. Ler xlsx com pandas (header=0). Selecionar colunas por letra via mapa do config.
2. Normalizar: strip de strings; analista vazio -> "none"; grupo vazio -> "Não atribuído".
3. Derivar máscaras booleanas por linha:
       is_inc = (H == 'Incidente')
       is_sol = (H == 'Solicitação')
       is_sla = (E == 'Sim')              # demais valores/NaN = não violado
       is_res = (J == 'Resolvido')
4. total = len(df); inc_total/sol_total/sla_total/res_total = soma das máscaras.
5. grupos          = df.groupby(col_P) -> total + soma de is_inc/is_sol/is_sla por grupo
6. analistas       = df.groupby(col_Q) (+ grupo predominante) -> ordenar total desc
7. subcat_matrix   = df.groupby([col_L, col_P]) -> pivot -> top 15 por total
8. keywords        = para cada bucket, aplicar regex sobre col_I NORMALIZADA
                     (NFKD + remover acentos + lower), e quebrar por col_P:
       - "Nota Fiscal / NF": r"nota\s*fiscal|\bnf\b"   -> 101  (substring)
       - "Estoque":          r"estoque"                -> 35   (substring)
       - "Pedido":           r"\bpedido\b"             -> 167  (PALAVRA EXATA, singular)
     ⚠ "Pedido" usa \b...\b e NÃO casa "pedidos" (plural). Foi assim que o mock foi gerado.
        NF e Estoque casam por substring. Não unifique as três regras.
     (Buckets independentes; um chamado pode contar em mais de uma keyword.)
9. top_solicitantes= df.groupby(col_O) -> top 10 por total (+ is_inc/is_sla/sol_count)
```

Normalização de acentos para keywords: `unicodedata.normalize('NFKD', s)`, remover combining
chars, `str.lower()` antes do regex.

### Números-alvo para o teste (devem bater exatamente)
`test_transform.py` deve afirmar contra a planilha real:
`total=1595, inc_total=1248, sol_total=347, sla_total=64, res_total=1589`,
`keywords: NF=101 (N2:74,N3:18,N1:9), Estoque=35 (N2:23,N3:10,N1:2), Pedido=167 (N2:123,N1:27,N3:17)`.

---

## 8. Render (`render.py`)

```
1. Ler templates/book_template.html (UTF-8).
2. Substituir o marcador /*__DATA__*/{} por json.dumps(D, ensure_ascii=False).
3. Atualizar o carimbo "Gerado em ..." com a data/hora atual (pt-BR).
4. Salvar em output/book_AAAA-MM-DD.html. Retornar o caminho.
```

**Preparar o template uma vez:** copiar o mock para `templates/book_template.html` e trocar
`const D = {...grande objeto...};` por `const D = /*__DATA__*/{};`.

---

## 9. E-mail (`mailer.py`)

```
1. Montar corpo HTML EMAIL-SAFE (tabelas, CSS inline, sem <script>):
   - KPIs: Total, Incidentes, Solicitações, SLA Violado
   - Mini-tabela: total por grupo (Coluna P)
   - Mini-tabela: Top 5 solicitantes
   - Texto: "Book completo e interativo em anexo."
2. Anexar output/book_AAAA-MM-DD.html.
3. (Fase 2) Anexar/embutir PNG via Playwright (cid: inline).
4. Enviar via SMTP Gmail (smtplib + EmailMessage), STARTTLS na porta 587:
   `smtplib.SMTP(EMAIL_SMTP, EMAIL_PORTA)` -> `starttls()` -> `login(EMAIL_USER, EMAIL_PASS)`.
   ⚠ EMAIL_PASS é uma App Password do Gmail (16 dígitos), não a senha da conta.
```

Variáveis (`.env`, convenção `EMAIL_*` — mesma do FlowETL): `EMAIL_USER`, `EMAIL_PASS`,
`EMAIL_DESTINATARIO` (split por vírgula -> lista de destinatários), `EMAIL_SMTP`, `EMAIL_PORTA`,
`EMAIL_ASSUNTO_PREFIXO`. Assunto sugerido: `Book Operações de TI — {data}`.

---

## 9.1. Alertas Telegram (`notifier.py`)

Notifica a cada execução: **sucesso** (arquivo processado) ou **erro**. Independente do e-mail —
serve como monitoramento operacional do job.

```
- Função send(texto): POST https://api.telegram.org/bot{TOKEN}/sendMessage
                      payload = {chat_id, text, parse_mode:'HTML'}, timeout=10s.
- O notifier NUNCA derruba o pipeline: envolver o POST em try/except e só logar se falhar
  (um alerta que falha não pode abortar a rodada nem mascarar o erro original).
- Se TELEGRAM_TOKEN/CHAT_ID estiverem vazios, o notifier vira no-op (apenas loga "telegram desativado").

Mensagens:
  ✅ sucesso -> "✅ <b>Book Operações de TI</b>\nArquivo: {nome_xlsx}\nLinhas: {total}\n
                Incidentes: {inc} | Solicitações: {sol} | SLA viol.: {sla}\nE-mail enviado a {n} destinatário(s)."
  ❌ erro    -> "❌ <b>Book Operações de TI — FALHA</b>\nEtapa: {etapa}\nArquivo: {nome ou '—'}\n
                Erro: {tipo}: {mensagem curta}\nVer log: {caminho_do_log}"
```

Variáveis (`.env`): `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.

> ⚠ Segurança: o token dá controle total do bot. Mantê-lo só no `.env` (gitignored). Se for exposto,
> revogar no @BotFather (`/revoke`) e gerar outro.

---

## 9.2. Orquestração e tratamento de erro (`pipeline.py`)

```
def run():
    log.info("início da rodada")
    try:
        xlsx   = local_client.baixar()          # etapa = "download"
        df     = ler(xlsx)                       # etapa = "leitura"
        D      = transform.build(df)             # etapa = "transform"
        html   = render.gerar(D)                 # etapa = "render"
        n      = mailer.enviar(html, D)          # etapa = "email"
        notifier.sucesso(xlsx, D, n)             # alerta ✅
        log.info("rodada concluída")
    except Exception as e:
        log.exception("falha na etapa %s", etapa_atual)
        notifier.erro(etapa_atual, nome_arquivo, e, caminho_log)   # alerta ❌
        raise        # re-levanta para o run.py sair com código != 0 (útil no cron)
```

Rastrear `etapa_atual` numa variável para o alerta de erro dizer **onde** quebrou.

---

## 10. Configuração (`.env`)

`.env.example`:
```
# Inbox local
INBOX_DIR=inbox

# Email (Gmail — reaproveitando a conta do FlowETL)
EMAIL_USER=seu_bot@gmail.com
EMAIL_PASS=                                   # App Password de 16 dígitos (preencher local; NUNCA commitar)
EMAIL_DESTINATARIO=destino@exemplo.com      # aceita lista separada por vírgula
EMAIL_SMTP=smtp.gmail.com
EMAIL_PORTA=587                               # STARTTLS. Alternativa: 465 (SSL direto)
EMAIL_ASSUNTO_PREFIXO=Book Operações de TI

# Telegram (alertas de sucesso/erro) — preencher local, NÃO commitar
TELEGRAM_TOKEN=                               # token do @BotFather
TELEGRAM_CHAT_ID=                             # id do chat/grupo de destino

# App
SCHEDULE_HOUR=9
SCHEDULE_MINUTE=0
OUTPUT_DIR=output
LOG_DIR=logs
```

Mapa de colunas fica em `config.py` (não no `.env`) — todas confirmadas:
```python
COLUNAS = {
    "sla":          "E",   # 'Sla Violado.'                 -> == 'Sim'
    "tipo":         "H",   # 'Tipo de Registro de Serviço'  -> Incidente/Solicitação
    "descricao":    "I",   # 'Descrição'                    -> keywords
    "status":       "J",   # 'Legenda'                      -> == 'Resolvido'
    "subcategoria": "L",   # 'Subcategoria'                 -> ofensores
    "solicitante":  "O",   # 'Usuário Solicitante'         -> top 10
    "grupo":        "P",   # 'Grupo solucionador'          -> divisão por grupo
    "analista":     "Q",   # 'Analista responsável'        -> divisão por analista
}
```

---

## 11. Pendências / Perguntas a confirmar

✅ **Resolvidas** (via inspeção da planilha real): schema/headers, mapeamento das colunas E/H/J,
nome/padrão do arquivo no Drive, e os números-alvo de validação.

Ainda em aberto:

1. ~~Servidor SMTP~~ ✅ Resolvido: Gmail (`seu_bot@gmail.com`) reaproveitado do FlowETL, com
   App Password já existente. Falta só preencher `EMAIL_PASS` no `.env` local.
2. **Host/fuso do agendamento**: o WSL precisa estar ligado às 09:00. Se a máquina costuma ficar
   desligada, considerar servidor dedicado ou Agendador de Tarefas do Windows.
3. **Janela de dados**: a planilha é sempre um *snapshot* completo (acumulado) ou já vem filtrada por
   período? Isso define se o book é "do dia" ou "acumulado". (Hoje o mock trata como acumulado.)

---

## 12. Roadmap de implementação

- **Fase 0 — Setup**: estrutura de pastas, `requirements.txt`, `.env.example`, `logging_setup.py`, preparar `book_template.html` com o marcador.
- **Fase 1 — Transform offline**: com a amostra `.xlsx`, implementar `transform.py` + `test_transform.py`. Render local e abrir no navegador. (Sem Drive, sem e-mail ainda.)
- **Fase 2 — Inbox**: `local_client.py` lendo de `inbox/` (✅ concluído).
- **Fase 3 — E-mail**: `mailer.py` com corpo email-safe + anexo. Teste enviando para você mesmo.
- **Fase 4 — Orquestração**: `pipeline.py` + `run.py` (one-shot) ponta a ponta.
- **Fase 4.5 — Alertas Telegram**: `notifier.py` + integração no `pipeline.py` (✅ sucesso / ❌ erro).
- **Fase 5 — Agendamento**: `scheduler.py` (APScheduler 09:00) ou cron do sistema.
- **Fase 6 (opcional)**: snapshot PNG via Playwright para preview inline.

---

## 12.1. Logs (`logging_setup.py`)

Double-sink, igual ao FlowETL: **console** + **arquivo**.

```
- Arquivo: logs/book_AAAA-MM-DD.log (um por dia; rotação por data no nome).
- Formato: "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
- Nível: INFO no console, DEBUG no arquivo (configurável por LOG_LEVEL no .env, opcional).
- Cada etapa loga início/fim: download, leitura, transform, render, email, telegram.
- Erros: log.exception(...) grava o traceback COMPLETO no arquivo; o Telegram recebe só o resumo.
- O caminho do log do dia entra na mensagem de erro do Telegram (pra você achar rápido).
```

Assim: Telegram = alerta curto/imediato; arquivo de log = detalhe completo para diagnóstico.

---

## 12.2. Execução manual ("rodar na mão")

O job roda sozinho às 09:00, mas você pode disparar uma rodada completa a qualquer momento:

```bash
# rodada completa agora (download -> transform -> render -> e-mail -> alerta Telegram)
python run.py

# só validar o transform contra a planilha, sem e-mail nem Telegram:
python -m src.book_ti.transform --arquivo tests/fixtures/sample.xlsx --dry-run

# gerar o book localmente e abrir no navegador, sem enviar nada:
python run.py --no-email --no-telegram        # flags a implementar no run.py
```

`run.py` deve aceitar flags `--no-email` e `--no-telegram` para testes locais sem efeitos colaterais,
e sair com código `!= 0` em caso de falha (pro cron/Telegram saberem que quebrou).

### Prompt pronto pro Claude Code (kickoff no VSCode)
Cole isto na primeira mensagem do Claude Code, com o `CLAUDE.md` na raiz do projeto:

> "Leia o CLAUDE.md por completo. Implemente as Fases 0 e 1: estrutura de pastas, requirements.txt,
> .gitignore, .env.example, config.py, logging_setup.py, templates/book_template.html (a partir do
> mock, com o marcador), transform.py e test_transform.py. O test_transform.py deve rodar contra
> tests/fixtures/sample.xlsx e afirmar exatamente: total=1595, inc=1248, sol=347, sla=64, res=1589,
> NF=101, Estoque=35, Pedido=167. Rode o pytest e me mostre verde antes de seguir para o Drive/e-mail."

---

- Logging double-sink (console + `logs/book_AAAA-MM-DD.log`), igual ao FlowETL.
- Alertas Telegram nunca derrubam o pipeline; se token/chat vazios, viram no-op.
- Nada de segredos no código nem no Git: `.env` e o token do Telegram são *gitignored*.
- Toda agregação testável isoladamente (input DataFrame → output dict), sem depender de Drive/SMTP.
- `run.py` deve ser idempotente: rodar 2x no mesmo dia só regera o book/e-mail, sem efeito colateral persistente.
- Código e comentários em PT-BR; nomes de variáveis podem ser em inglês.

---

## 14. Comandos úteis

```bash
# setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# rodar uma vez (manual)
python run.py

# rodar o agendador residente (09:00)
python -m src.book_ti.scheduler

# testes
pytest -q

# testar só o alerta Telegram (sem rodar o pipeline):
python -c "from src.book_ti import notifier; notifier.send('teste de alerta ✅')"

# cron WSL alternativo (one-shot às 09:00):
# 0 9 * * * cd /caminho/book-operacoes-ti && /caminho/.venv/bin/python run.py >> logs/cron.log 2>&1
```
