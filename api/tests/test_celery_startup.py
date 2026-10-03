from app.celery_app import STARTUP_SOURCES, app, startup_refresh


def test_startup_refresh_fetches_boundary_before_every_scheduled_source():
    workflow = startup_refresh()
    boundary, sources = workflow.tasks

    assert boundary.task == "app.sources.boundary.fetch_krakow_boundary"
    assert [s.task for s in sources.tasks] == STARTUP_SOURCES
    scheduled = {e["task"] for e in app.conf.beat_schedule.values()}
    assert scheduled == set(STARTUP_SOURCES) | {boundary.task}
