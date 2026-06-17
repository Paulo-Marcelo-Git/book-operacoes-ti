"""Agendador residente: executa o pipeline todo dia no horário do .env (default 09:00)."""
from apscheduler.schedulers.blocking import BlockingScheduler

from . import config, pipeline
from .logging_setup import get_logger

log = get_logger()


def main():
    sched = BlockingScheduler(timezone=config.TIMEZONE)
    sched.add_job(pipeline.run, "cron",
                  hour=config.SCHEDULE_HOUR, minute=config.SCHEDULE_MINUTE)
    log.info("Agendador ativo: todo dia às %02d:%02d (%s). Ctrl+C para sair.",
             config.SCHEDULE_HOUR, config.SCHEDULE_MINUTE, config.TIMEZONE)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Agendador encerrado.")


if __name__ == "__main__":
    main()
