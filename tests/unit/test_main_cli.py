"""Unit tests for main application lifecycle, services orchestration, and helpers."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException

import main


def test_main_start_and_stop_services():
    mock_app = FastAPI()
    with (
        patch("main.app", mock_app),
        patch("main.MQTTService") as MockMQTT,
        patch("main.BackgroundPoller") as MockPoller,
        patch("main.ZeroFlowTracker"),
    ):
        main.config.mqtt.enabled = True
        main.config.poller.enabled = True

        main.start_services()
        assert mock_app.state.zero_flow_tracker is not None
        MockMQTT.return_value.start.assert_called_once()
        MockPoller.return_value.start.assert_called_once()

        main.stop_services()
        MockPoller.return_value.stop.assert_called_once()
        MockMQTT.return_value.stop.assert_called_once()


def test_main_lifespan():
    mock_app = FastAPI()
    with (
        patch("main.init_config") as mock_init,
        patch("main.stop_services") as mock_stop,
    ):

        async def run_lifespan():
            async with main.lifespan(mock_app):
                pass

        asyncio.run(run_lifespan())
        mock_init.assert_called_once()
        mock_stop.assert_called_once()


def test_main_image_and_config_helpers(tmp_path):
    test_cfg_file = tmp_path / "config.ini"
    test_cfg_file.write_text("[DEFAULT]\nLogLevel = INFO\n")

    with patch("main.config_file", str(test_cfg_file)):
        # Test load_config_file
        content = main.load_config_file()
        assert "LogLevel = INFO" in content

        # Test save_config_file
        main.save_config_file("[DEFAULT]\nLogLevel = DEBUG\n")
        assert "DEBUG" in main.load_config_file()

        # Test backup helpers
        with patch("config_history.ConfigHistoryManager") as MockMgr:
            MockMgr.list_backups.return_value = []
            MockMgr.undo_last.return_value = "undone"
            MockMgr.create_backup.return_value = "created"
            MockMgr.delete_backup.return_value = True
            MockMgr.get_diff.return_value = ["diff"]

            assert main.list_config_backups() == []
            main.restore_config_backup("bak1")
            MockMgr.restore_backup.assert_called_once_with(str(test_cfg_file), "bak1")

            assert main.undo_last_config() == "undone"
            assert main.create_config_snapshot("snap") == "created"
            assert main.delete_config_backup("bak1") is True
            assert main.diff_config_backup("bak1") == ["diff"]


def test_main_get_image_as_base64_str():
    with patch("main.app") as mock_app:
        mock_cache = MagicMock()
        mock_app.state.image_cache = mock_cache

        # 1. Cached image found
        mock_img = MagicMock()
        mock_cache.get.return_value = mock_img
        with patch("utils.image.convert_image_base64str", return_value="dGVzdA=="):
            res = main.get_image_as_base64_str("final")
            assert res == "dGVzdA=="

        # 2. Not found
        mock_cache.get.return_value = None
        with pytest.raises(HTTPException):
            main.get_image_as_base64_str("unknown_image")


def test_main_init_gui():
    mock_app = FastAPI()
    mock_app.state.zero_flow_tracker = MagicMock()
    mock_app.state.poller = MagicMock()
    mock_app.state.mqtt_service = MagicMock()

    with patch("gui.frontend.init") as mock_front_init:
        main.init_gui(mock_app)
        mock_front_init.assert_called_once()
