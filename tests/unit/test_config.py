from src.lib.Config import Config


def test_config():
    config = Config()
    config.parseConfig("config/config.ini")

    assert config.httpImageUrl == "file:///config/original.jpg"
    assert config.httpTimeoutLoadImage == 10
    assert config.httpImageMinSize == 20000
    assert config.httpImageLogFolder == "/log/source_image/"
    assert config.httpLogOnlyFalsePictures is True
