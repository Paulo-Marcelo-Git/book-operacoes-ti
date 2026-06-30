"""Agendador residente: executa o pipeline todo dia no horário do .env (default 09:00).

Se a inbox estiver vazia (FileNotFoundError), retenta a cada 5 min por até 2 horas.
"""
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler

from . import config, notifier, pipeline
from .logging_setup import current_log_path, get_logger

log = get_logger()

_RETRY_MIN = 5
_MAX_MIN = 120
_MAX_TENTATIVAS = _MAX_MIN // _RETRY_MIN  # 24


def main():
    sched = BlockingScheduler(timezone=config.TIMEZONE)
    _tentativas = {"n": 0}

    def _executar():
        try:
            pipeline.run()
            _tentativas["n"] = 0
        except FileNotFoundError as exc:
            _tentativas["n"] += 1
            if _tentativas["n"] <= _MAX_TENTATIVAS:
                prox = datetime.now() + timedelta(minutes=_RETRY_MIN)
                log.warning(
                    "inbox/ vazia — tentativa %d/%d. Próxima em %d min (%s).",
                    _tentativas["n"], _MAX_TENTATIVAS, _RETRY_MIN,
                    prox.strftime("%H:%M"),
                )
                sched.add_job(_executar, "date", run_date=prox,
                              id="retry", replace_existing=True,
                              misfire_grace_time=300)
            else:
                log.error(
                    "inbox/ vazia após %d tentativas (%dh). Encerrando retentativas.",
                    _MAX_TENTATIVAS, _MAX_MIN // 60,
                )
                _tentativas["n"] = 0
                notifier.erro("download", None, exc, current_log_path())
        except Exception:
            _tentativas["n"] = 0
            raise

    sched.add_job(_executar, "cron",
                  hour=config.SCHEDULE_HOUR, minute=config.SCHEDULE_MINUTE,
                  misfire_grace_time=300)
    log.info("Agendador ativo: todo dia às %02d:%02d (%s). Ctrl+C para sair.",
             config.SCHEDULE_HOUR, config.SCHEDULE_MINUTE, config.TIMEZONE)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Agendador encerrado.")


if __name__ == "__main__":
    main()
