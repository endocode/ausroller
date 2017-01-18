from ConfigParser import ConfigParser, NoOptionError
import json
import logging
import os
import sys


class CommandlineArgs(object):

    def __init__(self, arguments):
        self.args = arguments

    def get_value(self, key, default=None):
        try:
            value = self.args[key]
            if not value:
                value = default
        except KeyError:
            logging.debug(
                "Return default value {} for key {}".format(default, key))
            value = default

        return value


class Configuration(object):

    def __init__(self, arguments):
        args = CommandlineArgs(arguments)

        self.context = args.get_value('--context')

        self.deployment = {}
        self.deployment['name'] = args.get_value('--app')
        self.deployment['version'] = args.get_value('--version')

        self.commit_message = args.get_value('--message', "")
        self.is_dryrun = args.get_value('--dryrun')
        self.is_dryrun_but_templates = args.get_value('--dryruntemp')
        self.is_verbose = args.get_value('--verbose')

        config_file = args.get_value(
            "--config", os.path.join(os.path.expanduser("~"), ".ausroller.ini"))
        self.read_configfile(config_file)
        self.namespace = args.get_value("--namespace")

        # set paths and read in the json file with the secrets
        self.templates_path = os.path.join(self.repopath, 'templates')
        self.rollout_path = os.path.join(
            self.repopath, 'rollout', self.namespace)

        self.secretsfile = args.get_value("--secret", os.path.join(
            self.repopath, 'secrets', self.namespace, 'secret_vars.json'))
        try:
            self.secrets = read_variables(self.secretsfile)
        except Exception as e:
            logging.error("Cannot read secret variables from \"{}\"! [{}]".format(
                self.secretsfile, e))
            sys.exit(1)

        self.extravarsfile = args.get_value(
            "--extravars", os.path.join(self.repopath, 'manifests', self.namespace, 'extra_vars.json'))
        self.extra_variables = {}
        if os.path.exists(self.extravarsfile):
            try:
                self.extra_variables = read_variables(self.extravarsfile)
            except Exception as e:
                logging.error("Cannot read extra variables from \"{}\"! [{}]".format(
                    self.extravarsfile, e))
                sys.exit(1)

    def read_configfile(self, configfile):
        cp = ConfigParser()
        configuration = [(self.context, 'repopath'),
                         ('ausroller', 'kubectlpath')]
        try:
            logging.debug("Reading JSON file {}".format(configfile))
            cp.read(configfile)
        except:
            logging.error(
                "Cannot read configuration file \"{}\"!".format(configfile))
            sys.exit(1)

        for (section, option) in configuration:
            try:
                setattr(self, option, os.path.realpath(
                    cp.get(section, option)))
            except NoOptionError:
                logging.warn("Cannot read option '{}' from section '{}' in configuration file \"{}\"!".format(
                    option, section, configfile))
                setattr(self, option, None)


def _custom_json_pairs_hook(pairs):
    result = dict()
    for key, value in pairs:
        if key in result:
            raise KeyError("Duplicate definition of \"{}\" found.".format(key))
        else:
            result[key] = value
    return result


def read_variables(varfile):
    variables = {}
    logging.debug("Reading vars from {}".format(varfile))
    with open(varfile) as f:
        variables = json.load(f, object_pairs_hook=_custom_json_pairs_hook)
    return variables
