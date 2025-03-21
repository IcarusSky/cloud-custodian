# coding: utf-8

import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2.region.ces_region import CesRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkces.v2 import *

if __name__ == "__main__":
    # The AK and SK used for authentication are hard-coded or stored in plaintext, which has great security risks. It is recommended that the AK and SK be stored in ciphertext in configuration files or environment variables and decrypted during use to ensure security.
    # In this example, AK and SK are stored in environment variables for authentication. Before running this example, set environment variables CLOUD_SDK_AK and CLOUD_SDK_SK in the local environment
    ak = os.environ["CLOUD_SDK_AK"]
    sk = os.environ["CLOUD_SDK_SK"]

    credentials = BasicCredentials(ak, sk)

    client = CesClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(CesRegion.value_of("cn-north-4")) \
        .build()

    try:
        request = CreateAlarmRulesRequest()
        listNotificationListOkNotifications = [
            "urn:smn:cn-north-4:e196f2790965422f80502748f4d58649:CES_notification_group_kNrnzmm0J"
        ]
        listOkNotificationsbody = [
            Notification(
                type="notification",
                notification_list=listNotificationListOkNotifications
            )
        ]
        listNotificationListAlarmNotifications = [
            "urn:smn:cn-north-4:e196f2790965422f80502748f4d58649:CES_notification_group_kNrnzmm0J"
        ]
        listAlarmNotificationsbody = [
            Notification(
                type="notification",
                notification_list=listNotificationListAlarmNotifications
            )
        ]
        listPoliciesbody = [
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
            ok_notifications=listOkNotificationsbody,
            alarm_notifications=listAlarmNotificationsbody,
            type="EVENT.SYS",
            policies=listPoliciesbody,
            namespace="SYS.VPC",
            description="alarm-vpc-change",
            name="alarm-vpc-change"
        )
        response = client.create_alarm_rules(request)
        print(response)
    except exceptions.ClientRequestException as e:
        print(e.status_code)
        print(e.request_id)
        print(e.error_code)
        print(e.error_msg)
