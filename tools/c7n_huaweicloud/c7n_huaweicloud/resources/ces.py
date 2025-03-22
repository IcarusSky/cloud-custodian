# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import logging

from c7n_huaweicloud.actions.base import HuaweiCloudBaseAction
from c7n_huaweicloud.provider import resources
from c7n_huaweicloud.query import QueryResourceManager, TypeInfo

log = logging.getLogger("custodian.huaweicloud.resources.alarm")


@resources.register('alarm')
class Alarm(QueryResourceManager):
    class resource_type(TypeInfo):
        service = 'cesv2'
        enum_spec = ("list_alarm_rules", 'alarms', 'offset')
        id = 'alarm_id'
        tag = True

