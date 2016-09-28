import os
import yaml
from boto import ec2
from io import StringIO
from optparse import OptionParser
from collections import namedtuple

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')


class ConfigLoader(object):
    Config = namedtuple('Config', ['aws_access_key', 'aws_secret_access_key', 'aws_regions', 'hosts_file'])

    def __init__(self, path=CONFIG_FILE_PATH):
        with open(path) as f:
            self.config_file = f.read()

    def load(self):
        config_dict = yaml.load(self.config_file)
        return self.Config(
            config_dict['aws_access_key'],
            config_dict['aws_secret_access_key'],
            config_dict['aws_regions'],
            config_dict['hosts_file']
        )


class EC2Connections(object):
    def __init__(self, config):
        self.config = config
        self.connections = []

    def make(self):
        for region in self.config.aws_regions:
            conn = ec2.connect_to_region(region, aws_access_key_id=self.config.aws_access_key,
                                         aws_secret_access_key=self.config.aws_secret_access_key)
            if not conn:
                print('Invalid region - %s' % region)
            else:
                self.connections.append(conn)
        return self.connections


class EC2Hosts(object):
    def __init__(self, ec2connections, config):
        self.config = config
        self.ec2_connections = ec2connections
        self.ip_tags = {}
        self.hosts_data = []

    def instances(self):
        return []

    def load_ip_tags(self):
        [self.ip_tags.update({idata['tags']['Name']: idata['ip_address']}) for idata in self.instances()]

    def load_hosts_data(self):
        with open(self.config.hosts_file, 'r') as f:
            self.hosts_data = list(
                map(lambda x: {'ip': x.split(' ', 1)[0], 'record': x.split(' ', 1)[1].strip()}, f.readlines())
            )

    def update_hosts_data(self):
        self.ip_tags or self.load_ip_tags()
        self.hosts_data or self.load_hosts_data()
        for hosts_entry in self.hosts_data:
            try:
                hosts_entry['ip'] = self.ip_tags[hosts_entry['record']] if hosts_entry['ip'] != self.ip_tags[
                    hosts_entry['record']] else hosts_entry['ip']
                del self.ip_tags[hosts_entry['record']]
            except KeyError:
                pass
        [self.hosts_data.append({'ip': v, 'record': k}) for k, v in self.ip_tags.items() if v]

    def show(self):
        self.update_hosts_data()
        output = StringIO()
        [output.write('{0} {1}\n'.format(i['ip'], i['record'])) for i in self.hosts_data]
        print(output.getvalue())


class InteractivePrompter(object):
    def mask(self, value):
        return value[:4] + '*' * 4 + value[-4:]

    def get_value(self, current_value, prompt_text='', sensitive=False):
        response = input("{} [{}]: ".format(prompt_text, self.mask(current_value) if sensitive else current_value))
        if not response:
            response = current_value
        return response


def configure():
    config = ConfigLoader().load()
    prompter = InteractivePrompter()
    hosts_file_msg = 'full path to hosts file'
    aws_access_key_msg = 'aws access key'
    aws_secret_key_msg = 'aws secret access key'
    aws_regions_msg = 'aws regions separated by space'

    updated_config = dict()
    try:
        updated_config['hosts_file'] = prompter.get_value(config.hosts_file, hosts_file_msg)
        updated_config['aws_access_key'] = prompter.get_value(config.aws_access_key, aws_access_key_msg, True)
        updated_config['aws_secret_access_key'] = prompter.get_value(config.aws_secret_access_key, aws_secret_key_msg,
                                                                     True)
        updated_config['aws_regions'] = prompter.get_value(" ".join(config.aws_regions), aws_regions_msg).split(" ")
    except KeyboardInterrupt:
        print("Configuration aborted!")
        exit()

    confirmation = prompter.get_value('Y', "Save configuration?")
    if confirmation.upper().startswith('Y'):
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write(yaml.dump(updated_config))


def parse_args():
    parser = OptionParser()
    parser.add_option("-c", "--configure", action="store_true", help="configure the tool interactively")
    options, args = parser.parse_args()
    return options


def main():
    options = parse_args()
    if options.configure:
        configure()
        exit(0)
    config = ConfigLoader().load()
    ec2hosts = EC2Hosts(ec2connections=EC2Connections(config), config=config)
    ec2hosts.show()


if __name__ == '__main__':
    main()
