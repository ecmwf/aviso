.. _how_to:

.. highlight:: console

How to Develop
==============

Aviso source code is available on GitHub at https://github.com/ecmwf/aviso

Please report any issues on GitHub at https://github.com/ecmwf/aviso/issues

Below a few steps to guide the development:

* Clone Aviso repository::

    git clone https://github.com/ecmwf/aviso.git

* Install pyaviso for development, from inside the main aviso folder::

    pip install -e .

* Install development dependencies::

    pip install -U -r tests/requirements-dev.txt

* Unit and system tests for pyaviso can be run with `pytest <https://pytest.org>`_ with::

    pytest tests -v --cov=pyaviso --cache-clear

* Ensure to comply with PEP8 code quality::
    
    tox -e quality

* Before submitting a pull request run all tests and code quality check::

    tox



