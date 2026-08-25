from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _setup_config() -> ConfigParser:
    parser = ConfigParser()
    parser.read(ROOT / "setup.cfg", encoding="utf-8")
    return parser


def test_v2_release_metadata_is_canonical():
    config = _setup_config()

    assert config["metadata"]["name"] == "wvab-system"
    assert config["metadata"]["version"] == "2.0.0"
    assert config["options"]["python_requires"] == ">=3.10"
    assert config["metadata"]["long_description"] == "file: README.md"
    assert config["metadata"]["license"] == "MIT"
    assert config["metadata"]["license_files"] == "LICENSE"
    assert (ROOT / "README.md").is_file()
    assert not (ROOT / "Readme.md").exists()


def test_v2_wheel_contains_dispatcher_and_console_entrypoint():
    config = _setup_config()

    modules = {line.strip() for line in config["options"]["py_modules"].splitlines() if line.strip()}
    assert "main" in modules

    entrypoints = config["options.entry_points"]["console_scripts"]
    assert "wvab = main:main" in entrypoints


def test_v2_package_discovery_includes_runtime_namespaces():
    config = _setup_config()

    include = {
        line.strip()
        for line in config["options.packages.find"]["include"].splitlines()
        if line.strip()
    }
    assert {
        "assets*",
        "core*",
        "mapping*",
        "navigation*",
        "perception*",
        "training*",
        "tools*",
    } <= include


def test_fonts_are_explicit_package_data():
    config = _setup_config()

    assert config["options"].getboolean("include_package_data") is False
    assert "fonts/*.ttf" in config["options.package_data"]["assets"]
