# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
from filecmp import dircmp
from shutil import rmtree

import pytest
from click.testing import CliRunner

from pyaviso import logger, user_config
from pyaviso.cli_aviso_config import cli
from pyaviso.engine.engine_factory import EngineType

test_svc = "test_svc/v1"
config_folder_to_push1 = "tests/system/fixtures/config_test_push1"
config_folder_to_push2 = "tests/system/fixtures/config_test_push2"
config_folder_to_pull = "tests/system/fixtures/config_test_pull1"


def create_conf() -> user_config.UserConfig:  # this automatically configure the logging
    c = user_config.UserConfig(conf_path="tests/config.yaml")
    return c


# setting up multiple configurations for running the tests multiple times
c1 = create_conf()
c1.configuration_engine.type = EngineType.ETCD_REST
c2 = create_conf()
c2.configuration_engine.type = EngineType.ETCD_GRPC
confs = [c1, c2]


@pytest.mark.parametrize("conf", confs)
@pytest.fixture(autouse=True)  # this runs before and after every test
def pre_post_test(conf):
    # set environment
    os.environ["AVISO_CONFIG"] = "tests/config.yaml"
    yield


@pytest.fixture(scope="module", autouse=True)
def clear_environment():
    yield
    try:
        os.environ.pop("AVISO_CONFIG")
    except KeyError:  # ignore
        pass


@pytest.fixture(autouse=True)
def remove_test_svc():
    yield
    result = CliRunner().invoke(cli, ["remove", test_svc, "-f"])
    assert result.exit_code == 0


def _print_diff_files(dcmp) -> str:
    result = ""
    for name in dcmp.diff_files:
        result += "diff_file %s found in %s and %s" % (name, dcmp.left, dcmp.right)
    for f in dcmp.funny_files:
        result += f"Something funny {f}"
    for f in dcmp.left_only:
        result += f"Something left only {f}"
    for f in dcmp.right_only:
        result += f"Something right only {f}"
    for sub_dcmp in dcmp.subdirs.values():
        result += _print_diff_files(sub_dcmp)
    return result


@pytest.mark.parametrize("conf", confs)
def test_help(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(cli, ["-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1

    result = runner.invoke(cli, ["push", "-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1

    result = runner.invoke(cli, ["pull", "-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1

    result = runner.invoke(cli, ["remove", "-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1

    result = runner.invoke(cli, ["revert", "-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1

    result = runner.invoke(cli, ["status", "-h"])
    # run successfully
    assert result.exit_code == 0
    # display the options
    assert result.output.find("Options:") != -1


@pytest.mark.parametrize("conf", confs)
def test_push_and_pull(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    # run successfully
    assert result.exit_code == 0
    # display the operation completed
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # delete pull directory
    if os.path.exists(config_folder_to_pull):
        rmtree(config_folder_to_pull)
        assert not os.path.exists(config_folder_to_pull)

    # pull to retrieve the files on a new directory
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    # run successfully
    assert result.exit_code == 0
    # display the operation completed
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check the files are there and are identical
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push1, config_folder_to_pull)
    assert _print_diff_files(dcmp) == ""


@pytest.mark.parametrize("conf", confs)
def test_push_and_pull_workflow1(conf):
    """
    First push larger set, then a small set with NO delete -> pulled folder is like the union of the larger and smaller
    set
    :param conf:
    :return:
    """
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    # First push larger set
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # Push smaller set
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push2, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # delete pull directory
    if os.path.exists(config_folder_to_pull):
        rmtree(config_folder_to_pull)
        assert not os.path.exists(config_folder_to_pull)

    # pull to retrieve the files on a new directory
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check that is like the larger set
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push1, config_folder_to_pull)
    assert (
        _print_diff_files(dcmp) == "diff_file config1.json found in tests/system/fixtures/config_test_push1 "
        "and tests/system/fixtures/config_test_pull1diff_file config2.json found "
        "in tests/system/fixtures/config_test_push1 and tests/system/"
        "fixtures/config_test_pull1"
    )


@pytest.mark.parametrize("conf", confs)
def test_push_and_pull_workflow2(conf):
    """
    First push larger set, then a small set with delete -> pulled folder is like the smaller set
    :param conf:
    :return:
    """
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    # First push larger set
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # Push smaller set
    result = runner.invoke(
        cli, ["push", test_svc, "-D", config_folder_to_push2, "-m", "test configuration", "--delete"]
    )
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # delete pull directory
    if os.path.exists(config_folder_to_pull):
        rmtree(config_folder_to_pull)
        assert not os.path.exists(config_folder_to_pull)

    # pull to retrieve the files on a new directory
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check that is like the smaller set
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push2, config_folder_to_pull)
    assert _print_diff_files(dcmp) == ""


@pytest.mark.parametrize("conf", confs)
def test_push_and_pull_workflow3(conf):
    """
    First push larger set and pull, then push small set with delete and pull with NO delete -> pulled folder
    is like the union of larger and smaller set
    :param conf:
    :return:
    """
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    # First push larger set
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # delete pull directory
    if os.path.exists(config_folder_to_pull):
        rmtree(config_folder_to_pull)
        assert not os.path.exists(config_folder_to_pull)

    # pull to retrieve the files on a new directory
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check that is like the larger set
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push1, config_folder_to_pull)
    assert _print_diff_files(dcmp) == ""

    # Push smaller set
    result = runner.invoke(
        cli, ["push", test_svc, "-D", config_folder_to_push2, "-m", "test configuration", "--delete"]
    )
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # pull to retrieve the files on the same directory
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check that is like the larger set
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push1, config_folder_to_pull)
    assert (
        _print_diff_files(dcmp) == "diff_file config1.json found in tests/system/fixtures/config_test_push1 "
        "and tests/system/fixtures/config_test_pull1diff_file config2.json found "
        "in tests/system/fixtures/config_test_push1 and tests/system/"
        "fixtures/config_test_pull1"
    )


@pytest.mark.parametrize("conf", confs)
def test_push_and_pull_workflow4(conf):
    """
    First push larger set and pull, then push small set with delete and pull with delete -> pulled folder
    is like the smaller set
    :param conf:
    :return:
    """
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    # First push larger set
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # delete pull directory
    if os.path.exists(config_folder_to_pull):
        rmtree(config_folder_to_pull)
        assert not os.path.exists(config_folder_to_pull)

    # pull to retrieve the files on a new directory
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check that is like the larger set
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push1, config_folder_to_pull)
    assert _print_diff_files(dcmp) == ""

    # Push smaller set
    result = runner.invoke(
        cli, ["push", test_svc, "-D", config_folder_to_push2, "-m", "test configuration", "--delete"]
    )
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # pull to retrieve the files on the same directory
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull, "--delete"])
    assert result.exit_code == 0
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check that is like the smaller set
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push2, config_folder_to_pull)
    assert _print_diff_files(dcmp) == ""


@pytest.mark.parametrize("conf", confs)
def test_remove(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    # First push
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # remove with NO doit -> nothing is removed
    result = runner.invoke(cli, ["remove", test_svc])
    assert result.exit_code == 0
    assert result.output.find("remove --doit to delete these files") != -1

    # delete pull directory
    if os.path.exists(config_folder_to_pull):
        rmtree(config_folder_to_pull)
        assert not os.path.exists(config_folder_to_pull)

    # pull to retrieve the files on a new directory
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check that is like the larger set
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push1, config_folder_to_pull)
    assert _print_diff_files(dcmp) == ""


@pytest.mark.parametrize("conf", confs)
def test_remove_doit(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    # First push
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # remove with doit -> files are removed
    result = runner.invoke(cli, ["remove", test_svc, "--doit"])
    assert result.exit_code == 0
    assert result.output.find(f"Remove operation for service {test_svc} successfully executed") != -1

    # delete pull directory
    if os.path.exists(config_folder_to_pull):
        rmtree(config_folder_to_pull)
        assert not os.path.exists(config_folder_to_pull)

    # pull to retrieve the files on a new directory -> no file found
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"No files found for service {test_svc}") != -1


@pytest.mark.parametrize("conf", confs)
def test_revert(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    # First push
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # now change a file
    content = ""
    with open(config_folder_to_push1 + "/config1.json", "r") as f:
        content = f.read()
    content += "xxx"
    with open(config_folder_to_push1 + "/config1.json", "w") as f:
        f.write(content)

    # Push again
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # pull to retrieve the files
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check that is like the current dir
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push1, config_folder_to_pull)
    assert _print_diff_files(dcmp) == ""

    # revert to the previous version
    result = runner.invoke(cli, ["revert", test_svc])
    assert result.exit_code == 0
    assert result.output.find(f"Revert operation for service {test_svc} successfully executed") != -1

    # pull to retrieve the files
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"Pull operation for service {test_svc} successfully executed") != -1
    # check that is like not like the current dir
    assert os.path.exists(config_folder_to_pull)
    dcmp = dircmp(config_folder_to_push1, config_folder_to_pull)
    assert _print_diff_files(dcmp) != ""

    # revert file to before the change
    content = content.replace("xxx", "")
    with open(config_folder_to_push1 + "/config1.json", "w") as f:
        f.write(content)

    # check again is like the current dir
    dcmp = dircmp(config_folder_to_push1, config_folder_to_pull)
    assert _print_diff_files(dcmp) == ""


@pytest.mark.parametrize("conf", confs)
def test_status(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    # First push
    result = runner.invoke(cli, ["push", test_svc, "-D", config_folder_to_push1, "-m", "test configuration"])
    assert result.exit_code == 0
    assert result.output.find(f"Push operation for service {test_svc} successfully executed") != -1

    # Check we have a status associated to the service
    result = runner.invoke(cli, ["status", test_svc])
    assert result.exit_code == 0
    assert result.output.find('"message": "test configuration"')


@pytest.mark.parametrize("conf", confs)
def test_pull_nothing(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(cli, ["pull", test_svc, "-D", config_folder_to_pull])
    assert result.exit_code == 0
    assert result.output.find(f"No files found for service {test_svc}") != -1


@pytest.mark.parametrize("conf", confs)
def test_remove_nothing(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(cli, ["remove", test_svc, "-f"])
    assert result.exit_code == 0
    assert result.output.find(f"No files found for service {test_svc}") != -1


@pytest.mark.parametrize("conf", confs)
def test_revert_nothing(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(cli, ["revert", test_svc])
    assert result.exit_code == 0
    assert result.output.find(f"No files found for service {test_svc}") != -1


@pytest.mark.parametrize("conf", confs)
def test_status_nothing(conf):
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])
    runner = CliRunner()
    result = runner.invoke(cli, ["status", test_svc])
    assert result.exit_code == 0
    assert result.output.find(f"No service {test_svc} found") != -1
