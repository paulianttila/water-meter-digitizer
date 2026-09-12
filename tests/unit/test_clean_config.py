from unittest.mock import MagicMock

from PIL import Image

import utils.image
from configuration import Config
from gui.step_adjust import AdjustStep


def test_create_clean_default_properties():
    clean_cfg = Config.create_clean_default(
        config_dir="/custom_config", data_dir="/custom_data"
    )

    # Paths and general properties
    assert clean_cfg.config_dir == "/custom_config"
    assert clean_cfg.data_dir == "/custom_data"
    assert clean_cfg.digital_models_dir == "/custom_config/neuralnets/digital"
    assert clean_cfg.analog_models_dir == "/custom_config/neuralnets/analog"
    assert clean_cfg.previous_value_file == "/custom_config/prevalue.ini"
    assert clean_cfg.min_confidence_threshold == 60.0

    # Image source
    assert clean_cfg.image_source.url == ""
    assert clean_cfg.image_source.timeout == 30
    assert clean_cfg.image_source.min_size == 10000

    # Crop & Resize
    assert clean_cfg.crop.enabled is False
    assert clean_cfg.crop.x == 0
    assert clean_cfg.resize.enabled is False

    # Image Processing
    assert clean_cfg.image_processing.enabled is False
    assert clean_cfg.image_processing.contrast == 1.0
    assert clean_cfg.image_processing.brightness == 1.0
    assert clean_cfg.image_processing.autocontrast.enabled is False
    assert clean_cfg.image_processing.glare_suppression.enabled is False

    # Alignment & references
    assert clean_cfg.alignment.rotate_angle == 0.0
    assert clean_cfg.alignment.post_rotate_angle == 0.0
    assert len(clean_cfg.alignment.ref_images) == 0

    # Digital & Analog Readout
    assert clean_cfg.digital_readout.enabled is False
    assert len(clean_cfg.digital_readout.cut_images) == 0
    assert "class100" in clean_cfg.digital_readout.model_file
    assert clean_cfg.analog_readout.enabled is False
    assert len(clean_cfg.analog_readout.cut_images) == 0
    assert "continuous" in clean_cfg.analog_readout.model_file

    # Meters
    assert len(clean_cfg.meter_configs) == 1
    assert clean_cfg.meter_configs[0].name == "total"
    assert clean_cfg.meter_configs[0].format == ""

    # Services
    assert clean_cfg.poller.enabled is False
    assert clean_cfg.mqtt.enabled is False
    assert clean_cfg.history.enabled is True
    assert clean_cfg.snapshots.enabled is True
    assert clean_cfg.zero_flow_monitor.enabled is False


def test_clean_config_save_and_reload():
    clean_cfg = Config.create_clean_default()
    ini_str = clean_cfg.save_to_string()

    reloaded = Config()
    reloaded.load_from_string(ini_str)

    assert reloaded.image_source.url == ""
    assert len(reloaded.alignment.ref_images) == 0
    assert len(reloaded.digital_readout.cut_images) == 0
    assert len(reloaded.analog_readout.cut_images) == 0
    assert len(reloaded.meter_configs) == 1
    assert reloaded.meter_configs[0].name == "total"


def test_adjust_step_after_clean_config_pipeline():
    # Generate a dummy test image base64
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    img_b64 = utils.image.convert_image_base64str(img)

    main_images = []
    comp_images = []

    def set_main_img(b64: str) -> None:
        main_images.append(b64)

    def set_comp_img(b64: str) -> None:
        comp_images.append(b64)

    adjust_step = AdjustStep(
        name="Adjust image",
        set_image_callback=set_main_img,
        set_comparison_callback=set_comp_img,
    )

    # Initialize mock UI controls
    adjust_step.live_preview = MagicMock(value=True)
    adjust_step.compare_mode = MagicMock(value="Single")
    adjust_step.rotate_enabled = MagicMock(value=False)
    adjust_step.rotate_angle = MagicMock(value=0)
    adjust_step.crop_enabled = MagicMock(value=False)
    adjust_step.crop_x = MagicMock(value=0)
    adjust_step.crop_y = MagicMock(value=0)
    adjust_step.crop_w = MagicMock(value=0)
    adjust_step.crop_h = MagicMock(value=0)
    adjust_step.resize_enabled = MagicMock(value=False)
    adjust_step.resize_w = MagicMock(value=0)
    adjust_step.resize_h = MagicMock(value=0)
    adjust_step.adjust_enabled = MagicMock(value=False)
    adjust_step.adjust_contrast = MagicMock(value=1.0)
    adjust_step.adjust_brightness = MagicMock(value=1.0)
    adjust_step.adjust_sharpness = MagicMock(value=1.0)
    adjust_step.adjust_color = MagicMock(value=1.0)
    adjust_step.grayscale_enabled = MagicMock(value=False)
    adjust_step.autocontrast_enabled = MagicMock(value=False)
    adjust_step.autocontrast_cutoff_low = MagicMock(value=2.0)
    adjust_step.autocontrast_cutoff_high = MagicMock(value=45.0)
    adjust_step.autocontrast_cut_images_enabled = MagicMock(value=False)
    adjust_step.autocontrast_cut_images_cutoff_low = MagicMock(value=2.0)
    adjust_step.autocontrast_cut_images_cutoff_high = MagicMock(value=45.0)
    adjust_step.glare_enabled = MagicMock(value=False)
    adjust_step.glare_mode = MagicMock(value="clahe")
    adjust_step.glare_inpaint_threshold = MagicMock(value=230)
    adjust_step.glare_inpaint_radius = MagicMock(value=3)
    adjust_step.glare_clahe_clip_limit = MagicMock(value=2.0)
    adjust_step.glare_clahe_grid_size = MagicMock(value=8)
    adjust_step.glare_apply_to_cut_images = MagicMock(value=False)

    clean_cfg = Config.create_clean_default()
    adjust_step.load_from_config(clean_cfg)

    # Initial state should be clean (ref_images empty)
    assert len(adjust_step.ref_images) == 0

    # Simulate advancing to Adjust step with rotated image from pipeline
    adjust_step.update_image(img_b64)

    # Preview canvas should have updated image
    assert adjust_step.org_image == img_b64
    assert adjust_step.image != ""
    assert len(main_images) > 0
    # Comparison image should be cleared in single view mode
    assert comp_images[-1] == ""

    # Test Side-by-Side compare mode
    adjust_step.compare_mode.value = "Side-by-Side"
    adjust_step._update_preview_canvas()

    # In side-by-side mode, top canvas gets original, bottom gets adjusted
    assert main_images[-1] == img_b64
    assert comp_images[-1] != ""


def test_save_refs_keyword_arguments(tmp_path):
    from gui.step_draw_rois_base import Roi

    # Verify ImagePosition instantiation with keyword arguments works
    roi = Roi(name="Ref1", x=10, y=10, w=20, h=20)
    pos = utils.image.ImagePosition(name=roi.name, x=roi.x, y=roi.y, w=roi.w, h=roi.h)
    assert pos.name == "Ref1"
    assert pos.x == 10

    # Cut and save image
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    cut = utils.image.cut_image(img, pos)
    out_file = str(tmp_path / f"ref_{roi.name}_x{roi.x}_y{roi.y}.jpg")
    utils.image.save_image(cut, out_file)
    assert (tmp_path / f"ref_{roi.name}_x{roi.x}_y{roi.y}.jpg").exists()


def test_draw_refs_step_warning_logic():
    from data_classes import RefImage
    from gui.step_draw_refs import DrawRefsStep

    step = DrawRefsStep(
        name="draw_refs",
        name_template="Ref",
        set_image_callback=MagicMock(),
        set_rois_to_svg_func=MagicMock(),
        show_temp_draw_in_svg_func=MagicMock(),
    )
    # Mock warning container
    mock_container = MagicMock()
    step.warning_container = mock_container

    # 0 reference points
    step.load_from_config([])
    mock_container.clear.assert_called()

    # 1 reference point
    step.load_from_config(
        [RefImage(name="Ref1", x=10, y=10, w=20, h=20, file_name="ref1.jpg")]
    )
    assert len(step.rois) == 1

    # 3 reference points
    step.load_from_config(
        [
            RefImage(
                name=f"Ref{i}", x=10 * i, y=10 * i, w=20, h=20, file_name=f"ref{i}.jpg"
            )
            for i in range(1, 4)
        ]
    )
    assert len(step.rois) == 3
