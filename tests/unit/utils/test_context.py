"""Unit tests for AppContext container and dependency provider in src/context.py."""

from unittest.mock import MagicMock

from context import AppContext, get_app_context
from data_classes import (
    ConfigBackupInfo,
    MQTTStatus,
    PollerStatus,
    TimelineFrame,
    VisualDiffMetrics,
)


def test_app_context_initialization_and_property():
    mock_config = MagicMock()
    mock_storage = MagicMock()
    mock_cache = MagicMock()
    mock_tracker = MagicMock()
    mock_mqtt = MagicMock()
    mock_poller = MagicMock()

    ctx = AppContext(
        config=mock_config,
        config_file="/config/test.ini",
        config_version=2,
        storage=mock_storage,
        cache=mock_cache,
        zero_flow_tracker=mock_tracker,
        mqtt_service=mock_mqtt,
        poller=mock_poller,
        version="1.2.3",
        start_time=100.0,
        started_at="2026-01-01T12:00:00Z",
    )

    assert ctx.config == mock_config
    assert ctx.config_file == "/config/test.ini"
    assert ctx.config_version == 2
    assert ctx.storage == mock_storage
    assert ctx.cache == mock_cache
    assert ctx.image_cache == mock_cache
    assert ctx.zero_flow_tracker == mock_tracker
    assert ctx.mqtt_service == mock_mqtt
    assert ctx.poller == mock_poller
    assert ctx.version == "1.2.3"
    assert ctx.start_time == 100.0
    assert ctx.started_at == "2026-01-01T12:00:00Z"


def test_get_app_context_from_request():
    mock_request = MagicMock()
    mock_app = MagicMock()
    mock_request.app = mock_app

    mock_app.state.config = MagicMock()
    mock_app.state.config_file = "/config/config.ini"
    mock_app.state.config_version = 3
    mock_app.state.storage = MagicMock()
    mock_app.state.image_cache = MagicMock()
    mock_app.state.zero_flow_tracker = MagicMock()
    mock_app.state.mqtt_service = MagicMock()
    mock_app.state.poller = MagicMock()
    mock_app.state.version = "2.0.0"
    mock_app.state.start_time = 50.0
    mock_app.state.started_at = "2026-09-01T00:00:00Z"

    ctx = get_app_context(mock_request)
    assert ctx.config == mock_app.state.config
    assert ctx.config_file == "/config/config.ini"
    assert ctx.config_version == 3
    assert ctx.storage == mock_app.state.storage
    assert ctx.cache == mock_app.state.image_cache
    assert ctx.image_cache == mock_app.state.image_cache
    assert ctx.zero_flow_tracker == mock_app.state.zero_flow_tracker
    assert ctx.mqtt_service == mock_app.state.mqtt_service
    assert ctx.poller == mock_app.state.poller
    assert ctx.version == "2.0.0"


def test_dict_access_mixin_on_typed_models():
    # 1. PollerStatus
    poller = PollerStatus(enabled=True, running=True, interval_seconds=120)
    assert poller.enabled is True
    assert poller["enabled"] is True
    assert poller.get("enabled") is True
    assert poller.get("missing_key", "default") == "default"
    assert "running" in poller

    # 2. MQTTStatus
    mqtt = MQTTStatus(
        enabled=True,
        connected=True,
        broker="mqtt.local",
        last_published_topics={"watermeter/total/value": "123.45"},
        last_published_readout={"total": 123.45},
    )
    assert mqtt.broker == "mqtt.local"
    assert mqtt["broker"] == "mqtt.local"
    assert mqtt.get("broker") == "mqtt.local"
    assert "connected" in mqtt
    assert mqtt.last_published_topics["watermeter/total/value"] == "123.45"
    assert mqtt.last_published_readout["total"] == 123.45

    # 3. ConfigBackupInfo
    backup = ConfigBackupInfo(name="backup_1.ini", size_bytes=1024)
    assert backup.name == "backup_1.ini"
    assert backup["size_bytes"] == 1024
    assert backup.get("name") == "backup_1.ini"

    # 4. TimelineFrame
    frame = TimelineFrame(id=42, timestamp="2026-09-19T10:00:00Z", has_frame=True)
    assert frame.id == 42
    assert frame["id"] == 42
    assert frame.get("has_frame") is True

    # 5. VisualDiffMetrics
    diff = VisualDiffMetrics(reading_id=1, ssim_similarity=0.98, is_anomaly=False)
    assert diff.reading_id == 1
    assert diff["ssim_similarity"] == 0.98
    assert diff.get("is_anomaly") is False
