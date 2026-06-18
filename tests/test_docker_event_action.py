from app.models.docker_event_action import DockerEventAction


def test_health_status_details_match_documented_action() -> None:
    assert DockerEventAction.normalize("health_status: unhealthy") == "health_status"
    assert DockerEventAction.HEALTH_STATUS.matches("health_status: healthy")


def test_from_raw_returns_matching_action() -> None:
    assert DockerEventAction.from_raw("die") == DockerEventAction.DIE
    assert (
        DockerEventAction.from_raw("health_status: healthy")
        == DockerEventAction.HEALTH_STATUS
    )


def test_from_raw_returns_none_for_unknown_action() -> None:
    assert DockerEventAction.from_raw("made_up_action") is None
