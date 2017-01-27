# encoding: utf-8
import argparse
import sys
import os
import json
import logging
import ConfigParser


class Configuration(object):

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-a', '--app', type=str, required=True,
                            help='Application to rollout')
        parser.add_argument('-v', '--version', type=str, required=True,
                            help='Version to rollout')
        parser.add_argument('-m', '--message', type=str, required=False,
                            default='', help='Optional commit message')
        parser.add_argument('-c', '--config', type=str, required=False,
                            default='',
                            help='Path to config file [$HOME/.ausroller.ini]')
        parser.add_argument('-d', '--dryrun', action='store_true',
                            help='Don\'t do anything just print')
        parser.add_argument('-D', '--dryruntemp', action='store_true',
                            help='Don\'t do apply but produce git commits')
        parser.add_argument('-V', '--verbose', action='store_true',
                            help='Be verbose; print debug messages')
        parser.add_argument('-n', '--namespace', type=str, required=True,
                            help='Which namespace to rollout on')
        parser.add_argument('-e', '--extravars', type=str, required=False,
                            help='Path to file holding extra variables')
        parser.add_argument('-s', '--secret', type=str, required=False,
                            help='Path to file holding [<repopath>/secrets/<namespace>/secret_vars.json]')
        args = parser.parse_args()

        self.app_name = args.app
        self.app_version = args.version
        self.namespace = args.namespace
        self.commit_message = args.message
        self.is_dryrun = args.dryrun
        self.is_dryrun_but_templates = args.dryruntemp
        self.is_verbose = args.verbose
        if self.is_verbose:
            self.log_level = logging.DEBUG
        else:
            self.log_level = logging.INFO
        self.configfile = args.config
        self.extravarsfile = args.extravars
        self.secretsfile = args.secret
        self.kubectlpath = None
        self.plugin_path = os.path.join(os.path.expanduser("~"),
                                        ".ausroller_plugins/")

    def read_config(self):
        home_dir = os.path.expanduser("~")
        # read config file
        if not self.configfile:
            self.configfile = os.path.join(home_dir, ".ausroller.ini")
        cp = ConfigParser.ConfigParser()
        try:
            cp.read(self.configfile)
        except:
            logging.error(
                "Cannot read configuration file \"{}\"!".format(self.configfile))
            sys.exit(1)

        try:
            self.repopath = os.path.realpath(cp.get('ausroller', 'repopath'))
        except:
            logging.error("Cannot read 'repopath' from configuration file \"{}\"!".format(
                self.configfile))
            sys.exit(1)

        # set paths and read in the json file with the secrets
        self.templates_path = os.path.join(self.repopath, 'templates')
        self.rollout_path = os.path.join(
            self.repopath, 'rollout', self.namespace)
        if not self.secretsfile:
            self.secretsfile = os.path.join(
                self.repopath, 'secrets', self.namespace, 'secret_vars.json')
        try:
            self.variables = self.read_variables(self.secretsfile)
        except KeyError as e:
            logging.error("Cannot read secret variables from \"{}\"! [{}]".format(self.secretsfile, e))
            sys.exit(1)

        self.extra_variables = {}
        if not self.extravarsfile:
            default_extravarsfile = os.path.join(
                self.repopath, 'manifests', self.namespace, 'extra_vars.json')
            if os.path.exists(default_extravarsfile):
                logging.info("found default extra vars file")
                self.extravarsfile = default_extravarsfile

        if self.extravarsfile:
            try:
                self.extra_variables = self.read_variables(self.extravarsfile)
            except KeyError as e:
                logging.error("Cannot read extra variables from \"{}\"! [{}]".format(self.extravarsfile, e))
                sys.exit(1)
        self.kubectl_cmd = 'kubectl --namespace={}'.format(self.namespace)

    def _custom_json_pairs_hook(self, pairs):
        ''' (list of pairs) -> dict
            Checks if in a given list of key-value pairs duplicate keys exists.
            >>> c = Configuration()
            >>> c._custom_json_pairs_hook([('key','value'),('key1','value')])
            {'key1': 'value', 'key': 'value'}
        '''
        result = dict()
        for key, value in pairs:
            if key in result:
                raise KeyError("Duplicate definition of \"{}\" found.".format(key))
            else:
                result[key] = value
        return result

    def read_variables(self, varfile):
        ''' (string) -> dict
            Reads from a given json filename and returns a dict.
        '''
        variables = {}
        logging.debug("Reading vars from {}".format(varfile))
        with open(varfile) as f:
            variables = json.load(f, object_pairs_hook=self._custom_json_pairs_hook)
        return variables
