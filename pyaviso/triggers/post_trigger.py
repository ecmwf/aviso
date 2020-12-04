# (C) Copyright 1996- ECMWF.
# 
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import requests
import json
from typing import Dict
import uuid
import datetime

from . import trigger
from .trigger import TriggerType
from .. import logger
from ..custom_exceptions import TriggerException


class PostTrigger(trigger.Trigger):
    """
    This class implements a trigger in charge of translating the notification in a CloudEvent message and 
    POST it to the URL specified by the user.
    This class expects the params to contain the URL where to send the message to. The remaining fields are optional.
    """
    TIMEOUT_DEFAULT = 60
    CLOUDEVENT_TYPE_DEFAULT = "aviso"
    CLOUDEVENT_SOURCE_DEFAULT = "https://aviso.ecmwf.int"

    def __init__(self, notification: Dict, params: Dict):
        trigger.Trigger.__init__(self, notification, params)
        assert params.get("url") is not None, "url is a mandatory field"
        self.url = params.get("url")
        self.trigger_type = TriggerType.post
        self.timeout = self.params.get("timeout", self.TIMEOUT_DEFAULT)
        self.cloudevent_type = self.params.get("cloudevent_type", self.CLOUDEVENT_TYPE_DEFAULT)
        self.cloudevent_source = self.params.get("cloudevent_source", self.CLOUDEVENT_SOURCE_DEFAULT)
        self.headers = self.params.get("headers", {})

    def execute(self):
        logger.info(f"Starting Post Trigger...'")
        
        # prepare the CloudEvent message
        data = {
            "type": self.cloudevent_type,
            "data": self.notification,
            "datacontenttype": "application/json",
            "id": str(uuid.uuid4()),
            "source": self.cloudevent_source,                    
            "specversion": "1.0",
            "time": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        logger.debug(f"Sending CloudEvent notification {data}")
        try:
            resp = requests.post(self.url, json=data, headers=self.headers, verify=False, timeout=self.timeout)
        except Exception as e:
            logger.error("Not able to POST CloudEvent notification")
            raise TriggerException(e) 
        if resp.status_code != 200:
            raise TriggerException(f"Not able to POST CloudEvent notification to {self.url}, "
                         f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}")
             
        logger.debug(f"Post Trigger completed")
