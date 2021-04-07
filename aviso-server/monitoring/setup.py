# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from aviso_monitoring import __version__
from setuptools import setup, find_packages

setup(
    name='aviso-monitoring',
    description='Aviso_monitoring is a library providing collectors to fetch telemetries, receivers and reporters to '
                'transmit them to the monitoring servers',
    version=__version__,
    url='https://git.ecmwf.int/projects/AVISO/repos/aviso/browse',
    author='ECMWF',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'PyYAML>=5.1.2',
        'python-json-logger>=0.1.11',
        'requests>=2.23.0',
        'flask>=1.1.2',
    ],
    entry_points={}
)
