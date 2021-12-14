# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import os
from shutil import rmtree
from typing import Dict, List

from . import logger
from .authentication.auth import Auth
from .custom_exceptions import ServiceConfigException
from .engine import engine_factory as ef
from .user_config import UserConfig

KEY_PREFIX = "/ec/config/"
MAX_FILE_SIZE_HARD = 1048576  # 1MiB


class ServiceConfigManager:
    """
    This class manages the operations associated to the configuration server
    """

    def __init__(self, config: UserConfig):
        """

        :param config: UserConfig object
        """
        logger.debug("Creating the engine")
        # Create the engine factory
        engine_factory: ef.EngineFactory = ef.EngineFactory(config.configuration_engine, Auth.get_auth(config))
        # Create the engine to connect to the configuration server
        self._engine = engine_factory.create_engine()
        self._max_file_size = config.configuration_engine.max_file_size

    def push(self, service: str, directory: str, user_message: str, delete: bool) -> List[str]:
        """
        This method implements the push command
        :param service: service to push to
        :param directory: directory from where to read the files to push
        :param user_message: message associated to this push operation
        :param delete: if True the files not pushed will be deleted from the server folder
        :return: List of files pushed
        """
        logger.debug("Calling push...")

        # Find the KV pairs in the dir
        if not directory.endswith("/"):
            directory = directory + "/"
        logger.debug(f"Looking for file in the directory {directory}")
        service_key = self._build_service_key(service)
        max_file_size_soft = self._max_file_size * 1024  # convert KiB to B
        kvs: List[Dict[str, any]] = []
        pushed_files: List[str] = []
        for x in os.walk(directory):
            for fp in x[2]:  # any file
                # prepare the key with suffix and prefix
                local_path = x[0]
                # removing the directory part so to have just the relative path
                suffix = local_path[len(directory) :]
                key: str = os.path.join(service_key, suffix, fp)
                fp_path = os.path.join(local_path, fp)

                # check file size limits
                if os.path.getsize(fp_path) > MAX_FILE_SIZE_HARD:
                    logger.warning(f"File {fp} exceeds hard limit of max file size allowed of {MAX_FILE_SIZE_HARD}B ")
                    continue
                if os.path.getsize(fp_path) > max_file_size_soft:
                    logger.warning(
                        f"File {fp} exceeds the configured max file size allowed of {max_file_size_soft}B, "
                        f"try increasing the limit in the configuration"
                    )
                    continue
                # prepare the value, read the file as binary
                with open(fp_path, "rb") as f:
                    value: bytes = f.read()
                kv: Dict[str, bytes] = {"key": key, "value": value}
                kvs.append(kv)
                pushed_files.append(f.name)
                logger.debug("Pushing file")

        # check if we need to delete any file
        ks_delete = []
        if delete:
            old_kvs = self._engine.pull(service_key)
            new_keys = []
            for new_kv in kvs:
                new_keys.append(new_kv["key"])
            for old_kv in old_kvs:
                old_key = old_kv["key"]
                if old_key not in new_keys:  # we need to delete this key
                    ks_delete.append(old_key)
                    logger.debug(f"Selecting file to delete: {old_key}")

        # push all the pairs as one transaction to the service
        if len(kvs) > 0:
            base_key = self._build_service_key(service, root_only=True)
            logger.debug("Calling the engine push with status update")
            if self._engine.push_with_status(kvs, base_key=base_key, message=user_message, ks_delete=ks_delete):
                logger.debug(f"Push operation for service {service} successfully executed")
                return pushed_files
            else:
                raise ServiceConfigException(f"Push operation for service {service} has failed")
        else:
            logger.debug(f"No file found to push to service {service}")
            return pushed_files

    def pull(self, service: str, key_only=False) -> List[List[any]]:
        """
        This method implements the pull command
        :param service: service to pull from
        :param key_only: if True no values are returned
        :return: KV pairs
        """
        logger.debug("Calling pull...")
        # pull the service
        service_key = self._build_service_key(service)
        kvs = self._engine.pull(service_key, key_only)
        if len(kvs) != 0:
            for kv in kvs:
                file_name = kv["key"]
                logger.debug(f"File pulled: {file_name}")
        else:
            logger.debug(f"No files found for service {service}")

        return kvs

    def remove(self, service: str) -> List[str]:
        """
        This method implements the remove command
        :param service: service to remove
        :return: List of files deleted
        """
        logger.debug("Calling remove...")
        # delete the service including the status
        service_key = self._build_service_key(service, root_only=True)
        kvs = self._engine.delete(service_key, prefix=True)
        removed_files = []
        if len(kvs) == 0:
            logger.debug(f"No file found for service {service}")
        else:
            for kv in kvs:
                file_name = kv["key"]
                logger.debug(f"File deleted: {file_name}")
                removed_files.append(file_name)
            logger.debug(f"Remove operation for service {service} successfully executed")
        return removed_files

    def pull_and_save(self, service: str, directory: str, delete: bool) -> List[str]:
        """
        This method implements the pull command and save the files retrieved to disk
        :param service: service to pull from
        :param directory: directory to save the file to
        :param delete: if True the files not pulled will be deleted from the local folder
        :return: List of files pulled
        """
        logger.debug("Calling pull and save...")

        service_key = self._build_service_key(service)

        # pull the service
        kvs: List[List[any]] = self._engine.pull(service_key)
        # look at the result
        pulled_files = []
        pulled_files_tmp = []
        if len(kvs) > 0:

            # First check if we need to delete the existing folder
            if delete and os.path.exists(directory):
                try:
                    # try to delete it
                    rmtree(directory)
                    logger.debug(f"Existing directory {directory} successfully deleted.")
                except Exception as e:
                    logger.warning(f"Error in deleting the folder {directory}: {e}")
                    logger.debug("", exc_info=True)

            # save the files retrieved with .tmp suffix
            for kv in kvs:
                # extract the file path and create the directory structure
                relative_file_path = kv["key"][len(service_key) :]
                full_path = os.path.join(directory, relative_file_path)
                full_path_tmp = full_path + ".tmp"
                os.makedirs(os.path.dirname(full_path_tmp), exist_ok=True)
                with open(full_path_tmp, "wb") as f:
                    f.write(kv["value"])
                    logger.debug(f"File successfully saved: {full_path_tmp}")
                    pulled_files.append(full_path)
                    pulled_files_tmp.append(full_path_tmp)

            # unlink existing files
            for f in pulled_files:
                try:
                    os.unlink(f)
                    logger.debug(f"File successfully unlinked: {f}")
                except FileNotFoundError:  # ignore
                    pass

            # remove the .tmp suffix
            for f_tmp, f in zip(pulled_files_tmp, pulled_files):
                os.rename(f_tmp, f)
                logger.debug(f"File successfully renamed: {f}")

            logger.debug(f"Pull operation for service {service} successfully executed")

        else:
            logger.debug(f"No file found for service {service}")

        return pulled_files

    def status(self, service: str) -> Dict[str, str]:
        """
        This method retrieves the status of the service passed
        :param service: service to check
        :return: status as dictionary
        """
        logger.debug("Calling status...")
        # pull the service
        service_key = self._build_service_key(service, root_only=True)
        kvs = self._engine.pull(service_key, prefix=False)
        if len(kvs) == 0:
            logger.warning(f"No service {service} found")
            return {}
        elif len(kvs) > 1:
            logger.error(f"Error in retrieving the status of service {service}, more than one KV returned")
            return {}

        logger.debug("Reading status from retrieved result")
        status = kvs[0]["value"].decode()
        status = json.loads(status)
        # add version to it
        status["version"] = kvs[0]["version"]
        logger.debug(f"Status retrieved for service {service}: {status}")

        return status

    def revert(self, service: str) -> List[str]:
        """
        This method reverts the service defined to the previous version
        :param service: service to revert
        :return: List of files reverted
        """
        #  first get the current version and revision
        logger.debug("Calling revert...")
        # pull the service
        service_key = self._build_service_key(service, root_only=True)
        kvs = self._engine.pull(service_key, key_only=True)
        reverted_files = []
        if len(kvs) == 0:
            logger.debug(f"No file found for service {service}")
            return reverted_files

        revert_kvs = []
        # for each file
        for kv in kvs:
            if kv["version"] == 1:  # we cannot revert this file
                continue
            # first we need to find the revision associated with the previous version
            target_version = kv["version"] - 1
            mod_rev = kv["mod_rev"]
            create_rev = kv["create_rev"]
            key = kv["key"]
            while mod_rev > create_rev:
                # retrieve the previous revision
                new_rev = mod_rev - 1
                old_kvs = self._engine.pull(key, key_only=True, rev=new_rev, prefix=False)
                if len(old_kvs) != 1:
                    raise ServiceConfigException(f"Error in retrieving older versions of key {key}, revision {new_rev}")
                new_kv = old_kvs[0]
                # it may be still the same version
                if new_kv["version"] == target_version:
                    # retrieve now the file of the target version and save it for later
                    old_kvs = self._engine.pull(key, rev=new_rev, prefix=False)
                    key = old_kvs[0]["key"]
                    revert_kvs.append(old_kvs[0])
                    logger.debug(f"File {key} waiting to be reverted to version {target_version}")
                    break

        if len(revert_kvs) == 0:
            logger.debug(f"No revertible file found for service {service}")
        else:
            # push it back to the store as a new version
            if self._engine.push(revert_kvs):
                for kv in revert_kvs:
                    key = kv["key"]
                    version = kv["version"]
                    reverted_files.append(key)
                    logger.debug(f"File {key} successfully reverted to version {version}")
            else:
                raise ServiceConfigException(f"Service {service} could not be reverted to previous version")

            logger.debug(f"Revert operation for service {service} successfully executed")

        return reverted_files

    def _build_service_key(self, service: str, root_only=False) -> str:
        """
        :param service:
        :param root_only: if True will return the service key with no "/" to indicate only the root key
        :return: the key associated to the folder of the service on the key-value store
        """
        suffix = "/"
        if service.endswith("/") or root_only:
            suffix = ""
        service_key = KEY_PREFIX + service + suffix
        return service_key
