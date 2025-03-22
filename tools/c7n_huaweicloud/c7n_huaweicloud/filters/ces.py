# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

from c7n.filters import Filter
from c7n.utils import type_schema

def register_tms_filters(filters):
    filters.register('alarm-namespace-metric', AlarmNameSpaceAndMetricFilter)

class AlarmNameSpaceAndMetricFilter(Filter):
    schema = type_schema(
        'alarm-namespace-metric',
        required=['namespaces', 'metric_names'],
        namespaces={'type': 'array', 'items': {'type': 'string'}},  # 目标namespace列表
        metric_names={'type': 'array', 'items': {'type': 'string'}}  # 目标metric_name列表
    )

    def process(self, resources, event=None):
        matched = []
        for alarm in resources:
            # check namespace filter
            namespace_match = alarm.get('namespace') in self.data['namespaces']

            # check policies.metric_name filter
            policies = alarm.get('policies', [])
            metric_match = any(
                policy.get('metric_name') in self.data['metric_names']
                for policy in policies
            )

            if namespace_match and metric_match:
                matched.append(alarm)
        return matched