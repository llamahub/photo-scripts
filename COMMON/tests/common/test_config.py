import os
from common.config import BaseConfig, load_config, ProjectConfig


def test_base_config_defaults():
    config = BaseConfig()
    assert config.environment == "dev"
    assert config.debug is True
    assert config.log_level == "INFO"
    assert config.api_host == "localhost"
    assert config.api_port == 8000
    assert config.api_debug is True
    assert config.database_echo is False


def test_base_config_env_override(tmp_path, monkeypatch):
    # Create a .env file
    env_file = tmp_path / ".env"
    env_file.write_text("LOG_LEVEL=WARNING\nAPI_PORT=9000\nDEBUG=False\n")
    monkeypatch.chdir(tmp_path)
    config = load_config(project_path=tmp_path)
    assert config.log_level == "WARNING"
    assert config.api_port == 9000
    assert config.debug is False


def test_base_config_env_specific(tmp_path, monkeypatch):
    # Create a .env.test file
    env_file = tmp_path / ".env.test"
    env_file.write_text("API_HOST=127.0.0.1\nAPI_DEBUG=False\n")
    monkeypatch.chdir(tmp_path)
    config = load_config(project_path=tmp_path, env="test")
    assert config.api_host == "127.0.0.1"
    assert config.api_debug is False


def test_project_config_custom_settings():
    config = ProjectConfig(project_name="myproj", custom_settings={"foo": 123})
    assert config.project_name == "myproj"
    assert config.project_version == "1.0.0"
    assert config.custom_settings["foo"] == 123


def test_env_variable_set(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    load_config(project_path=tmp_path, env="prod")
    assert os.environ["ENVIRONMENT"] == "prod"
