# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import random
import time
from datetime import datetime

from aviso_admin import config, logger
from aviso_admin.compactor import Compactor


def conf() -> config.Config:  # this automatically configure the logging
    c = config.Config(conf_path="tests/config.yaml")
    return c


def test_get_current_server_rev():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    compactor = Compactor(conf().compactor)
    rev = compactor.get_current_server_rev()
    print(rev)
    assert rev is not None
    assert rev > 0


def test_save_rev():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    compactor = Compactor(conf().compactor)
    rev = random.randint(1, 100000)
    res = compactor.save_rev(rev, datetime.now())
    assert res

    history = compactor.get_history()
    rev_h = list(filter(lambda h: h["revision"]==rev, history))
    assert len(rev_h) == 1


def test_clean_history():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    compactor = Compactor(conf().compactor)

    # first save a revision
    res = compactor.save_rev(1112, datetime.now())
    assert res

    # now retrieve it back
    old_rev = compactor.clean_history(datetime.now())
    assert old_rev == 1112


def test_compact():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    compactor = Compactor(conf().compactor)

    # first get the current version
    rev = compactor.get_current_server_rev()

    # compact revision
    res = compactor.compact(rev)
    assert res


def test_compact_run():
    logger.debug(os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0])
    compactor = Compactor(conf().compactor)
    compactor.clean_history(datetime.now())
    rev_init = compactor.get_current_server_rev()

    for i in range(5):
        compactor.run(sec_ret_per=True)
        time.sleep(1)
    rev_end = compactor.get_current_server_rev()
    # there are 2 revisions for every run: one for saving the rev and one for cleaning the history
    assert rev_end-rev_init == 10
    try:
        compactor.compact(rev_end - 6)
        assert False
    except AssertionError as e:
        assert True

    try:
        compactor.compact(rev_end - 4)
        assert True
    except AssertionError as e:
        assert False

