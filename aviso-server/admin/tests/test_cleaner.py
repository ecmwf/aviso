# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import os

import requests
from aviso_admin import config, logger
from aviso_admin.cleaner import Cleaner, DATE_FORMAT
from aviso_admin.utils import encode_to_str_base64


def conf() -> config.Config:  # this automatically configure the logging
    c = config.Config(conf_path="aviso-server/admin/tests/config.yaml")
    return c


def test_get_destinations():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    config = conf().cleaner
    cleaner = Cleaner(config)

    date = datetime.datetime.now() - datetime.timedelta(days=1)

    # first put a few destinations
    prefix = config["dest_path"]+date.strftime(DATE_FORMAT)+"/"
    put_key(config["url"], prefix+"EC1")
    put_key(config["url"], prefix + "FOO")
    put_key(config["url"], prefix + "FOO2")

    # retrieve destinations
    dests = cleaner.get_destinations(date)
    assert len(dests) == 3


def test_delete_destination_keys():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    config = conf().cleaner
    cleaner = Cleaner(config)

    date = datetime.datetime.now() - datetime.timedelta(days=1)

    # first put a few destinations
    prefix = config["dest_path"] + date.strftime(DATE_FORMAT) + "/"
    put_key(config["url"], prefix + "EC1")
    put_key(config["url"], prefix + "FOO")
    put_key(config["url"], prefix + "FOO2")

    # delete destinations
    n_deleted = cleaner.delete_destination_keys(date)
    assert n_deleted == 3

    # retrieve destinations
    dests = cleaner.get_destinations(date)
    print(dests)
    assert len(dests) == 0


def test_delete_dissemination_keys():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    config = conf().cleaner
    cleaner = Cleaner(config)

    date = datetime.datetime.now() - datetime.timedelta(days=1)

    # first put a few dissemination keys
    put_key(config["url"], config["diss_path"] + "EC1/date=" + date.strftime(DATE_FORMAT)+"/aaaa")
    put_key(config["url"], config["diss_path"] + "EC1/date=" + date.strftime(DATE_FORMAT)+"/bbbb")
    put_key(config["url"], config["diss_path"] + "EC1/date=" + date.strftime(DATE_FORMAT)+"/cccc")

    # delete dissemination keys
    n_deleted = cleaner.delete_keys(date, "EC1")
    assert n_deleted == 3


def test_delete_mars_keys():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    config = conf().cleaner
    cleaner = Cleaner(config)

    date = datetime.datetime.now() - datetime.timedelta(days=1)

    # first put a few MARS keys
    put_key(config["url"], config["mars_path"] + "date=" + date.strftime(DATE_FORMAT)+"/aaaa")
    put_key(config["url"], config["mars_path"] + "date=" + date.strftime(DATE_FORMAT)+"/bbbb")
    put_key(config["url"], config["mars_path"] + "date=" + date.strftime(DATE_FORMAT)+"/cccc")

    # delete MARS keys
    n_deleted = cleaner.delete_keys(date)
    assert n_deleted == 3


def test_run_cleaner():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    config = conf().cleaner
    cleaner = Cleaner(config)

    date = datetime.datetime.now() - datetime.timedelta(days=config["retention_period"])

    # check that there are no destinations
    cleaner.delete_destination_keys(date)
    assert len(cleaner.get_destinations(date)) == 0

    # first put a few destinations and keys
    prefix = config["dest_path"] + date.strftime(DATE_FORMAT) + "/"
    put_key(config["url"], prefix + "EC1")
    put_key(config["url"], config["diss_path"] + "EC1/date=" + date.strftime(DATE_FORMAT) + "/aaaa")
    put_key(config["url"], config["diss_path"] + "EC1/date=" + date.strftime(DATE_FORMAT) + "/bbbb")
    put_key(config["url"], config["diss_path"] + "EC1/date=" + date.strftime(DATE_FORMAT) + "/cccc")

    # run the whole workflow
    cleaner.run()

    # check that there are no destinations
    assert len(cleaner.get_destinations(date)) == 0


def put_key(url, key):
    url = url + "/v3/kv/put"
    body = {
        "key": encode_to_str_base64(key),
        "value": ""
    }
    # make the call
    resp = requests.post(url, json=body)
    assert resp.status_code == 200, f'Not able to put key {key}, status {resp.status_code}, ' \
        f'{resp.reason}, {resp.content.decode()}'


