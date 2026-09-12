"""Unit tests for StepMeters configuration component in Setup Wizard."""

from unittest.mock import MagicMock, patch

from data_classes import MeterConfig
from gui.step_meters import Meter, MeterParams, MeterStep


def test_meter_init_and_update():
    on_del = MagicMock()
    m = Meter(["digit1", "digit2", "analog1"], "main_meter", on_delete=on_del)
    assert m.name_candidate == "main_meter"
    assert m.meter.name == "main_meter"

    m.digits = MagicMock(value=["digit1", "digit2", ".", "analog1"])
    m.preview_label = MagicMock()
    m.meter.unit = "m3"

    m.update_vals()
    assert m.meter.value == "{digit1}{digit2}.{analog1}"
    assert "{digit1}{digit2}.{analog1} m3" in m.preview_label.text


def test_meter_show_new_and_remove():
    with patch("gui.step_meters.ui") as mock_ui:
        mock_ui.card.return_value.__enter__ = MagicMock()
        mock_ui.card.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.grid.return_value.__enter__ = MagicMock()
        mock_ui.grid.return_value.__exit__ = MagicMock()

        on_del = MagicMock()
        m = Meter(["digit1"], "total", on_delete=on_del)
        params = m.show_new()
        assert isinstance(params, MeterParams)
        assert params.name == "total"

        m.remove()
        m.value_container.clear.assert_called_once()
        m.value_container.delete.assert_called_once()


def test_step_meters_load_and_add_remove():
    get_digit_names = MagicMock(return_value=["digit1", "digit2", "analog1"])
    set_img = MagicMock()
    step = MeterStep(
        name="Meters",
        set_image_callback=set_img,
        get_digit_names_func=get_digit_names,
    )

    with patch("gui.step_meters.ui") as mock_ui:
        mock_ui.card.return_value.__enter__ = MagicMock()
        mock_ui.card.return_value.__exit__ = MagicMock()
        mock_ui.row.return_value.__enter__ = MagicMock()
        mock_ui.row.return_value.__exit__ = MagicMock()
        mock_ui.grid.return_value.__enter__ = MagicMock()
        mock_ui.grid.return_value.__exit__ = MagicMock()

        step.values_container = MagicMock()
        step.values_container.__enter__ = MagicMock()
        step.values_container.__exit__ = MagicMock()

        configs = [
            MeterConfig(
                name="total",
                format="{digit1}{digit2}.{analog1}",
                consistency_enabled=True,
                allow_negative_rates=False,
                max_rate_value=0.2,
                use_previous_value=True,
                pre_value_from_file_max_age=15,
                use_extended_resolution=True,
                unit="m3",
            )
        ]

        step.load_from_config(configs)
        assert len(step.meters) == 1
        assert len(step.meter_params) == 1
        assert step.meter_params[0].name == "total"
        assert step.meter_params[0].consistency_enabled is True

        # Add another meter
        step._add_meter()
        assert len(step.meters) == 2
        assert len(step.meter_params) == 2
        assert step.meter_params[1].name == "Meter2"

        # Remove meter
        step._remove_meter()
        assert len(step.meters) == 1
        assert len(step.meter_params) == 1

        # Delete remaining meter via callback
        step._delete_meter(step.meters[0])
        assert len(step.meters) == 0
        assert len(step.meter_params) == 0


def test_meter_update_digit_names_options():
    m = Meter(["digit1"], "total")
    m.digits = MagicMock(value=["digit1", "."], options=["digit1", "."])
    m.preview_label = MagicMock()
    m.meter.unit = "m3"

    m.update_digit_names(["digit1", "digit2", "digit3", "analog1"])
    assert m.digits.options == ["digit1", "digit2", "digit3", "analog1", "."]
    m.digits.update.assert_called_once()


def test_meter_step_refresh_digit_names():
    digit_names_store = ["digit1", "digit2"]
    step = MeterStep(
        name="Meters",
        set_image_callback=MagicMock(),
        get_digit_names_func=lambda: list(digit_names_store),
    )

    m1 = Meter(list(digit_names_store), "total")
    m1.digits = MagicMock(value=["digit1"], options=["digit1", "digit2", "."])
    m1.preview_label = MagicMock()
    step.meters.append(m1)

    # Simulate user adding new digital and analog ROIs in previous steps
    digit_names_store.extend(["digit3", "analog1", "analog2"])

    step.refresh_digit_names()
    assert m1.digits.options == [
        "digit1",
        "digit2",
        "digit3",
        "analog1",
        "analog2",
        ".",
    ]
