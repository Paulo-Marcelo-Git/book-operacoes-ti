"""Configuração central: carrega o .env e expõe constantes do projeto.

Nenhum segredo é escrito aqui — tudo vem do .env (que NÃO é versionado).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Raiz do repositório: este arquivo está em src/book_ti/config.py -> sobe 3 níveis.
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=True)

# ------------------------------------------------------------------ Inbox local
INBOX_DIR = BASE_DIR / os.getenv("INBOX_DIR", "inbox")
INBOX_DIR.mkdir(exist_ok=True)
(INBOX_DIR / "processados").mkdir(exist_ok=True)

# ----------------------------------------------------------------------- Email
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")
EMAIL_DESTINATARIO = os.getenv("EMAIL_DESTINATARIO", "")
EMAIL_SMTP = os.getenv("EMAIL_SMTP", "smtp.gmail.com")
EMAIL_PORTA = int(os.getenv("EMAIL_PORTA", "587"))
EMAIL_ASSUNTO_PREFIXO = os.getenv("EMAIL_ASSUNTO_PREFIXO", "Book Operações de TI")


def destinatarios() -> list[str]:
    """Lista de destinatários (aceita vários separados por vírgula no .env)."""
    return [e.strip() for e in EMAIL_DESTINATARIO.split(",") if e.strip()]


# -------------------------------------------------------------------- Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ------------------------------------------------------------------- Caminhos
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "output")
LOG_DIR = BASE_DIR / os.getenv("LOG_DIR", "logs")
TEMPLATE_PATH = BASE_DIR / "templates" / "book_template.html"
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------- Agendamento
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "9"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")

# --------------------------------------------- Mapeamento de colunas (por LETRA)
# Confirmado contra a planilha real (1.595 linhas).
COLUNAS = {
    "sla":          "E",   # 'Sla Violado.'                -> == 'Sim'
    "tipo":         "H",   # 'Tipo de Registro de Serviço' -> Incidente/Solicitação
    "descricao":    "I",   # 'Descrição'                   -> keywords
    "status":       "J",   # 'Legenda'                     -> == 'Resolvido'
    "subcategoria": "L",   # 'Subcategoria'                -> ofensores
    "solicitante":  "O",   # 'Usuário Solicitante'        -> top 10
    "grupo":        "P",   # 'Grupo solucionador'         -> divisão por grupo
    "analista":     "Q",   # 'Analista responsável'       -> divisão por analista
}


def col_idx(letra: str) -> int:
    """Converte letra de coluna do Excel (ex.: 'P') em índice 0-based do pandas."""
    idx = 0
    for ch in letra.upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1
