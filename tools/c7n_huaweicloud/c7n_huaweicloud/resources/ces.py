# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import logging
import smtplib

from huaweicloudsdkces.v1 import *
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkces.v2 import *
from huaweicloudsdksmn.v2 import PublishMessageRequest, PublishMessageRequestBody

from c7n.actions import Notify, ActionRegistry, BaseAction
from c7n.filters.missing import Missing
from c7n.filters import Filter, FilterRegistry, ValueFilter
from c7n.utils import type_schema
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


Alarm.filter_registry.register('missing', Missing)


@Alarm.action_registry.register("alarm-update-notification")
class AlarmUpdateNotification(HuaweiCloudBaseAction):
    """Update CES Alarm notification settings.

    :Example:

    .. code-block:: yaml

policies:
  - name: ces-alarm-have-smn-check
    description: "Filter all alarm rules that do not have notifications enabled. Update the SMN notifications corresponding to these alarm settings"
    resource: huaweicloud.alarm
    filters:
      - type: value
        key: notification_enabled
        value: false
    actions:
      - type: alarm-update-notification
        parameters:
          action_type: "notification"
          notification_list:
            - "urn:smn:cn-north-4:xxxxxxxxxxx:ces_notification_group_xxxxx"

    """

    schema = type_schema(
        "alarm-update-notification",
        required=["parameters"],
        **{
            "parameters": {
                "type": "object",
                "required": ["notification_list", "action_type"],
                "properties": {
                    "notification_list": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "action_type": {
                        "type": "string",
                        "enum": ["notification"]
                    }
                }
            }
        }
    )

    def perform_action(self, resource):
        params = self.data.get('parameters', {})
        action_type = params.get('action_type', 'notification')
        response = None
        # 告警更新切换到V1接口
        self.manager.resource_type.service = 'cesv1'
        client = self.manager.get_client()
        request = UpdateAlarmRequest()
        request.alarm_id = resource["id"]
        list_ok_actions_body = [
            AlarmActions(
                type=action_type,
                notification_list=params['notification_list']
            )
        ]
        list_alarm_actions_body = [
            AlarmActions(
                type="notification",
                notification_list=params['notification_list']
            )
        ]
        request.body = UpdateAlarmRequestBody(
            ok_actions=list_ok_actions_body,
            alarm_actions=list_alarm_actions_body,
            alarm_action_enabled=True
        )
        try:
            response = client.update_alarm(request)
            log.info(f"Update alarm notification {response}")
        except exceptions.ClientRequestException as e:
            log.error(f"Update alarm notification failed: {e.error_msg}")
        return response


@Alarm.action_registry.register("batch-start-stopped-alarm-rules")
class BatchStartStoppedAlarmRules(HuaweiCloudBaseAction):
    """Update CES Alarm all start.

    :Example:

    .. code-block:: yaml

policies:
  - name: alarm-action-enabled-check
    description: "Verify that all alarm rules must be enabled and enable the disabled alarms."
    resource: huaweicloud.alarm
    filters:
      - type: value
        key: enabled
        value: false
    actions:
      - type: batch-start-stopped-alarm-rules
        parameters:
          subject: "CES alarm not activated Check email"
          message: "You have the following alarms that have not been started, please check the system. The tasks have been started, please log in to the system and check again."
          notification_list:
            - "urn:smn:cn-north-4:xxxxx:CES_notification_xxxxxxx"
    """

    schema = type_schema(
        "batch-start-stopped-alarm-rules",
        required=["parameters"],
        **{
            "parameters": {
                "type": "object",
                "required": ["notification_list", "subject", "message"],
                "properties": {
                    "notification_list": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "subject": {
                        "type": "string",
                    },
                    "message": {
                        "type": "string",
                    }
                }
            }
        }
    )

    def perform_action(self, resource):
        response = None
        client = self.manager.get_client()
        batch_enable_alarm_rule_request = BatchEnableAlarmRulesRequest()
        list_alarm_ids = [resource["id"]]
        batch_enable_alarm_rule_request.body = BatchEnableAlarmsRequestBody(
            alarm_enabled=True,
            alarm_ids=list_alarm_ids
        )
        params = self.data.get('parameters', {})
        subject = params.get('subject', 'subject')
        message = params.get('message', 'message')
        # id_list = '\n'.join([f"- {id}" for id in list_alarm_ids])
        # message += f"\nalarm list:\n{id_list}"
        # message += f"\nregion: {self.region}"
        publish_message_request = PublishMessageRequest()
        publish_message_request.body = PublishMessageRequestBody(
            subject=subject,
            message=message
        )
        try:
            response = client.batch_enable_alarm_rules(batch_enable_alarm_rule_request)
            log.info(f"Batch start alarm, response: {response}")
            self.manager.resource_type.service = 'smn'
            client = self.manager.get_client()
            for topic_urn in params['notification_list']:
                publish_message_request.topic_urn = topic_urn,
                response = client.publish_message(publish_message_request)
            log.info(f"Message send, response: {response}")
        except exceptions.ClientRequestException as e:
            log.error(f"Batch start alarm failed: {e.error_msg}")
        return response


@Alarm.action_registry.register("create-kms-event-alarm-rule")
class CreateKmsEventAlarmRule(BaseAction):
    """Check CES isn't configured KMS change alarm rule.

    :Example:

    .. code-block:: yaml

policies:
  - name: alarm-kms-disable-or-delete-key
    description: "Check whether the monitoring alarm for events that monitor KMS disabling or scheduled key deletion is configured. If not, create the corresponding alarm."
    resource: huaweicloud.alarm
    filters:
        - type: missing
          policy:
            resource: huaweicloud.alarm
            filters:
              - type: value
                key: enabled
                value: true
                op: eq
              - type: value
                key: type
                value: "EVENT.SYS"
                op: eq
              - type: value
                key: namespace
                value: "SYS.KMS"
                op: eq
              - type: list-item
                key: resources
                attrs:
                  - type: value
                    key: "dimensions"
                    value: []
                    op: eq
              - type: value
                key: "contains(policies[].metric_name, 'retireGrant')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'revokeGrant')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'disableKey')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'scheduleKeyDeletion')"
                value: true
                op: eq
    actions:
      - type: create-kms-event-alarm-rule
        parameters:
          action_type: "notification"
          notification_list:
            - "urn:smn:cn-north-4:e196f2790965422f80502748f4d58649:CES_notification_group_kNrnzmm0J"

    """

    schema = type_schema(
        "create-kms-event-alarm-rule",
        required=["parameters"],
        **{
            "parameters": {
                "type": "object",
                "required": ["notification_list", "action_type"],
                "properties": {
                    "notification_list": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "action_type": {
                        "type": "string",
                        "enum": ["notification"]
                    }
                }
            }
        }
    )

    def process(self, resources):
        params = self.data.get('parameters', {})
        action_type = params.get('action_type', 'notification')
        client = self.manager.get_client()
        request = CreateAlarmRulesRequest()

        list_ok_notifications_body = [
            Notification(
                type=action_type,
                notification_list=params['notification_list']
            )
        ]
        list_alarm_notifications_body = [
            Notification(
                type=action_type,
                notification_list=params['notification_list']
            )
        ]
        list_policies_body = [
            Policy(
                metric_name="retireGrant",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="revokeGrant",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="disableKey",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="scheduleKeyDeletion",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            )
        ]
        request.body = PostAlarmsReqV2(
            notification_enabled=True,
            enabled=True,
            enterprise_project_id="0",
            notification_end_time="23:59",
            notification_begin_time="00:00",
            ok_notifications=list_ok_notifications_body,
            alarm_notifications=list_alarm_notifications_body,
            type=AlarmType.EVENT_SYS,
            policies=list_policies_body,
            namespace="SYS.KMS",
            description="alarm-kms-change",
            name="alarm-kms-change",
            resources=[]
        )
        try:
            response = client.create_alarm_rules(request)
            log.info(f"Create alarm {response}")
        except exceptions.ClientRequestException as e:
            log.error(f"Create alarm failed: {e.error_msg}")


@Alarm.action_registry.register("create-obs-event-alarm-rule")
class CreateObsEventAlarmRule(BaseAction):
    """Check CES isn't configured OBS change alarm rule.

    :Example:

    .. code-block:: yaml

policies:
  - name: alarm-obs-bucket-policy-change
    description: "Check whether the alarm for the OBS bucket policy change event is configured. If not, create a corresponding alarm."
    resource: huaweicloud.alarm
    filters:
        - type: missing
          policy:
            resource: huaweicloud.alarm
            filters:
              - type: value
                key: enabled
                value: true
                op: eq
              - type: value
                key: type
                value: "EVENT.SYS"
                op: eq
              - type: value
                key: namespace
                value: "SYS.OBS"
                op: eq
              - type: list-item
                key: resources
                attrs:
                  - type: value
                    key: "dimensions"
                    value: []
                    op: eq
              - type: value
                key: "contains(policies[].metric_name, 'setBucketPolicy')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'setBucketAcl')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'deleteBucketPolicy')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'deleteBucket')"
                value: true
                op: eq
    actions:
      - type: create-obs-event-alarm-rule
        parameters:
          action_type: "notification"
          notification_list:
            - "urn:smn:cn-north-4:e196f2790965422f80502748f4d58649:CES_notification_group_kNrnzmm0J"

    """

    schema = type_schema(
        "create-obs-event-alarm-rule",
        required=["parameters"],
        **{
            "parameters": {
                "type": "object",
                "required": ["notification_list", "action_type"],
                "properties": {
                    "notification_list": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "action_type": {
                        "type": "string",
                        "enum": ["notification"]
                    }
                }
            }
        }
    )

    def process(self, resources):
        params = self.data.get('parameters', {})
        action_type = params.get('action_type', 'notification')
        client = self.manager.get_client()
        request = CreateAlarmRulesRequest()

        list_ok_notifications_body = [
            Notification(
                type=action_type,
                notification_list=params['notification_list']
            )
        ]
        list_alarm_notifications_body = [
            Notification(
                type=action_type,
                notification_list=params['notification_list']
            )
        ]
        list_policies_body = [
            Policy(
                metric_name="setBucketPolicy",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="setBucketAcl",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="deleteBucketPolicy",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="deleteBucket",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            )
        ]
        request.body = PostAlarmsReqV2(
            notification_enabled=True,
            enabled=True,
            enterprise_project_id="0",
            notification_end_time="23:59",
            notification_begin_time="00:00",
            ok_notifications=list_ok_notifications_body,
            alarm_notifications=list_alarm_notifications_body,
            type=AlarmType.EVENT_SYS,
            policies=list_policies_body,
            namespace="SYS.OBS",
            description="alarm-obs-change",
            name="alarm-obs-change",
            resources=[]
        )
        try:
            response = client.create_alarm_rules(request)
            log.info(f"Create alarm {response}")
        except exceptions.ClientRequestException as e:
            log.error(f"Create alarm failed: {e.error_msg}")


@Alarm.action_registry.register("create-vpc-event-alarm-rule")
class CreateVpcEventAlarmRule(BaseAction):
    """Check CES isn't configured VPC change alarm rule.

    :Example:

    .. code-block:: yaml

policies:
  - name: alarm-vpc-change
    description: "Check whether the event monitoring alarm for monitoring VPC changes is configured. If not, create the corresponding alarm."
    resource: huaweicloud.alarm
    filters:
        - type: missing
          policy:
            resource: huaweicloud.alarm
            filters:
              - type: value
                key: enabled
                value: true
                op: eq
              - type: value
                key: type
                value: "EVENT.SYS"
                op: eq
              - type: value
                key: namespace
                value: "SYS.VPC"
                op: eq
              - type: list-item
                key: resources
                attrs:
                  - type: value
                    key: "dimensions"
                    value: []
                    op: eq
              - type: value
                key: "contains(policies[].metric_name, 'modifyVpc')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'modifySubnet')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'deleteSubnet')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'modifyBandwidth')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'deleteVpn')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'modifyVpc')"
                value: true
                op: eq
              - type: value
                key: "contains(policies[].metric_name, 'modifyVpn')"
                value: true
                op: eq
    actions:
      - type: create-vpc-event-alarm-rule
        parameters:
          action_type: "notification"
          notification_list:
            - "urn:smn:cn-north-4:e196f2790965422f80502748f4d58649:CES_notification_group_kNrnzmm0J"

    """

    schema = type_schema(
        "create-vpc-event-alarm-rule",
        required=["parameters"],
        **{
            "parameters": {
                "type": "object",
                "required": ["notification_list", "action_type"],
                "properties": {
                    "notification_list": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "action_type": {
                        "type": "string",
                        "enum": ["notification"]
                    }
                }
            }
        }
    )

    def process(self, resources):
        params = self.data.get('parameters', {})
        action_type = params.get('action_type', 'notification')
        client = self.manager.get_client()
        request = CreateAlarmRulesRequest()

        list_ok_notifications_body = [
            Notification(
                type=action_type,
                notification_list=params['notification_list']
            )
        ]
        list_alarm_notifications_body = [
            Notification(
                type=action_type,
                notification_list=params['notification_list']
            )
        ]
        list_policies_body = [
            Policy(
                metric_name="deleteVpc",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="modifyVpn",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="deleteVpn",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="modifyVpc",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="deleteSubnet",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="modifySubnet",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            ),
            Policy(
                metric_name="modifyBandwidth",
                period=0,
                filter="average",
                comparison_operator=">=",
                value=1,
                unit="count",
                count=1,
                suppress_duration=0,
                level=2
            )
        ]
        request.body = PostAlarmsReqV2(
            notification_enabled=True,
            enabled=True,
            enterprise_project_id="0",
            notification_end_time="23:59",
            notification_begin_time="00:00",
            ok_notifications=list_ok_notifications_body,
            alarm_notifications=list_alarm_notifications_body,
            type=AlarmType.EVENT_SYS,
            policies=list_policies_body,
            namespace="SYS.VPC",
            description="alarm-vpc-change",
            name="alarm-vpc-change",
            resources=[]
        )
        try:
            response = client.create_alarm_rules(request)
            log.info(f"Create alarm {response}")
        except exceptions.ClientRequestException as e:
            log.error(f"Create alarm failed: {e.error_msg}")


@Alarm.action_registry.register("alarm-action-enabled-check")
class AlarmActionEnabledCheck(HuaweiCloudBaseAction):
    """alarm-action-enabled-check.

    :Example:

    .. code-block:: yaml

        policies:
          - name: alarm-action-enabled-check
            resource: huaweicloud.alarm
            flters:
              - type: value
                key: alarm_enabled
                value: false
            actions:
              - type: notify
                to:
                  - 1974365584@qq.com
                subject: "Unverified CES Alarm"
                message: "CES alarm {resource.alarm_id} is not started. Please verify th configuration."
                template: default.html
                transport:
                  type: smtp
                  host: smtp.qq.com    # SMTP 服务器地址
                  port: 587            # TLS 加密端口qthjekzidosugdja
                  username: "1974365584@qq.com"
                  password: "qthjekzidosugdja"
                  from: "cloud-alerts@huawei.com"
                  starttls: true
        code-block:: html
        <html>
            <body>
                <h2>CES告警规则状态异常通知</h2>
                    <p>发现以下告警规则状态未开启：</p>
                        <ul>
                            <li>告警规则ID: {{ resource.alarm_id }}</li>
                        </ul>
                    <p>请及时处理！</p>
            </body>
        </html>
    """

    schema = type_schema(
        "alarm-action-enabled-check",
        required=['transport', 'to', 'subject'],
        **Notify.schema
    )

    def perform_action(self, resource):
        notifier = AlarmNotify(
            data=self.data,
            manager=self.manager,
            log=log
        )
        notification_data = {
            'resources': [notifier.format_resource(r) for r in resources],
            'account': self.manager.config.account_id
        }
        notifier.send_notification(notification_data)
