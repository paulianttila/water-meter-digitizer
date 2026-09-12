import os

from configuration import Config, ConfigurationMissing
from data_classes import ImagePosition, MeterConfig, RefImage


def test_config():
    config = Config().load_from_file("config/config.ini")
    cfg_dir = "/config" if os.path.exists("/config") else os.path.abspath("config")

    assert config.log_level == "INFO"
    assert config.config_dir == cfg_dir
    assert config.digital_models_dir == f"{cfg_dir}/neuralnets/digital"
    assert config.analog_models_dir == f"{cfg_dir}/neuralnets/analog"
    assert config.previous_value_file == f"{cfg_dir}/prevalue.ini"

    assert config.image_source.url == f"file://{cfg_dir}/original.jpg"
    assert config.image_source.timeout == 10
    assert config.image_source.min_size == 20000

    assert config.alignment.rotate_angle == 180
    assert config.alignment.post_rotate_angle == 0
    assert config.alignment.ref_images == [
        RefImage(
            name="ref0",
            x=99,
            y=219,
            w=0,
            h=0,
            file_name=f"{cfg_dir}/Ref_ZR_x99_y219.jpg",
        ),
        RefImage(
            name="ref1",
            x=512,
            y=117,
            w=0,
            h=0,
            file_name=f"{cfg_dir}/Ref_m3_x512_y117.jpg",
        ),
        RefImage(
            name="ref2",
            x=301,
            y=386,
            w=0,
            h=0,
            file_name=f"{cfg_dir}/Ref_x0_x301_y386.jpg",
        ),
    ]

    assert config.crop.enabled is False
    assert config.crop.x == 100
    assert config.crop.y == 200
    assert config.crop.w == 300
    assert config.crop.h == 400

    assert config.resize.enabled is False
    assert config.resize.w == 640
    assert config.resize.h == 480

    assert config.image_processing.enabled is False
    assert config.image_processing.contrast == 1.0
    assert config.image_processing.brightness == 1.0
    assert config.image_processing.sharpness == 1.0
    assert config.image_processing.color == 1.0
    assert config.image_processing.grayscale is False
    assert config.image_processing.autocontrast.enabled is False
    assert config.image_processing.autocontrast.cutoff_low == 2.0
    assert config.image_processing.autocontrast.cutoff_high == 45
    assert config.image_processing.autocontrast.ignore is None
    assert config.image_processing.autocontrast_cut_images.enabled is False
    assert config.image_processing.autocontrast_cut_images.cutoff_low == 2.0
    assert config.image_processing.autocontrast_cut_images.cutoff_high == 45
    assert config.image_processing.autocontrast_cut_images.ignore is None
    assert config.image_processing.glare_suppression.enabled is False
    assert config.image_processing.glare_suppression.mode == "clahe"
    assert config.image_processing.glare_suppression.inpaint_threshold == 230
    assert config.image_processing.glare_suppression.inpaint_radius == 3
    assert config.image_processing.glare_suppression.clahe_clip_limit == 2.0
    assert config.image_processing.glare_suppression.clahe_grid_size == 8
    assert config.image_processing.glare_suppression.apply_to_cut_images is False

    assert config.digital_readout.enabled is True
    assert (
        config.digital_readout.model_file
        == f"{cfg_dir}/neuralnets/digital/class100/dig-class100_0168_s2_q.tflite"
    )
    assert config.digital_readout.model == "auto"
    assert config.digital_readout.cut_images == [
        ImagePosition(name="digit1", x=215, y=97, w=42, h=75),
        ImagePosition(name="digit2", x=273, y=97, w=42, h=75),
        ImagePosition(name="digit3", x=332, y=97, w=42, h=75),
        ImagePosition(name="digit4", x=390, y=97, w=42, h=75),
        ImagePosition(name="digit5", x=446, y=97, w=42, h=75),
    ]

    assert config.analog_readout.enabled is True
    assert (
        config.analog_readout.model_file
        == f"{cfg_dir}/neuralnets/analog/continuous/ana-cont_1209_s2.tflite"
    )
    assert config.analog_readout.model == "auto"
    assert config.analog_readout.cut_images == [
        ImagePosition(name="analog1", x=491, y=307, w=115, h=115),
        ImagePosition(name="analog2", x=417, y=395, w=115, h=115),
        ImagePosition(name="analog3", x=303, y=424, w=115, h=115),
        ImagePosition(name="analog4", x=163, y=358, w=115, h=115),
    ]

    assert config.meter_configs == [
        MeterConfig(
            name="digital",
            format="{digit1}{digit2}{digit3}{digit4}{digit5}",
            consistency_enabled=False,
            allow_negative_rates=False,
            max_rate_value=0,
            use_previous_value=False,
            pre_value_from_file_max_age=0,
            use_extended_resolution=False,
        ),
        MeterConfig(
            name="analog",
            format="{analog1}{analog2}{analog3}{analog4}",
            consistency_enabled=False,
            allow_negative_rates=False,
            max_rate_value=0,
            use_previous_value=False,
            pre_value_from_file_max_age=0,
            use_extended_resolution=True,
        ),
        MeterConfig(
            name="total",
            format="{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}"
            "{analog3}{analog4}",
            consistency_enabled=True,
            allow_negative_rates=False,
            max_rate_value=0.2,
            use_previous_value=True,
            pre_value_from_file_max_age=0,
            use_extended_resolution=True,
        ),
    ]

    assert config.poller.enabled is False
    assert config.poller.interval_seconds == 300
    assert config.poller.run_on_startup is True
    assert config.poller.save_images is False
    assert config.poller.retry_interval_seconds == 30

    assert config.mqtt.enabled is True
    assert config.mqtt.broker == "localhost"
    assert config.mqtt.port == 1883
    assert config.mqtt.topic_prefix == "watermeter"
    assert config.mqtt.keepalive == 60
    assert config.mqtt.tls is False
    assert config.mqtt.retain is True
    assert config.mqtt.homeassistant_discovery is True
    assert config.mqtt.discovery_prefix == "homeassistant"
    assert config.mqtt.device_name == "Water Meter Digitizer"
    assert config.mqtt.device_id == "water_meter_digitizer"

    assert config.zero_flow_monitor.enabled is False
    assert config.zero_flow_monitor.meter_name == "total"
    assert config.zero_flow_monitor.continuous_flow_hours == 2.0
    assert config.zero_flow_monitor.min_leak_volume == 0.010
    assert config.zero_flow_monitor.flow_threshold == 0.001
    assert config.zero_flow_monitor.resolve_debounce_count == 2
    assert config.zero_flow_monitor.max_history_events == 50


def test_config_file_missing():
    config = Config()
    try:
        config.load_from_file("config/missing.ini")
    except ConfigurationMissing as e:
        assert str(e) == "Configuration file 'config/missing.ini' not found"
    else:
        raise AssertionError()


def test_save():
    TEMPFILENAME = "temp-file-for-unit-test.ini"
    try:
        config = Config().load_from_file("tests/unit/resource/config-for-save-test.ini")
        config.save_to_file(TEMPFILENAME)
        config2 = Config().load_from_file(TEMPFILENAME)
        assert config == config2
    finally:
        import os

        if os.path.exists(TEMPFILENAME):
            os.remove(TEMPFILENAME)


def test_config_save_preserves_title_case():
    config = Config().load_from_file("tests/unit/resource/config-for-save-test.ini")
    saved_str = config.save_to_string()

    # Ensure sections and keys are serialized with TitleCase/PascalCase
    assert "LogLevel=" in saved_str
    assert "ConfigDir=" in saved_str
    assert "DigitalModelsDir=" in saved_str
    assert "AnalogModelsDir=" in saved_str
    assert "PreviousValueFile=" in saved_str
    assert "PostRotationAngle=" in saved_str
    assert "RotationAngle=" in saved_str
    assert "AutoContrastCutoffLow=" in saved_str
    assert "AutoContrastCutoffHigh=" in saved_str
    assert "UsePreviousValue=" in saved_str
    assert "PreValueFromFileMaxAge=" in saved_str
    assert "HomeAssistantDiscovery=" in saved_str
    assert "DiscoveryPrefix=" in saved_str
    assert "ContinuousFlowHours=" in saved_str
    assert "MinLeakVolume=" in saved_str
    assert "ResolveDebounceCount=" in saved_str


def test_config_save_uses_variable_interpolation():
    config = Config().load_from_file("config/config.ini")
    saved_str = config.save_to_string()

    # Verify interpolation variables are used in saved output
    assert "DigitalModelsDir=${ConfigDir}/neuralnets/digital" in saved_str
    assert "AnalogModelsDir=${ConfigDir}/neuralnets/analog" in saved_str
    assert "PreviousValueFile=${ConfigDir}/prevalue.ini" in saved_str
    assert "URL=file://${ConfigDir}/original.jpg" in saved_str
    assert "Image=${ConfigDir}/Ref_ZR_x99_y219.jpg" in saved_str
    assert (
        "ModelFile=${DigitalModelsDir}/class100/dig-class100_0168_s2_q.tflite"
        in saved_str
    )
    assert (
        "ModelFile=${AnalogModelsDir}/continuous/ana-cont_1209_s2.tflite" in saved_str
    )
    assert "DBUrl=sqlite:///${DataDir}/history.db" in saved_str
    assert "StorageDir=${DataDir}/snapshots" in saved_str

    # Verify round-trip parsing expands variables seamlessly
    reloaded = Config().load_from_string(saved_str)
    assert reloaded.digital_models_dir == config.digital_models_dir
    assert reloaded.analog_models_dir == config.analog_models_dir
    assert reloaded.previous_value_file == config.previous_value_file
    assert reloaded.image_source.url == config.image_source.url
    assert (
        reloaded.alignment.ref_images[0].file_name
        == config.alignment.ref_images[0].file_name
    )
    assert reloaded.digital_readout.model_file == config.digital_readout.model_file
    assert reloaded.analog_readout.model_file == config.analog_readout.model_file
    assert reloaded.history.db_url == config.history.db_url
    assert reloaded.snapshots.storage_dir == config.snapshots.storage_dir


def test_config_save_preserves_external_paths():
    config = Config().load_from_file("config/config.ini")
    # Point some paths to custom / external locations
    config.image_source.url = "http://192.168.1.100/cam.jpg"
    config.digital_readout.model_file = "/opt/models/my_custom_digit_model.tflite"
    config.history.db_url = "sqlite:///:memory:"
    config.snapshots.storage_dir = "/mnt/nas/snapshots"

    saved_str = config.save_to_string()
    assert "URL=http://192.168.1.100/cam.jpg" in saved_str
    assert "ModelFile=/opt/models/my_custom_digit_model.tflite" in saved_str
    assert "DBUrl=sqlite:///:memory:" in saved_str
    assert "StorageDir=/mnt/nas/snapshots" in saved_str

    reloaded = Config().load_from_string(saved_str)
    assert reloaded.image_source.url == "http://192.168.1.100/cam.jpg"
    assert (
        reloaded.digital_readout.model_file
        == "/opt/models/my_custom_digit_model.tflite"
    )
    assert reloaded.history.db_url == "sqlite:///:memory:"
    assert reloaded.snapshots.storage_dir == "/mnt/nas/snapshots"


def test_config_save_with_nested_data_dir():
    config = Config().load_from_file("config/config.ini")
    # Simulate setup where data_dir is inside config_dir
    config.config_dir = "/Users/pali/test_config3"
    config.data_dir = "/Users/pali/test_config3/data"
    config.digital_models_dir = "/Users/pali/test_config3/neuralnets/digital"
    config.analog_models_dir = "/Users/pali/test_config3/neuralnets/analog"
    config.previous_value_file = "/Users/pali/test_config3/prevalue.ini"
    config.digital_readout.model_file = (
        "/Users/pali/test_config3/neuralnets/digital/dig-class11_1701_s2.tflite"
    )
    config.history.db_url = "sqlite:////Users/pali/test_config3/data/history.db"
    config.snapshots.storage_dir = "/Users/pali/test_config3/data/snapshots"

    saved_str = config.save_to_string()
    assert "ConfigDir=/Users/pali/test_config3" in saved_str
    assert "DataDir=${ConfigDir}/data" in saved_str
    assert "DigitalModelsDir=${ConfigDir}/neuralnets/digital" in saved_str
    assert "AnalogModelsDir=${ConfigDir}/neuralnets/analog" in saved_str
    assert "PreviousValueFile=${ConfigDir}/prevalue.ini" in saved_str
    assert "ModelFile=${DigitalModelsDir}/dig-class11_1701_s2.tflite" in saved_str
    assert "DBUrl=sqlite:///${DataDir}/history.db" in saved_str
    assert "StorageDir=${DataDir}/snapshots" in saved_str

    reloaded = Config().load_from_string(saved_str)
    assert reloaded.config_dir == "/Users/pali/test_config3"
    assert reloaded.data_dir == "/Users/pali/test_config3/data"
    assert reloaded.digital_models_dir == "/Users/pali/test_config3/neuralnets/digital"
    assert (
        reloaded.digital_readout.model_file
        == "/Users/pali/test_config3/neuralnets/digital/dig-class11_1701_s2.tflite"
    )
    assert (
        reloaded.history.db_url == "sqlite:////Users/pali/test_config3/data/history.db"
    )
    assert reloaded.snapshots.storage_dir == "/Users/pali/test_config3/data/snapshots"


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("METER_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("METER_CONFIG_DIR", "/custom/config")
    config = Config()
    assert config.log_level == "DEBUG"
    assert config.config_dir == "/custom/config"


def test_config_json_schema():
    schema = Config.model_json_schema()
    assert "properties" in schema
    assert "log_level" in schema["properties"]
    assert "image_source" in schema["properties"]


def test_ensure_config_initialized_already_exists():
    from configuration import ensure_config_initialized

    assert ensure_config_initialized("config/config.ini") is True


def test_ensure_config_initialized_populates_from_seed(tmp_path):
    from configuration import ensure_config_initialized

    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / "config.ini").write_text("[DEFAULT]\nLogLevel=DEBUG\n")
    (seed_dir / "test.txt").write_text("hello")

    target_config = tmp_path / "target" / "config.ini"
    assert not target_config.exists()

    result = ensure_config_initialized(str(target_config), seed_dir=str(seed_dir))
    assert result is True
    assert target_config.exists()
    assert (tmp_path / "target" / "test.txt").exists()
    assert (tmp_path / "target" / "test.txt").read_text() == "hello"


def test_ensure_config_initialized_missing_seed(tmp_path):
    from configuration import ensure_config_initialized

    missing_seed = tmp_path / "nonexistent"
    target_config = tmp_path / "target" / "config.ini"

    result = ensure_config_initialized(str(target_config), seed_dir=str(missing_seed))
    assert result is False
    assert not target_config.exists()


def test_init_config_logging_level(monkeypatch, tmp_path):
    import logging

    import main

    test_ini = tmp_path / "config.ini"
    test_ini.write_text("[DEFAULT]\nLogLevel=WARNING\n")

    monkeypatch.setattr(main, "config_file", str(test_ini))
    main.init_config()

    assert logging.getLogger().level == logging.WARNING
    assert main.logger.level == logging.WARNING

    # Reset back to INFO for subsequent tests
    test_ini.write_text("[DEFAULT]\nLogLevel=INFO\n")
    main.init_config()
    assert logging.getLogger().level == logging.INFO
