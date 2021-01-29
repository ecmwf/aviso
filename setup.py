# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import io
import re

from setuptools import setup, find_packages

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',  # It excludes inline comment too
    io.open('pyaviso/version.py', encoding='utf_8_sig').read()
).group(1)

setup(
    name='aviso',
    description='Aviso is a notification application allowing users to send and receive custom events and to trigger '
                'users workflows',
    version=__version__,
    url='https://git.ecmwf.int/projects/AVISO/repos/aviso/browse',
    author='ECMWF',
    packages=find_packages(exclude=("tests", "frontend", "admin", "auth")),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'Click>=7.0',
        'etcd3>=0.11.1',
        'PyYAML>=5.1.2',
        'python-json-logger>=0.1.11',
        'requests>=2.23.0',
        'parse>=1.12.1',
        'pyinotify>=0.9.6',
        'cloudevents>=1.2.0'
    ],
    entry_points={
        'console_scripts': [
            'aviso=pyaviso.cli_aviso:cli',
            'aviso-config=pyaviso.cli_aviso_config:cli'
        ]
    }
)
