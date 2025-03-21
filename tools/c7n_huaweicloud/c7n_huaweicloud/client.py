# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import sys

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import *
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion
from huaweicloudsdkevs.v2 import *
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion
from huaweicloudsdkvpc.v2 import *
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion
from huaweicloudsdktms.v1 import *
from huaweicloudsdktms.v1.region.tms_region import TmsRegion
from huaweicloudsdkces.v1 import CesClient as CesV1Client
from huaweicloudsdkces.v2 import CesClient as CesV2Client, ListAlarmRulesRequest
from huaweicloudsdkces.v1.region.ces_region import CesRegion as CesV1Region
from huaweicloudsdkces.v2.region.ces_region import CesRegion as CesV2Region

log = logging.getLogger('custodian.huaweicloud.client')


class Session:
    """Session"""

    def __init__(self, options=None):
        self.region = os.getenv('HUAWEI_DEFAULT_REGION')
        if not self.region:
            log.error('No default region set. Specify a default via HUAWEI_DEFAULT_REGION')
            sys.exit(1)

        self.ak = os.getenv('HUAWEI_ACCESS_KEY_ID')
        if self.ak is None:
            log.error('No access key id set. Specify a default via HUAWEI_ACCESS_KEY_ID')
            sys.exit(1)

        self.sk = os.getenv('HUAWEI_SECRET_ACCESS_KEY')
        if self.sk is None:
            log.error('No secret access key set. Specify a default via HUAWEI_SECRET_ACCESS_KEY')
            sys.exit(1)

    def client(self, service):
        credentials = BasicCredentials(self.ak, self.sk)
        if service == 'vpc':
            client = VpcClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(VpcRegion.value_of(self.region)) \
                .build()
        elif service == 'ecs':
            client = EcsClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(EcsRegion.value_of(self.region)) \
                .build()
        elif service == 'evs':
            client = EvsClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(EvsRegion.value_of(self.region)) \
                .build()
        elif service == 'tms':
            client = TmsClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(TmsRegion.value_of(self.region)) \
                .build()
        elif service == 'cesv1':
            client = CesV1Client.new_builder() \
                .with_credentials(credentials) \
                .with_region(CesV1Region.value_of(self.region)) \
                .build()
        elif service == 'cesv2':
            client = CesV2Client.new_builder() \
                .with_credentials(credentials) \
                .with_region(CesV2Region.value_of(self.region)) \
                .build()

        return client

    def request(self, service):
        if service == 'vpc':
            request = ListVpcsRequest()
        elif service == 'evs':
            request = ListVolumesRequest()
        elif service == 'cesv1':
            request = ListAlarmRulesRequest()
        elif service == 'cesv2':
            request = ListAlarmRulesRequest()

        return request
