from celery import Celery
from celery.schedules import crontab

from app.config import settings

app = Celery(
    "kryzio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.sources.shelters",
        "app.sources.tauron",
        "app.sources.imgw",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

app.conf.beat_schedule = {
    "fetch-shelters-every-2h": {
        "task": "app.sources.shelters.fetch_shelters",
        "schedule": 7200.0,
    },
    "fetch-tauron-every-30min": {
        "task": "app.sources.tauron.fetch_tauron_outages",
        "schedule": 1800.0,
    },
    "fetch-imgw-hydro-every-45min": {
        "task": "app.sources.imgw.fetch_imgw_hydro",
        "schedule": 2700.0,
    },
    "fetch-imgw-warnings-every-45min": {
        "task": "app.sources.imgw.fetch_imgw_warnings",
        "schedule": 2700.0,
    },
}

