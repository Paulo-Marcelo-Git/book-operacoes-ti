"""Entrypoint para rodar UMA rodada na mão.

Exemplos:
    python run.py                          # rodada completa (Drive -> e-mail -> Telegram)
    python run.py --no-email --no-telegram # gera o book local, sem efeitos colaterais
    python run.py --arquivo caminho.xlsx   # usa um xlsx local em vez do Drive
"""
import argparse
import sys

from src.book_ti import pipeline


def main():
    p = argparse.ArgumentParser(description="Book Operações de TI — rodada manual")
    p.add_argument("--no-email", action="store_true", help="não envia e-mail")
    p.add_argument("--no-telegram", action="store_true", help="não envia alerta Telegram")
    p.add_argument("--arquivo", help="usa um .xlsx local em vez de baixar do Drive")
    args = p.parse_args()

    try:
        pipeline.run(no_email=args.no_email, no_telegram=args.no_telegram, arquivo=args.arquivo)
    except Exception:
        sys.exit(1)   # código != 0 para o cron/Telegram saberem que falhou


if __name__ == "__main__":
    main()
