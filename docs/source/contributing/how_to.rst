.. _how_to:

.. highlight:: console

How to Develop
==============

Aviso source code is available on GitHub at https://github.com/ecmwf/aviso

Please report any issues on GitHub at https://github.com/ecmwf/aviso/issues

Below a few steps to guide the development:

* Install Aviso following :ref:`getting_started` and then install development dependencies::

    pip install -U -r tests/requirements-dev.txt

* Unit tests can be run with `pytest <https://pytest.org>`_ with::

    pytest -v --cov=pyaviso --cov-report=html --cache-clear

* Coverage can be checked opening in a browser the file ``htmlcov/index.html`` . Without the option ``--cov-report=html`` it will be printed to the console output. Please ensure the coverage at least stays the same before you submit a pull request.

* Please ensure to comply with PEP8 code quality 



