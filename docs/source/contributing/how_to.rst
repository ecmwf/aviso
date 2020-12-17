.. _how_to:

.. highlight:: console

How to develop
==============

.. Warning::
   This documentation is work in progress.
   
Install Aviso following :ref:`getting_started` and then install development dependencies::

    % pip install -U -r tests/requirements-dev.txt

Unit tests can be run with `pytest <https://pytest.org>`_ with::

    % pytest -v --flakes --cov=aviso --cov-report=html --cache-clear

Coverage can be checked opening in a browser the file ``htmlcov/index.html`` for example with::

    % open htmlcov/index.html

Please ensure the coverage at least stays the same before you submit a pull request.

Enforce PEP8 code quality by running `black` with:::

    % black --line-length=120 ecmwf_aviso
