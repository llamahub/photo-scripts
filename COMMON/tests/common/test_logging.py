import logging
import pytest
from common.logging import LoggingConfig, get_logger


class DummyConfig:
    log_level = "INFO"
    log_format = "%(levelname)s: %(message)s"
    log_file = None


def test_setup_logging_returns_logger(tmp_path):
    config = DummyConfig()
    log_dir = tmp_path / "logs"
    logger = LoggingConfig.setup_logging(
        config, project_name="testproj", log_dir=log_dir
    )
    assert isinstance(logger, logging.Logger)
    # Should create log file
    log_file = log_dir / "testproj.log"
    logger.info("Test message")
    assert log_file.exists()
    with open(log_file) as f:
        contents = f.read()
    assert "Test message" in contents


def test_get_logger_returns_logger():
    logger = get_logger("some_logger")
    assert isinstance(logger, logging.Logger)


@pytest.mark.parametrize("name", ["foo", "bar", "baz"])
def test_get_logger_names(name):
    logger = get_logger(name)
    assert logger.name == name
