from celery import Celery

from app.config import settings

app = Celery(
    "kryzio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.sources.shelters",
        "app.sources.tauron",
        "app.sources.imgw",
        "app.sources.boundary",
        "app.sources.gios",
        "app.sources.airly",
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
    "fetch-krakow-boundary-weekly": {
        "task": "app.sources.boundary.fetch_krakow_boundary",
        "schedule": 7 * 24 * 3600.0,
    },
    "fetch-gios-air-quality-hourly": {
        "task": "app.sources.gios.fetch_gios_air_quality",
        "schedule": 3600.0,
    },
    # Airly rate limit: never more often than every 2h (SPEC)
    "fetch-airly-air-quality-every-2h": {
        "task": "app.sources.airly.fetch_airly_air_quality",
        "schedule": 7200.0,
    },
}
