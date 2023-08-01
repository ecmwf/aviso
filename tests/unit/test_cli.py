# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from pyaviso import logger, user_config
from pyaviso.cli_aviso import cli, key, listen, notify, value
from pyaviso.engine.engine_factory import EngineType


@pytest.fixture()
def conf() -> user_config.UserConfig:  # this automatically configure the logging
    tests_path = Path(__file__).parent.parent
    c = user_config.UserConfig(conf_path=Path(tests_path / "config.yaml"))
    os.environ["AVISO_CONFIG"] = str(Path(tests_path / "config.yaml"))
    return c


@pytest.fixture(autouse=True)  # this runs before and after every test
def pre_post_test():
    # do nothing before each test
    yield


@pytest.fixture(scope="module", autouse=True)
def clear_environment():
    yield
    try:
        os.environ.pop("AVISO_CONFIG")
    except KeyError:  # ignore
        pass


@pytest.mark.skip
def test_listen(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(cli, ["listen", "examples/echoListener.yaml"])
    # run successfully
    assert result.exit_code == 0


def test_help():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(listen, ["-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1


def test_bad_dates_listen(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(
        listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "--from", "2019-20-01T00:00:00.0Z"]
    )
    assert result.exit_code == 2
    assert result.output.find("Invalid value for '--from': '2019-20-01T00:00:00.0Z'") != -1

    result = runner.invoke(
        listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "--from", "2030-02-01T00:00:00.0Z"]
    )
    assert result.exit_code == -1
    assert result.output.find("from_date must be in the past") != -1

    result = runner.invoke(listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "--to", "2019-02-01T00:00:00.0Z"])
    assert result.exit_code == -1
    assert result.output.find("from_date is required if to_date is defined") != -1

    result = runner.invoke(listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "--to", "2030-02-01T00:00:00.0Z"])
    assert result.exit_code == -1
    assert result.output.find("to_date must be in the past") != -1

    result = runner.invoke(
        listen,
        [
            "tests/unit/fixtures/basic_flight_listener.yaml",
            "--from",
            "2020-02-01T00:00:00.0Z",
            "--to",
            "2010-02-01T00:00:00.0Z",
        ],
    )
    assert result.exit_code == -1
    assert result.output.find("to_date must be later than from_date") != -1


def test_bad_listener_file(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(listen, ["tests/unit/fixtures/no_file.py"])
    # The process stops and return an error
    assert result.exit_code == -1
    assert result.output.find("[Errno 2] No such file or directory") != -1


def test_bad_multiple_argument(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "bad"])
    # The process stops and return an error
    assert result.exit_code == -1
    assert result.output.find("[Errno 2] No such file or directory") != -1


def test_bad_options(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "--bad"])
    # The process stops and return an error
    assert result.exit_code == 2
    assert result.output.find("No such option") != -1


def test_bad_logging(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "-l badLogging.yaml"])
    # The process run successfully using default logs
    assert result.exit_code == -1


def test_bad_config_file(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "-cbadConfig.yaml"])
    assert result.exit_code == -1


@pytest.mark.skip  # we cannot authenticate in this test setup
def test_bad_user(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "-uuser"])
    # The process stop as it cannot connect to the server
    assert result.exit_code == -1
    if conf.notification_engine.type == EngineType.ETCD_REST:
        assert result.output.find("Not able to authenticate") != -1
    if conf.notification_engine.type == EngineType.ETCD_GRPC:
        assert result.output.find("authentication failed") != -1


@pytest.mark.skip  # we cannot authenticate in this test setup, therefore we cannot read key
def test_bad_key(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "-kp"])
    # The process stop as it cannot connect to the server
    assert result.exit_code == -1
    assert result.output.find("Not able to load the key file") != -1


@pytest.mark.skip  # we cannot authenticate in this test setup
def test_bad_password(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(listen, ["tests/unit/fixtures/basic_flight_listener.yaml", "-ktests/unit/fixtures/bad/key"])
    # The process stop as it cannot connect to the server
    assert result.exit_code == -1
    if conf.notification_engine.type == EngineType.ETCD_REST:
        assert result.output.find("Not able to authenticate") != -1
    if conf.notification_engine.type == EngineType.ETCD_GRPC:
        assert result.output.find("authentication failed") != -1


def test_key_missing_params(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(key, ["event=flight,country=Italy,airport=fco,date=20210101"])

    assert result.exit_code == -1
    assert "Wrong parameters: number required" in result.output


def test_key_extra_params(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(key, ["event=flight,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Landed"])

    assert result.exit_code == -1
    assert "Key payload is not allowed" in result.output


def test_key_missing_event(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(key, ["country=Italy,airport=fco,date=20210101,number=AZ203"])

    assert result.exit_code == -1
    assert "Invalid notification, 'event' could not be located" in result.output


def test_key_bad_event(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(key, ["event=flight2,country=Italy,airport=fco,date=20210101,number=AZ203,payload=Landed"])

    assert result.exit_code == -1
    assert "Invalid notification, flight2 could not be located in the schema" in result.output


def test_key_bad_format(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(key, ["event=flight,country:Italy,airport:fco,date:20210101,number=AZ203"])

    assert result.exit_code == -1
    assert "Wrong structure for the notification string, it should be <key_name>=<key_value>,..." in result.output


def test_key_bad_format2(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(key, ["event=flight,country=Italy-airport=fco-date=20210101-number=AZ203"])

    assert result.exit_code == -1
    assert "Wrong structure for the notification string, it should be <key_name>=<key_value>,..." in result.output


def test_key_missing_all_params(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(key, [])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_key_help():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(key, ["-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1


def test_value_bad_format(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(value, ["event=flight,country=Italy,airport:fco,date:20210101,number:AZ203,payload=Landed"])

    assert result.exit_code == -1
    assert "Wrong structure for the notification string, it should be <key_name>=<key_value>,..." in result.output


def test_value_missing_params(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(value, [])

    assert result.exit_code == 2
    assert "Missing argument " in result.output


def test_value_help():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(value, ["-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1


def test_notify_help():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(notify, ["-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1


def test_notify_missing_params(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(notify, [])

    assert result.exit_code == 2
    assert "Missing argument" in result.output
