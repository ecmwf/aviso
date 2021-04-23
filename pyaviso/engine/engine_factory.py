# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from .. import logger
from ..authentication.auth import Auth
from ..custom_exceptions import EngineException
from ..user_config import EngineConfig
from . import EngineType


class EngineFactory:
    """
    Factory class of the Engine objects. It uses the server specific implementation depending on the value of
    ServerType.ETCD3
    """

    def __init__(self, engine_conf: EngineConfig, auth: Auth):
        """
        It uses the EngineConfig object to instantiate one instance of the server object. This instance contains the
        user's authentication details and the server URL. It is unique across the various Engine objects
        :param engine_conf:
        :param auth
        """
        assert engine_conf is not None, "Engine configuration required"
        assert engine_conf.host != "", "Server host is required"
        assert engine_conf.port != "", "Server port is required"
        assert engine_conf.type != "", "Server type is required"
        self._conf = engine_conf
        self._auth = auth

    def create_engine(self):
        """
        :return: an instance of the specific implementation of the Engine class
        """
        if self._conf.type == EngineType.ETCD_GRPC:
            # connect to the server by using pythonEtcd3
            logger.debug(f"Setting up gRPC stub to connect to the etcd server {self._conf.host}:{self._conf.port}")
        elif self._conf.type == EngineType.ETCD_REST:
            # connect to the server by using the REST API
            logger.debug(
                f"Setting up REST interface to connect to the etcd server " f"{self._conf.host}:{self._conf.port}"
            )
        elif self._conf.type == EngineType.FILE_BASED:
            # connect to the test file based server
            logger.debug("Setting up file-based test engine")
        else:
            raise EngineException(f"Configuration error - Engine: {self._conf.type} is not recognised")

        # instantiate the engine and return it
        engine_class = self._conf.type.get_class()
        try:
            # instantiate the engine and return
            return engine_class(config=self._conf, auth=self._auth)
        except Exception as e:
            raise EngineException(f"Error in creating the engine {engine_class.__name__}: {e}")
