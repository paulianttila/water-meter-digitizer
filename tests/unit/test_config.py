from src.Config import (
    Config,
    ConfigurationMissing,
    ImagePosition,
    MeterConfig,
    RefImages,
)


def test_config():
    config = Config()
    config.load_config("config/config.ini")

    assert config.log_level == "INFO"
    assert config.image_tmp_dir == "/image_tmp"
    assert config.config_dir == "/config"
    assert config.prevoius_value_file == "/config/prevalue.ini"

    assert config.http_image_url == "file:///config/original.jpg"
    assert config.http_load_image_timeout == 10
    assert config.http_image_min_size == 20000
    assert config.http_image_log_dir == "/log/source_image/"
    assert config.http_log_only_false_pictures is True

    assert config.alignment_rotate_angle == 180
    assert config.alignment_ref_images == [
        RefImages(name="ref0", file_name="/config/Ref_ZR_x99_y219.jpg", x=99, y=219),
        RefImages(name="ref1", file_name="/config/Ref_m3_x512_y117.jpg", x=512, y=117),
        RefImages(name="ref2", file_name="/config/Ref_x0_x301_y386.jpg", x=301, y=386),
    ]

    assert config.digital_readout_enabled is True
    assert config.analog_readout_enabled is True

    assert config.cut_digital_digit == [
        ImagePosition(name="digit1", x1=215, y1=97, w=42, h=75),
        ImagePosition(name="digit2", x1=273, y1=97, w=42, h=75),
        ImagePosition(name="digit3", x1=332, y1=97, w=42, h=75),
        ImagePosition(name="digit4", x1=390, y1=97, w=42, h=75),
        ImagePosition(name="digit5", x1=446, y1=97, w=42, h=75),
    ]

    assert config.cut_analog_counter == [
        ImagePosition(name="analog1", x1=491, y1=307, w=115, h=115),
        ImagePosition(name="analog2", x1=417, y1=395, w=115, h=115),
        ImagePosition(name="analog3", x1=303, y1=424, w=115, h=115),
        ImagePosition(name="analog4", x1=163, y1=358, w=115, h=115),
    ]
    assert config.meter_configs == [
        MeterConfig(
            name="digital",
            format="{digit1}{digit2}{digit3}{digit4}{digit5}",
            consistency_enabled=False,
            allow_negative_rates=False,
            max_rate_value=0,
            use_previuos_value=False,
            pre_value_from_file_max_age=0,
            use_extended_resolution=False,
        ),
        MeterConfig(
            name="analog",
            format="{analog1}{analog2}{analog3}{analog4}",
            consistency_enabled=False,
            allow_negative_rates=False,
            max_rate_value=0,
            use_previuos_value=False,
            pre_value_from_file_max_age=0,
            use_extended_resolution=False,
        ),
        MeterConfig(
            name="total",
            format="{digit1}{digit2}{digit3}{digit4}{digit5}.{analog1}{analog2}"
            "{analog3}{analog4}",
            consistency_enabled=True,
            allow_negative_rates=False,
            max_rate_value=0.2,
            use_previuos_value=True,
            pre_value_from_file_max_age=3000,
            use_extended_resolution=True,
        ),
    ]
    assert config.digit_model_file == "/config/neuralnets/dig-class100_0168_s2_q.tflite"
    assert config.digit_model == "auto"
    assert config.digit_do_image_logging is False
    assert config.digit_image_log_dir == ""
    assert config.cut_digital_digit == [
        ImagePosition(name="digit1", x1=215, y1=97, w=42, h=75),
        ImagePosition(name="digit2", x1=273, y1=97, w=42, h=75),
        ImagePosition(name="digit3", x1=332, y1=97, w=42, h=75),
        ImagePosition(name="digit4", x1=390, y1=97, w=42, h=75),
        ImagePosition(name="digit5", x1=446, y1=97, w=42, h=75),
    ]

    assert config.analog_model_file == "/config/neuralnets/ana-cont_1209_s2.tflite"
    assert config.analog_model == "auto"
    assert config.analog_do_image_logging is False
    assert config.analog_image_log_dir == ""
    assert config.cut_analog_counter == [
        ImagePosition(name="analog1", x1=491, y1=307, w=115, h=115),
        ImagePosition(name="analog2", x1=417, y1=395, w=115, h=115),
        ImagePosition(name="analog3", x1=303, y1=424, w=115, h=115),
        ImagePosition(name="analog4", x1=163, y1=358, w=115, h=115),
    ]


def test_config_file_missing():
    config = Config()
    try:
        config.load_config("config/missing.ini")
    except ConfigurationMissing as e:
        assert str(e) == "Configuration file 'config/missing.ini' not found"
    else:
        assert False
