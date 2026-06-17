"""Monta e envia o e-mail: corpo email-safe (sem JS) + book completo em anexo."""
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from . import config
from .logging_setup import get_logger

log = get_logger()


def _corpo_html(D: dict) -> str:
    """Corpo HTML compatível com Outlook/Gmail (tabelas + CSS inline, sem <script>)."""
    def linhas(itens, label_key, val_key):
        return "".join(
            f"<tr><td style='padding:5px 12px;border-bottom:1px solid #eee'>{it[label_key]}</td>"
            f"<td style='padding:5px 12px;border-bottom:1px solid #eee;text-align:right;"
            f"font-weight:700'>{it[val_key]}</td></tr>"
            for it in itens
        )

    kpis = [
        ("Total de chamados", D["total"], "#2563eb"),
        ("Incidentes", D["inc_total"], "#f59e0b"),
        ("Solicitações", D["sol_total"], "#4f46e5"),
        ("SLA violado", D["sla_total"], "#ef4444"),
    ]
    cards = "".join(
        f"<td style='padding:14px 18px;background:#fff;border-top:4px solid {cor};"
        f"border-radius:8px'>"
        f"<div style='font-size:11px;color:#94a3b8;text-transform:uppercase'>{lbl}</div>"
        f"<div style='font-size:26px;font-weight:800;color:#0f172a'>{val}</div></td>"
        f"<td style='width:12px'></td>"
        for lbl, val, cor in kpis
    )

    return f"""\
<div style="font-family:Segoe UI,Arial,sans-serif;background:#f1f5f9;padding:24px">
  <h2 style="color:#0f172a;margin:0 0 4px">Book – Operações de TI</h2>
  <p style="color:#64748b;margin:0 0 18px">Gerado em {datetime.now():%d/%m/%Y %H:%M}</p>

  <table cellpadding="0" cellspacing="0"><tr>{cards}</tr></table>

  <h3 style="color:#0f172a;margin:24px 0 8px">Por grupo solucionador</h3>
  <table cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;
         font-size:14px;color:#1e293b">{linhas(D['grupos'], 'grupo', 'total')}</table>

  <h3 style="color:#0f172a;margin:24px 0 8px">Top 5 solicitantes</h3>
  <table cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;
         font-size:14px;color:#1e293b">
         {linhas(D['top_solicitantes'][:5], 'solicitante', 'total')}</table>

  <p style="color:#64748b;margin-top:22px;font-size:13px">
     O <b>book completo e interativo</b> (com todos os gráficos) está em anexo —
     abra no navegador.</p>
</div>"""


def enviar(html_path, D: dict) -> int:
    """Envia o e-mail. Retorna o número de destinatários. Levanta erro se mal configurado."""
    if not config.EMAIL_PASS:
        raise RuntimeError("EMAIL_PASS vazio — defina a App Password do Gmail no .env.")
    dests = config.destinatarios()
    if not dests:
        raise RuntimeError("EMAIL_DESTINATARIO vazio no .env.")

    msg = EmailMessage()
    msg["Subject"] = f"{config.EMAIL_ASSUNTO_PREFIXO} — {datetime.now():%d/%m/%Y}"
    msg["From"] = config.EMAIL_USER
    msg["To"] = ", ".join(dests)
    msg.set_content("Seu cliente de e-mail não suporta HTML. O book está em anexo.")
    msg.add_alternative(_corpo_html(D), subtype="html")

    dados = Path(html_path).read_bytes()
    msg.add_attachment(dados, maintype="text", subtype="html",
                       filename=Path(html_path).name)

    with smtplib.SMTP(config.EMAIL_SMTP, config.EMAIL_PORTA) as smtp:
        smtp.starttls()
        smtp.login(config.EMAIL_USER, config.EMAIL_PASS)
        smtp.send_message(msg)

    log.info("E-mail enviado para %s", dests)
    return len(dests)
