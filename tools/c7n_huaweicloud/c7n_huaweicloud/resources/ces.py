# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import logging
import smtplib

from huaweicloudsdkces.v1 import *
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkces.v2 import *

from c7n.actions import Notify, ActionRegistry
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

@Alarm.action_registry.register("delete_by_id")
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
              - delete_by_id
    """

    schema = type_schema("delete_by_id")

    def perform_action(self, resource):
        response = None
        client = self.manager.get_client()
        request = BatchDeleteAlarmRulesRequest()
        request.body = BatchDeleteAlarmsRequestBody(alarm_ids=[resource["id"]])
        try:
            response = client.batch_delete_alarm_rules(request)
            log.info(f"Deleted alarm {response}")

        except exceptions.ClientRequestException as e:
            log.error(f"Delete failed: {e.error_msg}")
        return response


@Alarm.action_registry.register("ces-alarm-have-smn")
class AlarmUpdateNotification(HuaweiCloudBaseAction):
    """Update CES Alarm notification settings.

    :Example:

    .. code-block:: yaml

        policies:
          - name: enable-smn-notification
            resource: huaweicloud.alarm
            filters:
              - type: value
                key: alarm_action_enabled
                value: false
            actions:
              - type: ces-alarm-have-smn
                parameters:
                  action_type: "notification"
                  notification_list:
                    - "urn:smn:cn-north-4:xxxxxxxxxxx:ces_notification_group_xxxxx"

    """

    schema = type_schema(
        "ces-alarm-have-smn",
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
                        "enum": ["notification", "autoscaling"]
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


@Alarm.action_registry.register("alarm-enabled-check-and-start")
class AlarmUpdateEnabled(HuaweiCloudBaseAction):
    """Update CES Alarm all start.

    :Example:

    .. code-block:: yaml

        policies:
          - name: enable-all-alarm-rule-started
            resource: huaweicloud.alarm
            filters:
              - type: value
                key: enabled
                value: false
            actions:
              - type: alarm-enabled-check-and-start

    """

    schema = type_schema("alarm-enabled-check-and-start")

    def perform_action(self, resource):
        response = None
        client = self.manager.get_client()
        request = BatchEnableAlarmRulesRequest()
        list_alarm_ids = [resource["id"]]
        request.body = BatchEnableAlarmsRequestBody(
            alarm_enabled=True,
            alarm_ids=list_alarm_ids
        )
        try:
            response = client.batch_enable_alarm_rules(request)
            log.info(f"Batch start alarm {response}")
        except exceptions.ClientRequestException as e:
            log.error(f"Batch start alarm failed: {e.error_msg}")
        return response


@Alarm.action_registry.register("alarm-vpc-check")
class AlarmUpdateEnabled(HuaweiCloudBaseAction):
    """Check CES isn't configured VPC change alarm rule.

    :Example:

    .. code-block:: yaml

policies:
  - name: enable-all-alarm-rule-started
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
      - type: alarm-vpc-check
        parameters:
          action_type: "notification"
          notification_list:
            - "urn:smn:cn-north-4:e196f2790965422f80502748f4d58649:CES_notification_group_kNrnzmm0J"

    """

    schema = type_schema(
        "alarm-vpc-check",
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
                        "enum": ["notification", "autoscaling"]
                    }
                }
            }
        }
    )

    def process(self, resource):
        params = self.data.get('parameters', {})
        action_type = params.get('action_type', 'notification')
        # 告警更新切换到V1接口
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


# @Alarm.action_registry.register('notify')
# class AlarmNotify(Notify):
#     schema = type_schema('notify', **Notify.schema)
#
#     def get_resources(self, ids):
#         client = self.manager.get_client()
#         return client.list_alarm_rules().alarms
#
#     def format_resource(self, resource):
#         return {
#             'alarm_id': resource['alarm_id'],
#             'name': resource['alarm_name'],
#             'status': 'Enabled' if resource['alarm_enabled'] else 'Disabled'
#         }
#
#     def send_notification(self, notification_data):
#         """重写通知发送逻辑"""
#         # 1. 增强数据获取
#         resources = self.get_resource_data(notification_data['resources'])
#
#         # 2. 华为云元数据注入
#         notification_data.update({
#             'region_name': self.manager.config.region,
#             'project_id': self.manager.config.project_id,
#             'huawei_console_url': f"https://console.huaweicloud.com/ces/?region={self.manager.config.region}#/alarmManagement"
#         })
#
#         # 3. 连接池管理
#         with self.get_smtp_connection() as server:
#             for resource_batch in self.chunk_resources(resources, batch_size=50):
#                 # 4. 多语言模板选择
#                 template = self.select_template(resource_batch)
#                 # 5. 渲染并发送
#                 self.send_batch(
#                     server=server,
#                     template=template,
#                     batch_data=resource_batch,
#                     notification_data=notification_data
#                 )
#
#     def get_smtp_connection(self):
#         """复用SMTP连接（支持TLS/SSL）"""
#         config = self.data['transport']
#         if config.get('ssl'):
#             server = smtplib.SMTP_SSL(config['host'], config['port'])
#         else:
#             server = smtplib.SMTP(config['host'], config['port'])
#             if config.get('starttls'):
#                 server.starttls()
#         server.login(config['username'], config['password'])
#         return server
#
#     def chunk_resources(self, resources, batch_size):
#         """分批处理资源（避免单次邮件过大）"""
#         for i in range(0, len(resources), batch_size):
#             yield resources[i:i + batch_size]
#
#     def select_template(self, resources):
#         """根据资源状态选择模板"""
#         if any(r['alarm_level'] == 'critical' for r in resources):
#             return 'critical-alert.html'
#         return self.data.get('template', 'default.html')
#
#
# @Alarm.action_registry.register("alarm-action-enabled-check")
# class AlarmActionEnabledCheck(HuaweiCloudBaseAction):
#     """alarm-action-enabled-check.
#
#     :Example:
#
#     .. code-block:: yaml
#
#         policies:
#           - name: alarm-action-enabled-check
#             resource: huaweicloud.alarm
#             flters:
#               - type: value
#                 key: alarm_enabled
#                 value: false
#             actions:
#               - type: notify
#                 to:
#                   - 1974365584@qq.com
#                 subject: "Unverified CES Alarm"
#                 message: "CES alarm {resource.alarm_id} is not started. Please verify th configuration."
#                 template: default.html
#                 transport:
#                   type: smtp
#                   host: smtp.qq.com    # SMTP 服务器地址
#                   port: 587            # TLS 加密端口qthjekzidosugdja
#                   username: "1974365584@qq.com"
#                   password: "qthjekzidosugdja"
#                   from: "cloud-alerts@huawei.com"
#                   starttls: true
#         code-block:: html
#         <html>
#             <body>
#                 <h2>CES告警规则状态异常通知</h2>
#                     <p>发现以下告警规则状态未开启：</p>
#                         <ul>
#                             <li>告警规则ID: {{ resource.alarm_id }}</li>
#                         </ul>
#                     <p>请及时处理！</p>
#             </body>
#         </html>
#     """
#
#     schema = type_schema(
#         "alarm-action-enabled-check",
#         required=['transport', 'to', 'subject'],
#         ** Notify.schema
#     )
#
#     def perform_action(self, resource):
#         notifier = AlarmNotify(
#             data=self.data,
#             manager=self.manager,
#             log=log
#         )
#         notification_data = {
#             'resources': [notifier.format_resource(r) for r in resources],
#             'account': self.manager.config.account_id
#         }
#         notifier.send_notification(notification_data)
