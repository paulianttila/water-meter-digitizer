"""Unit tests for the harmonized engine test dialog component."""

import asyncio
from unittest.mock import MagicMock, patch

from configuration import Config
from gui.components.engine_test_dialog import (
    extract_meter_readouts,
    render_roi_overlay,
    run_engine_test_dialog,
)
from processor.digitizer import MeterResult, MeterValue


def test_extract_meter_readouts_with_multiple_meters():
    """Test extracting all configured meters and individual readout cards."""
    result = MeterResult(
        meters=[
            MeterValue(
                name="total",
                value="00452.912",
                unit="m³",
                quality="good",
                confidence=98.5,
            ),
            MeterValue(
                name="digital",
                value="00452",
                unit="",
                quality="good",
                confidence=99.1,
            ),
            MeterValue(
                name="analog",
                value="0912",
                unit="",
                quality="warning",
                confidence=92.0,
            ),
        ],
        digital_results={"D1": "0", "D2": "0", "D3": "4", "D4": "5", "D5": "2"},
        analog_results={"A1": "9", "A2": "1", "A3": "2"},
        confidence_scores={"D1": 99.1, "D2": 99.4, "A1": 95.0},
    )

    meters_list, readouts = extract_meter_readouts(result)
    assert len(meters_list) == 3

    assert meters_list[0]["name"] == "total"
    assert meters_list[0]["value"] == "00452.912"
    assert meters_list[0]["unit"] == "m³"
    assert meters_list[0]["quality"] == "good"
    assert meters_list[0]["confidence"] == 98.5

    assert meters_list[1]["name"] == "digital"
    assert meters_list[1]["value"] == "00452"

    assert meters_list[2]["name"] == "analog"
    assert meters_list[2]["value"] == "0912"
    assert meters_list[2]["quality"] == "warning"

    assert len(readouts) == 8
    d1 = next(r for r in readouts if r["name"] == "D1")
    assert d1["value"] == "0"
    assert d1["confidence"] == 99.1
    assert d1["is_digit"] is True

    a1 = next(r for r in readouts if r["name"] == "A1")
    assert a1["value"] == "9"
    assert a1["confidence"] == 95.0
    assert a1["is_digit"] is False


def test_extract_meter_readouts_fallback_empty():
    """Test extraction with empty MeterResult."""
    result = MeterResult()
    meters_list, readouts = extract_meter_readouts(result)
    assert len(meters_list) == 1
    assert meters_list[0]["value"] == "N/A"
    assert meters_list[0]["quality"] == "good"
    assert readouts == []


def test_render_roi_overlay_with_bytes():
    """Test rendering ROI overlay when raw bytes are provided."""
    import io

    import PIL.Image

    # Create dummy 100x100 RGB image
    img = PIL.Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    cfg = Config()
    overlay_uri = render_roi_overlay(cfg, image_bytes=raw_bytes)
    assert overlay_uri.startswith("data:image/jpeg;base64,")


def test_render_roi_overlay_error_graceful():
    """Test render_roi_overlay graceful failure returns empty string on invalid data."""
    cfg = Config()
    overlay_uri = render_roi_overlay(cfg, image_bytes=b"not an image")
    assert overlay_uri == ""


def test_run_engine_test_dialog_success():
    """Test run_engine_test_dialog executes inference and opens modal dialog."""
    mock_callbacks = MagicMock()
    mock_result = MeterResult(
        meters=[
            MeterValue(name="digital", value="12345"),
            MeterValue(name="total", value="12345.678", unit="m³"),
        ],
        digital_results={"D1": "1"},
    )
    mock_callbacks.get_meter_data.return_value = mock_result

    cfg = Config()
    spinner_mock = MagicMock()

    with (
        patch("gui.components.engine_test_dialog.ui.notify"),
        patch(
            "gui.components.engine_test_dialog.show_engine_test_modal"
        ) as mock_show_modal,
        patch(
            "gui.components.engine_test_dialog.render_roi_overlay",
            return_value="data:image/jpeg;base64,abc",
        ),
    ):
        asyncio.run(
            run_engine_test_dialog(
                config=cfg,
                callbacks=mock_callbacks,
                title_tag="Test Tag",
                parent_spinner=spinner_mock,
            )
        )

        mock_callbacks.get_meter_data.assert_called_once()
        mock_show_modal.assert_called_once()
        assert spinner_mock.visible is False


def test_run_engine_test_dialog_callbacks_none():
    """Test run_engine_test_dialog warns when callbacks is None."""
    with patch("gui.components.engine_test_dialog.ui.notify") as mock_notify:
        asyncio.run(
            run_engine_test_dialog(
                config=Config(),
                callbacks=None,
            )
        )
        mock_notify.assert_called_once_with(
            "Callbacks unavailable in standalone testing mode", type="warning"
        )


def test_run_engine_test_dialog_failure_handling():
    """Test run_engine_test_dialog handles backend exceptions cleanly."""
    mock_callbacks = MagicMock()
    mock_callbacks.get_meter_data.side_effect = RuntimeError(
        "Inference connection dropped"
    )

    with patch("gui.components.engine_test_dialog.ui.notify") as mock_notify:
        asyncio.run(
            run_engine_test_dialog(
                config=Config(),
                callbacks=mock_callbacks,
            )
        )
        # Should notify info for start and negative for error
        assert any("Engine test failed" in str(c) for c in mock_notify.call_args_list)
