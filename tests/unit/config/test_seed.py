"""Unit tests for config seed utilities and profile onboarding."""

from pathlib import Path

from config.seed import (
    copy_default_config,
    find_seed_dir,
    init_profile_for_wizard,
)


def test_find_seed_dir_with_env(monkeypatch, tmp_path):
    custom_seed = tmp_path / "custom_seed"
    custom_seed.mkdir()
    (custom_seed / "config.ini").write_text("[DEFAULT]\n")

    monkeypatch.setenv("DEFAULT_CONFIG_DIR", str(custom_seed))
    assert find_seed_dir() == str(custom_seed)


def test_find_seed_dir_repo_root():
    seed = find_seed_dir()
    assert seed is not None
    assert (Path(seed) / "config.ini").is_file()


def test_copy_default_config(tmp_path):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / "config.ini").write_text(
        "[DEFAULT]\nConfigDir = /config\n\n[ImageSource]\nURL = http://cam\n"
    )
    (seed_dir / "Ref_0.jpg").write_text("fake_ref")
    (seed_dir / "local").mkdir()
    (seed_dir / "local" / "dummy.txt").write_text("should_not_copy")
    (seed_dir / ".DS_Store").write_text("junk")

    target_profile = tmp_path / "profiles" / "meter1"
    target_config = target_profile / "config.ini"

    success = copy_default_config(str(target_config), seed_dir=str(seed_dir))
    assert success is True
    assert target_config.is_file()
    assert (target_profile / "Ref_0.jpg").is_file()
    # Check exclusions
    assert not (target_profile / "local").exists()
    assert not (target_profile / ".DS_Store").exists()

    # Check ConfigDir adjustment
    content = target_config.read_text()
    assert "ConfigDir" in content
    assert "/config" not in content


def test_copy_default_config_preserves_demo_url(tmp_path):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / "config.ini").write_text(
        "[DEFAULT]\nConfigDir = /config\n\n[ImageSource]\nURL = file://${ConfigDir}/original.jpg\n"
    )

    target_profile = tmp_path / "profiles" / "meter2"
    target_profile.mkdir(parents=True)
    (target_profile / "meter_photo.png").write_text("fake_png")

    target_config = target_profile / "config.ini"
    success = copy_default_config(str(target_config), seed_dir=str(seed_dir))
    assert success is True

    content = target_config.read_text()
    assert "file://${ConfigDir}/original.jpg" in content
    assert "meter_photo.png" not in content


def test_init_profile_for_wizard(tmp_path):
    target_profile = tmp_path / "profiles" / "axioma_w1"
    target_profile.mkdir(parents=True)
    (target_profile / "axioma_w1.png").write_text("photo")

    target_config = target_profile / "config.ini"
    success = init_profile_for_wizard(str(target_config))
    assert success is True
    assert target_config.is_file()

    content = target_config.read_text()
    # Picture check removed: should not automatically bind to local picture
    assert "file://${ConfigDir}/axioma_w1.png" not in content
    assert str(target_profile) in content or "axioma_w1" in content
    assert (target_profile / "meter_types").is_dir()


def test_copy_default_config_missing_seed(tmp_path):
    target_config = tmp_path / "target" / "config.ini"
    success = copy_default_config(str(target_config), seed_dir=str(tmp_path / "none"))
    assert success is False
    assert not target_config.exists()
