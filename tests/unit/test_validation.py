# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os

from pyaviso import logger
from pyaviso.event_listeners.event_listener import EventListener
from pyaviso.event_listeners.validation import (
    DateHandler,
    EnumHandler,
    FloatHandler,
    IntHandler,
    RegexHandler,
    StringHandler,
    TimeHandler,
)


def test_int_handler():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    schema = {"range": [0, 20], "canonic": "{0:0>4}", "error": "error"}
    try:
        validator = IntHandler(key="test", **schema)
    except TypeError as e:
        assert e.args[0] == "__init__() got an unexpected keyword argument 'error'"

    schema = {"range": [0, 20], "canonic": "{0:0>4}"}

    validator = IntHandler(key="test", **schema)
    try:
        result = validator.process("aaa")
    except ValueError as e:
        assert e.args[0] == "Key test has to be an integer"
    try:
        result = validator.process("12")
    except ValueError as e:
        assert e.args[0] == "Key test has to be an integer"

    result = validator.process(12.33)
    assert result == "0012"

    result = validator.process(12)
    assert result == "0012"

    try:
        result = validator.process(25)
    except ValueError as e:
        assert e.args[0] == "Value 25 for key test is outside the range defined"

    try:
        result = validator.process(-2)
    except ValueError as e:
        assert e.args[0] == "Value -2 for key test is outside the range defined"


def test_float_handler():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    schema = {"canonic": "{:2.2f}"}

    validator = FloatHandler(key="test", **schema)
    try:
        result = validator.process("aaa")
    except ValueError as e:
        assert e.args[0] == "Key test has to be a float"
    try:
        result = validator.process("12")
    except ValueError as e:
        assert e.args[0] == "Key test has to be a float"

    result = validator.process(12.33243254323)
    assert result == "12.33"

    result = validator.process(12)
    assert result == "12.00"


def test_regex_handler():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    schema = {"regex": "a"}

    validator = RegexHandler(key="test", **schema)
    try:
        result = validator.process("bbb")
    except ValueError as e:
        assert e.args[0] == "Value bbb is not valid for key test"

    result = validator.process("aaa")
    assert result == "aaa"


def test_string_handler():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    schema = {"canonic": "upper"}

    validator = StringHandler(key="test", **schema)
    result = validator.process("aaa")
    assert result == "AAA"

    schema = {"canonic": "uppercase"}
    validator = StringHandler(key="test", **schema)
    try:
        result = validator.process("aaa")
    except AttributeError as e:
        assert e.args[0] == "Case uppercase not recognised"


def test_date_handler():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    schema = {"canonic": "%Y%m%d"}

    validator = DateHandler(key="test", **schema)
    try:
        result = validator.process("aaa")
    except ValueError as e:
        assert e.args[0] == "Date attribute is not complying with the format defined"
    try:
        result = validator.process("12")
    except ValueError as e:
        assert e.args[0] == "Date attribute is not complying with the format defined"
    try:
        result = validator.process(12)
    except ValueError as e:
        assert e.args[0] == "Date attribute is not complying with the format defined"
    try:
        result = validator.process("2020/02/15")
    except ValueError as e:
        assert e.args[0] == "Date attribute is not complying with the format defined"

    result = validator.process("20200215")
    assert result == "20200215"

    result = validator.process("202021")
    assert result == "20200201"


def test_enum_handler():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    schema = {"values": ["1", "2", "3"]}

    validator = EnumHandler(key="test", **schema)
    try:
        result = validator.process("11")
    except ValueError as e:
        assert e.args[0] == "Key test accepts only the following values: 1,2,3"
    try:
        result = validator.process(1)
    except ValueError as e:
        assert e.args[0] == "Key test is not of a valid type"

    result = validator.process("1")
    assert result == "1"


def test_time_handler():
    logger.debug(os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0])

    schema = {"values": ["0", "6", "12", "18"], "canonic": "{0:0>2}"}

    validator = TimeHandler(key="test", **schema)
    try:
        result = validator.process("11")
    except ValueError as e:
        assert e.args[0] == "Key test accepts only the following values: 0,6,12,18"
    try:
        result = validator.process(12)
    except ValueError as e:
        assert e.args[0] == "Key test is not of a valid type"

    result = validator.process("12")
    assert result == "12"

    result = validator.process("0")
    assert result == "00"


def test_multiple_types():
    schema = {"postproc": [{"type": "EnumHandler", "values": ["auto", "'off'"]}, {"type": "IntHandler"}]}

    params = {"postproc": "auto"}
    EventListener._validate(params, schema)
    assert params["postproc"] == "auto"

    params = {"postproc": 12}
    EventListener._validate(params, schema)
    assert params["postproc"] == "12"

    params = {"postproc": "aaaa"}
    try:
        EventListener._validate(params, schema)
    except ValueError as e:
        assert e.args[0] == "Value aaaa is not valid for key postproc"

    params = {"postproc": "12"}
    try:
        EventListener._validate(params, schema)
    except ValueError as e:
        assert e.args[0] == "Value 12 is not valid for key postproc"

    params = {"postproc": 12.5}
    EventListener._validate(params, schema)
    assert params["postproc"] == "12"
