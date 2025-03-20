# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import logging

from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkces.v2 import *

from c7n.utils import type_schema
from c7n_huaweicloud.actions.base import HuaweiCloudBaseAction
from c7n_huaweicloud.provider import resources
from c7n_huaweicloud.query import QueryResourceManager, TypeInfo

log = logging.getLogger("custodian.huaweicloud.resources.alarm")


@resources.register('alarm')
class Alarm(QueryResourceManager):
    class resource_type(TypeInfo):
        service = 'ces'
        enum_spec = ("list_alarm_rules", 'alarms', 'offset')
        id = 'alarm_id'
        tag = True


@Alarm.action_registry.register("delete")
class AlarmDelete(HuaweiCloudBaseAction):
    """Deletes CES Alarm.

    :Example:

    .. code-block:: yaml

        policies:
          - name: delete-stopped-alarm
            resource: huaweicloud.alarm
            flters:
              - type: value
                key: alarm_action_enabled
                value: true
            actions:
              - delete
    """

    schema = type_schema("delete")

    def perform_action(self, resource):
        client = self.manager.get_client()
        request = BatchDeleteAlarmRulesRequest()
        request.body = BatchDeleteAlarmsRequestBody(alarm_ids=resource)
        response = client.batch_delete_alarm_rules(request)
        log.info(f"Received Job ID:{response}")
        # TODO: need to track whether the job succeed
        response = None
        return response
