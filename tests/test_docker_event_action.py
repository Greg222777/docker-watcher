from app.models.docker_event_action import DockerEventAction


class TestDockerEventAction:
    def test_normalizes_health_status_details(self) -> None:
        assert (
            DockerEventAction.normalize("health_status: unhealthy") == "health_status"
        )

    def test_from_raw_returns_matching_action(self) -> None:
        assert DockerEventAction.from_raw("die") == DockerEventAction.DIE
        assert (
            DockerEventAction.from_raw("health_status: healthy")
            == DockerEventAction.HEALTH_STATUS
        )

    def test_from_raw_returns_none_for_unknown_action(self) -> None:
        assert DockerEventAction.from_raw("made_up_action") is None

    def test_matches_normalized_actions(self) -> None:
        assert DockerEventAction.HEALTH_STATUS.matches("health_status: healthy")
