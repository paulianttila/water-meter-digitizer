from src.lib.Config import Config


def test_config():
    config = Config()
    config.load_config("config/config.ini")

    assert config.http_image_url == "file:///config/original.jpg"
    assert config.http_load_image_timeout == 10
    assert config.http_image_min_size == 20000
    assert config.http_image_log_dir == "/log/source_image/"
    assert config.http_log_only_false_pictures is True
