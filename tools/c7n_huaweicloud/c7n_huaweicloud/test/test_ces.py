# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
from huaweicloud_common import BaseTest


class AlarmTest(BaseTest):

    def test_alarm_query(self):
        factory = self.replay_flight_data('ces_alarm_query')
        p = self.load_policy({
             'name': 'all-volumes',
             'resource': 'huaweicloud.alarm'},
            session_factory=factory)
        resources = p.run()
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0]['alarm_id'], "al17427965140272BWJEvgrp")