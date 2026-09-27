"""Unit tests for model_alignment_dialog."""

import base64
import io
from typing import Any
from unittest.mock import MagicMock, patch

from PIL import Image

from config.meter_presets import MeterTypePreset, PresetRoiBox
from gui.dialogs.model_alignment_dialog import open_model_alignment_dialog


def _create_test_image_b64(width: int = 640, height: int = 480) -> str:
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def test_open_model_alignment_dialog_empty_image():
    """Verify warning notification and early return on empty image."""
    preset = MagicMock(spec=MeterTypePreset)
    with patch("gui.dialogs.model_alignment_dialog.ui") as mock_ui:
        open_model_alignment_dialog(
            camera_image_b64="",
            preset=preset,
        )
        mock_ui.notify.assert_called_once_with(
            "No camera image loaded to align", type="warning"
        )
        mock_ui.dialog.assert_not_called()


def test_open_model_alignment_dialog_invalid_image():
    """Verify error notification on corrupt image string."""
    preset = MagicMock(spec=MeterTypePreset)
    with patch("gui.dialogs.model_alignment_dialog.ui") as mock_ui:
        open_model_alignment_dialog(
            camera_image_b64="not-a-valid-base64-image",
            preset=preset,
        )
        mock_ui.notify.assert_called_once_with("Invalid camera image", type="negative")
        mock_ui.dialog.assert_not_called()


def test_open_model_alignment_dialog_opens_and_renders():
    """Verify dialog opens, creates interactive image and applies alignment calculation."""
    b64_img = _create_test_image_b64(640, 480)

    preset = MeterTypePreset(
        id="test_meter",
        label="Test Meter",
        description="Test Meter description",
        reference_resolution={"width": 640, "height": 480},
    )
    preset.alignment.references = [
        PresetRoiBox(name="ref0", x=50, y=50, w=40, h=40),
        PresetRoiBox(name="ref1", x=500, y=50, w=40, h=40),
        PresetRoiBox(name="ref2", x=300, y=400, w=40, h=40),
    ]
    preset.default_rois.digital = [
        PresetRoiBox(name="digit1", x=200, y=150, w=45, h=75),
        PresetRoiBox(name="digit2", x=250, y=150, w=45, h=75),
    ]
    preset.default_rois.analog = [
        PresetRoiBox(name="analog1", x=150, y=300, w=50, h=50),
    ]

    on_applied = MagicMock()

    with patch("gui.dialogs.model_alignment_dialog.ui") as mock_ui:
        mock_dialog = MagicMock()
        mock_dialog.__enter__.return_value = mock_dialog
        mock_dialog.props.return_value = mock_dialog
        mock_ui.dialog.return_value = mock_dialog

        mock_card = MagicMock()
        mock_card.__enter__.return_value = mock_card
        mock_ui.card.return_value = mock_card

        mock_row = MagicMock()
        mock_row.__enter__.return_value = mock_row
        mock_ui.row.return_value = mock_row

        mock_col = MagicMock()
        mock_col.__enter__.return_value = mock_col
        mock_ui.column.return_value = mock_col

        mock_viewport = MagicMock()
        mock_viewport.classes.return_value = mock_viewport
        mock_ui.interactive_image.return_value = mock_viewport

        mock_slider = MagicMock()
        mock_slider.props.return_value = mock_slider
        mock_slider.classes.return_value = mock_slider
        mock_ui.slider.return_value = mock_slider

        mock_btn = MagicMock()
        mock_btn.props.return_value = mock_btn
        mock_btn.classes.return_value = mock_btn
        mock_ui.button.return_value = mock_btn

        open_model_alignment_dialog(
            camera_image_b64=b64_img,
            preset=preset,
            digital_names=["digit1", "digit2"],
            analog_names=["analog1"],
            on_applied=on_applied,
        )

        mock_dialog.open.assert_called_once()
        mock_viewport.set_source.assert_called_once()

        # Find the Apply button call
        apply_btn_calls = [
            c
            for c in mock_ui.button.call_args_list
            if "Apply Alignment" in str(c.args or "")
        ]
        assert len(apply_btn_calls) == 1
        apply_handler = apply_btn_calls[0].kwargs.get("on_click")
        assert apply_handler is not None

        # Execute apply
        apply_handler()

        on_applied.assert_called_once()
        results = on_applied.call_args[0][0]
        assert "references" in results
        assert "digital" in results
        assert "analog" in results
        assert len(results["references"]) == 3
        assert len(results["digital"]) == 2
        assert len(results["analog"]) == 1
        mock_dialog.close.assert_called_once()


def test_open_model_alignment_dialog_svg_shapes_and_visibility_toggle():
    """Verify SVG includes inner/outer digit boxes, analog circles and crosshairs,

    and that individual ROIs can be hidden/unhidden.
    """
    b64_img = _create_test_image_b64(640, 480)

    preset = MeterTypePreset(
        id="test_meter",
        label="Test Meter",
        description="Test Meter description",
        reference_resolution={"width": 640, "height": 480},
    )
    preset.alignment.references = [
        PresetRoiBox(name="ref0", x=50, y=50, w=40, h=40),
    ]
    preset.default_rois.digital = [
        PresetRoiBox(name="digit1", x=200, y=150, w=50, h=80),
        PresetRoiBox(name="digit2", x=260, y=150, w=50, h=80),
    ]
    preset.default_rois.analog = [
        PresetRoiBox(name="analog1", x=150, y=300, w=60, h=60),
    ]

    with patch("gui.dialogs.model_alignment_dialog.ui") as mock_ui:
        mock_dialog = MagicMock()
        mock_dialog.__enter__.return_value = mock_dialog
        mock_dialog.props.return_value = mock_dialog
        mock_ui.dialog.return_value = mock_dialog

        mock_card = MagicMock()
        mock_card.__enter__.return_value = mock_card
        mock_ui.card.return_value = mock_card

        mock_row = MagicMock()
        mock_row.__enter__.return_value = mock_row
        mock_ui.row.return_value = mock_row

        mock_col = MagicMock()
        mock_col.__enter__.return_value = mock_col
        mock_ui.column.return_value = mock_col

        mock_viewport = MagicMock()
        mock_viewport.classes.return_value = mock_viewport
        mock_ui.interactive_image.return_value = mock_viewport

        mock_slider = MagicMock()
        mock_slider.props.return_value = mock_slider
        mock_slider.classes.return_value = mock_slider
        mock_ui.slider.return_value = mock_slider

        button_registry: dict[str, Any] = {}

        def fake_button(*args, **kwargs):
            m = MagicMock()
            m.props.return_value = m
            m.classes.return_value = m
            if args and isinstance(args[0], str):
                button_registry[args[0]] = kwargs.get("on_click")
            return m

        mock_ui.button.side_effect = fake_button

        open_model_alignment_dialog(
            camera_image_b64=b64_img,
            preset=preset,
            digital_names=["digit1", "digit2"],
            analog_names=["analog1"],
        )

        # Inspect initial SVG
        initial_src = mock_viewport.set_source.call_args[0][0]
        assert initial_src.startswith("data:image/svg+xml;base64,")
        b64_svg = initial_src.split(",", 1)[1]
        svg_text = base64.b64decode(b64_svg).decode("utf-8")

        # 1. Verify digital outer and inner boxes + center line
        # digit1 outer box: x="200" y="150" width="50" height="80"
        assert 'x="200"' in svg_text and 'width="50"' in svg_text
        # digit1 inner box: x = 200 + 50*0.2 = 210, width = 50 - 50*0.4 = 30
        assert 'x="210.0"' in svg_text and 'width="30.0"' in svg_text
        # digit1 center line: y1 = 150 + 40 = 190.0
        assert 'y1="190.0"' in svg_text and 'y2="190.0"' in svg_text

        # 2. Verify analog outer box, inscribed circle, and crosshairs
        # analog1 outer box: x="150" y="300" width="60" height="60"
        assert 'x="150"' in svg_text and 'width="60"' in svg_text
        # analog1 circle rx="30.0" ry="30.0"
        assert 'rx="30.0"' in svg_text and 'ry="30.0"' in svg_text
        # analog1 crosshairs center at acx = 180.0, acy = 330.0
        assert 'x1="180.0"' in svg_text and 'y1="330.0"' in svg_text

        # 3. Test hiding digit1
        assert "digit1" in button_registry
        button_registry["digit1"]()  # toggle digit1 off

        updated_src = mock_viewport.set_source.call_args[0][0]
        updated_svg = base64.b64decode(updated_src.split(",", 1)[1]).decode("utf-8")
        assert "digit1" not in updated_svg
        assert "digit2" in updated_svg
        assert "analog1" in updated_svg

        # 4. Test unhiding digit1
        button_registry["digit1"]()  # toggle digit1 back on
        restored_src = mock_viewport.set_source.call_args[0][0]
        restored_svg = base64.b64decode(restored_src.split(",", 1)[1]).decode("utf-8")
        assert "digit1" in restored_svg

        # 5. Test None (hide all) and All (show all)
        assert "None" in button_registry
        assert "All" in button_registry

        button_registry["None"]()
        none_src = mock_viewport.set_source.call_args[0][0]
        none_svg = base64.b64decode(none_src.split(",", 1)[1]).decode("utf-8")
        assert "digit1" not in none_svg
        assert "digit2" not in none_svg
        assert "analog1" not in none_svg

        button_registry["All"]()
        all_src = mock_viewport.set_source.call_args[0][0]
        all_svg = base64.b64decode(all_src.split(",", 1)[1]).decode("utf-8")
        assert "digit1" in all_svg
        assert "digit2" in all_svg
        assert "analog1" in all_svg


def test_open_model_alignment_dialog_wheel_zoom_and_keyboard_nudge():
    """Verify wheel zoom event handler and keyboard shortcut handler."""
    b64_img = _create_test_image_b64(640, 480)

    preset = MeterTypePreset(
        id="test_meter",
        label="Test Meter",
        description="Test Meter description",
        reference_resolution={"width": 640, "height": 480},
    )

    with patch("gui.dialogs.model_alignment_dialog.ui") as mock_ui:
        mock_dialog = MagicMock()
        mock_dialog.value = True
        mock_dialog.__enter__.return_value = mock_dialog
        mock_dialog.props.return_value = mock_dialog
        mock_ui.dialog.return_value = mock_dialog

        mock_card = MagicMock()
        mock_card.__enter__.return_value = mock_card
        mock_ui.card.return_value = mock_card

        mock_row = MagicMock()
        mock_row.__enter__.return_value = mock_row
        mock_ui.row.return_value = mock_row

        mock_col = MagicMock()
        mock_col.__enter__.return_value = mock_col
        mock_ui.column.return_value = mock_col

        mock_viewport = MagicMock()
        mock_viewport.classes.return_value = mock_viewport
        mock_ui.interactive_image.return_value = mock_viewport

        mock_slider = MagicMock()
        mock_slider.props.return_value = mock_slider
        mock_slider.classes.return_value = mock_slider
        mock_ui.slider.return_value = mock_slider

        mock_btn = MagicMock()
        mock_btn.props.return_value = mock_btn
        mock_btn.classes.return_value = mock_btn
        mock_btn.tooltip.return_value = mock_btn
        mock_ui.button.return_value = mock_btn

        mock_lbl = MagicMock()
        mock_lbl.classes.return_value = mock_lbl
        mock_lbl.tooltip.return_value = mock_lbl
        mock_ui.label.return_value = mock_lbl

        open_model_alignment_dialog(
            camera_image_b64=b64_img,
            preset=preset,
        )

        # 1. Test wheel event listener was attached
        wheel_calls = [
            c
            for c in mock_viewport.on.call_args_list
            if c.args and c.args[0] == "wheel"
        ]
        assert len(wheel_calls) == 1
        wheel_handler = wheel_calls[0].kwargs.get("handler")
        assert wheel_handler is not None

        # Simulate wheel scroll up (zoom in)
        mock_event = MagicMock()
        mock_event.args = {"deltaY": -100, "fracX": 0.5, "fracY": 0.5}
        wheel_handler(mock_event)
        zoom_in_src = mock_viewport.set_source.call_args[0][0]
        assert zoom_in_src.startswith("data:image/svg+xml;base64,")

        # Simulate wheel scroll down (zoom out)
        mock_event.args = {"deltaY": 100, "fracX": 0.5, "fracY": 0.5}
        wheel_handler(mock_event)
        zoom_out_src = mock_viewport.set_source.call_args[0][0]
        assert zoom_out_src.startswith("data:image/svg+xml;base64,")

        # 2. Test keyboard handler
        assert mock_ui.keyboard.called
        key_handler = mock_ui.keyboard.call_args.kwargs.get("on_key")
        assert key_handler is not None

        # Keyboard '+' zoom in
        ke_plus = MagicMock()
        ke_plus.action.keydown = True
        ke_plus.key = "+"
        ke_plus.modifiers.shift = False
        key_handler(ke_plus)

        # Keyboard ArrowRight pan
        ke_arrow = MagicMock()
        ke_arrow.action.keydown = True
        ke_arrow.key = "ArrowRight"
        ke_arrow.modifiers.shift = True
        key_handler(ke_arrow)

        # Keyboard ']' rotate CW
        ke_bracket = MagicMock()
        ke_bracket.action.keydown = True
        ke_bracket.key = "]"
        ke_bracket.modifiers.shift = False
        key_handler(ke_bracket)

        # Keyboard '0' reset view
        ke_zero = MagicMock()
        ke_zero.action.keydown = True
        ke_zero.key = "0"
        ke_zero.modifiers.shift = False
        key_handler(ke_zero)

        # Closed dialog ignores keys
        mock_dialog.value = False
        key_handler(ke_plus)


def test_open_model_alignment_dialog_number_inputs():
    """Verify ui.number inputs are created for scale, pan X/Y, angle, and opacity, and handle input."""
    b64_img = _create_test_image_b64(640, 480)
    preset = MeterTypePreset(
        id="test_meter",
        label="Test Meter",
        description="Test Meter description",
        reference_resolution={"width": 640, "height": 480},
    )

    with patch("gui.dialogs.model_alignment_dialog.ui") as mock_ui:
        mock_dialog = MagicMock()
        mock_dialog.__enter__.return_value = mock_dialog
        mock_ui.dialog.return_value = mock_dialog

        mock_card = MagicMock()
        mock_card.__enter__.return_value = mock_card
        mock_ui.card.return_value = mock_card

        mock_row = MagicMock()
        mock_row.__enter__.return_value = mock_row
        mock_ui.row.return_value = mock_row

        mock_col = MagicMock()
        mock_col.__enter__.return_value = mock_col
        mock_ui.column.return_value = mock_col

        mock_viewport = MagicMock()
        mock_ui.interactive_image.return_value = mock_viewport

        mock_slider = MagicMock()
        mock_slider.props.return_value = mock_slider
        mock_slider.classes.return_value = mock_slider
        mock_ui.slider.return_value = mock_slider

        mock_btn = MagicMock()
        mock_btn.props.return_value = mock_btn
        mock_btn.classes.return_value = mock_btn
        mock_btn.tooltip.return_value = mock_btn
        mock_ui.button.return_value = mock_btn

        number_inputs: list[dict[str, Any]] = []

        def fake_number(*args, **kwargs):
            m = MagicMock()
            m.props.return_value = m
            m.classes.return_value = m
            m.tooltip.return_value = m
            number_inputs.append({"args": args, "kwargs": kwargs, "mock": m})
            return m

        mock_ui.number.side_effect = fake_number

        open_model_alignment_dialog(
            camera_image_b64=b64_img,
            preset=preset,
        )

        # Verify 5 ui.number inputs: scale, pan_x, pan_y, angle, opacity
        assert len(number_inputs) == 5

        # 1. Scale input
        scale_input = number_inputs[0]
        assert scale_input["kwargs"].get("step") == 0.01
        on_scale_change = scale_input["kwargs"].get("on_change")
        assert on_scale_change is not None
        ev = MagicMock(value=1.20)
        on_scale_change(ev)

        # 2. Pan X input
        pan_x_input = number_inputs[1]
        assert pan_x_input["kwargs"].get("step") == 1
        on_pan_x_change = pan_x_input["kwargs"].get("on_change")
        assert on_pan_x_change is not None
        ev = MagicMock(value=35.0)
        on_pan_x_change(ev)

        # 3. Pan Y input
        pan_y_input = number_inputs[2]
        assert pan_y_input["kwargs"].get("step") == 1
        on_pan_y_change = pan_y_input["kwargs"].get("on_change")
        assert on_pan_y_change is not None
        ev = MagicMock(value=-20.0)
        on_pan_y_change(ev)

        # 4. Angle input
        angle_input = number_inputs[3]
        assert angle_input["kwargs"].get("step") == 0.1
        on_angle_change = angle_input["kwargs"].get("on_change")
        assert on_angle_change is not None
        ev = MagicMock(value=3.2)
        on_angle_change(ev)

        # 5. Opacity input
        opacity_input = number_inputs[4]
        assert opacity_input["kwargs"].get("step") == 5
        on_opacity_change = opacity_input["kwargs"].get("on_change")
        assert on_opacity_change is not None
        ev = MagicMock(value=60)
        on_opacity_change(ev)
