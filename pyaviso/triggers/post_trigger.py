# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import importlib
import json
from enum import Enum
from typing import Dict

import boto3
import requests
from cloudevents.http import CloudEvent, to_structured

from .. import logger
from ..custom_exceptions import TriggerException
from . import trigger


class ProtocolType(Enum):
    """
    Enum for the various protocols accepted by the post triggers
    """

    cloudevents_http = ("post_trigger", "PostCloudEventsHttp")
    cloudevents_aws = ("post_trigger", "PostCloudEventsAws")

    def get_class(self):
        module = importlib.import_module("pyaviso.triggers." + self.value[0])
        return getattr(module, self.value[1])


class PostTrigger(trigger.Trigger):
    """
    This class implements a trigger in charge of posting the notification accordingly to the protocol selected.
    This class expects the param protocol and protocol type. The remaining fields are optional.
    """

    def __init__(self, notification: Dict, params: Dict):
        trigger.Trigger.__init__(self, notification, params)
        assert params.get("protocol") is not None, "protocol is a mandatory field"
        protocol_params = params.get("protocol")
        assert protocol_params.get("type") is not None, "protocol type is a mandatory field"
        self.protocol = ProtocolType[protocol_params.get("type").lower()].get_class()(notification, protocol_params)

    def execute(self):
        logger.info("Starting Post Trigger for (params.get('protocol'))...'")

        # execute the specific protocol
        self.protocol.execute()

        logger.debug("Post Trigger completed")


class PostCloudEventsHttp:
    """
    This class implements a trigger in charge of translating the notification in a CloudEvents message and
    POST it to the HTTP API specified by the user.
    This class expects the params to contain the URL where to send the message to. The remaining fields are optional.
    """

    TIMEOUT_DEFAULT = 60
    TYPE_DEFAULT = "aviso"
    SOURCE_DEFAULT = "https://aviso.ecmwf.int"

    def __init__(self, notification: Dict, params: Dict):
        self.notification = notification
        assert params.get("url") is not None, "url is a mandatory field"
        self.url = params.get("url")
        self.timeout = params.get("timeout", self.TIMEOUT_DEFAULT)
        self.headers = params.get("headers", {})

        # cloudEvents specific fields
        if params.get("cloudevents"):
            self.type = params.get("cloudevents").get("type", self.TYPE_DEFAULT)
            self.source = params.get("cloudevents").get("source", self.SOURCE_DEFAULT)
        else:
            self.type = self.TYPE_DEFAULT
            self.source = self.SOURCE_DEFAULT

    def execute(self):

        # prepare the CloudEvents message

        attributes = {
            "type": self.type,
            "source": self.source,
            "time": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        data = self.notification
        event = CloudEvent(attributes, data)

        # Creates the HTTP request representation of the CloudEvents in structured content mode
        headers, body = to_structured(event)
        self.headers.update(headers)

        logger.debug(f"Sending CloudEvents notification {data}")

        # send the message
        try:
            resp = requests.post(self.url, data=body, headers=self.headers, verify=False, timeout=self.timeout)
        except Exception as e:
            logger.error("Not able to POST CloudEvents notification")
            raise TriggerException(e)
        if resp.status_code != 200:
            raise TriggerException(
                f"Not able to POST CloudEvents notification to {self.url}, "
                f"status {resp.status_code}, {resp.reason}, {resp.content.decode()}"
            )

        logger.debug("CloudEvents notification sent successfully")


class PostCloudEventsAws:
    """
    This class implements a trigger in charge of translating the notification in a CloudEvents messag and send it to a
    AWS topic specified by the user.
    """

    TIMEOUT_DEFAULT = 60
    TYPE_DEFAULT = "aviso"
    SOURCE_DEFAULT = "https://aviso.ecmwf.int"

    def __init__(self, notification: Dict, params: Dict):
        self.notification = notification
        assert params.get("arn") is not None, "arn is a mandatory field"
        self.arn = params.get("arn")
        assert params.get("region_name") is not None, "region_name is a mandatory field"
        self.region_name = params.get("region_name")
        self.MessageAttributes = params.get("MessageAttributes")
        # authentication is optional or is automatically set from ~/.aws/credentials
        self.aws_access_key_id = params.get("aws_access_key_id")
        self.aws_secret_access_key = params.get("aws_secret_access_key")
        # only for FIFO topics
        self.MessageGroupId = params.get("MessageGroupId")

        # cloudEvents specific fields
        if params.get("cloudevents"):
            self.type = params.get("cloudevents").get("type", self.TYPE_DEFAULT)
            self.source = params.get("cloudevents").get("source", self.SOURCE_DEFAULT)
        else:
            self.type = self.TYPE_DEFAULT
            self.source = self.SOURCE_DEFAULT

    def execute(self):

        # prepare the AWS topic message

        attributes = {
            "type": self.type,
            "source": self.source,
            "time": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        data = self.notification
        event = CloudEvent(attributes, data)

        # Creates the HTTP request representation of the CloudEvents in structured content mode
        headers, body = to_structured(event)
        event_body = body.decode()
        event_dict = json.loads(event_body)

        # Create message for AWS topic
        aws_publish_params = {
            "TopicArn": self.arn,
            "Message": json.dumps({"default": event_body}),
            "MessageStructure": "json",
            "Subject": self.type,
        }
        if self.MessageAttributes:
            aws_publish_params["MessageAttributes"] = self.MessageAttributes
        if self.MessageGroupId:
            aws_publish_params["MessageDeduplicationId"] = event_dict["id"]
            aws_publish_params["MessageGroupId"] = self.MessageGroupId

        logger.debug(f"Sending AWS topic notification {aws_publish_params}")

        # send the message
        try:
            sns = boto3.client(
                "sns",
                region_name=self.region_name,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )

            # this is the SNS standard to support
            sns.publish(**aws_publish_params)

        except Exception as e:
            logger.error("Not able to send AWS topic notification")
            raise TriggerException(e)

        logger.debug("AWS topic notification sent successfully")
