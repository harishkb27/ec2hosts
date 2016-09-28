import os
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

import ec2hosts
from ec2hosts import ConfigLoader, EC2Connections, EC2Hosts, configure


class EC2ConnectionsTests(unittest.TestCase):
    def setUp(self):
        config_file_path = os.path.join(os.path.dirname(__file__), 'test-config.yaml')
        self.config = ConfigLoader(config_file_path).load()

    def testConfigLoader(self):
        self.assertEqual(self.config.aws_access_key, 'AWSTESTACCESSKEY')
        self.assertEqual(self.config.aws_secret_access_key, 'AWSTESTSECRETACCESSKEY')
        self.assertListEqual(self.config.aws_regions, ['eu-west-1', 'us-east-1'])
        self.assertEqual(self.config.hosts_file, './tests/test-hosts')

    def testEC2Connections(self):
        ec2connections = EC2Connections(self.config)
        self.assertEqual(len(ec2connections.make()), 2)


class EC2HostsTests(unittest.TestCase):
    def setUp(self):
        config_file_path = os.path.join(os.path.dirname(__file__), 'test-config.yaml')
        self.config = ConfigLoader(config_file_path).load()
        ec2connections = EC2Connections(self.config)
        self.ec2hosts = EC2Hosts(ec2connections, self.config)
        self.ec2hosts.instances = MagicMock(
            return_value=[{'tags': {'Name': 'server' + i}, 'ip_address': '10.0.0.' + i, 'az': '1a'} for i in
                          ('1', '2')])
        self.expected_hosts_filestream = ('10.0.0.1 server1\n'
                                          '10.0.0.2 server2\n'
                                          '10.0.0.3 server3\n\n')

    def testLoadIPTags(self):
        self.ec2hosts.load_ip_tags()
        self.assertDictEqual(self.ec2hosts.ip_tags, {'server1': '10.0.0.1', 'server2': '10.0.0.2'})

    def testLoadHostsData(self):
        self.ec2hosts.load_hosts_data()
        self.assertListEqual(self.ec2hosts.hosts_data,
                             [{'ip': '10.0.1.1', 'record': 'server1'}, {'ip': '10.0.0.2', 'record': 'server2'},
                              {'ip': '10.0.0.3', 'record': 'server3'}])

    def testUpdateHostsData(self):
        self.ec2hosts.update_hosts_data()
        self.assertListEqual(self.ec2hosts.hosts_data,
                             [{'ip': '10.0.0.1', 'record': 'server1'}, {'ip': '10.0.0.2', 'record': 'server2'},
                              {'ip': '10.0.0.3', 'record': 'server3'}])

    @patch('sys.stdout', new_callable=StringIO)
    def testShow(self, mock_stdout):
        self.ec2hosts.show()
        self.assertEqual(mock_stdout.getvalue(), self.expected_hosts_filestream)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.config_test_file_path = os.path.join(os.path.dirname(__file__), 'test-config.yaml')
        with open(self.config_test_file_path, 'r') as f:
            self.original_content = f.read()

    def testConfigure(self):
        expectation = ('aws_access_key: awstestaccesskey\n'
                       'aws_regions: [eu-west-1]\n'
                       'aws_secret_access_key: awstestsecretaccesskey\n'
                       'hosts_file: /tmp/testhosts\n')
        with patch('builtins.input',
                   side_effect=['/tmp/testhosts', 'awstestaccesskey', 'awstestsecretaccesskey', 'eu-west-1', 'Y']):
            ec2hosts.CONFIG_FILE_PATH = self.config_test_file_path
            configure()
            with open(ec2hosts.CONFIG_FILE_PATH, 'r') as f:
                self.assertEqual(f.read(), expectation)

    def tearDown(self):
        with open(self.config_test_file_path, 'w') as f:
            f.write(self.original_content)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
