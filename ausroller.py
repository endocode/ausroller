#!/usr/bin/env python2
# encoding: utf-8

import argparse
import sys
from jinja2 import Template, Environment, FileSystemLoader, exceptions
from gbp.git import repository
import subprocess
import ConfigParser
import os
import json
import shlex
import logging


RESOURCES = ["configmap", "deployment", "service"]

class Ausroller(object):

    def __init__(self):
        # read cli parameters
        self.parse_args()

        # make log level configurable
        logging.basicConfig(format='%(levelname)s:\t%(message)s', level=logging.DEBUG)

        home_dir = os.path.expanduser("~")
        # read config file
        if not self.configfile:
            self.configfile = os.path.join(home_dir, ".ausroller.ini")
        self.read_config()
        # set paths and read in the json file with the secrets
        self.templates_path = os.path.join(self.repopath, 'templates')
        self.rollout_path = os.path.join(self.repopath, 'rollout', self.tenant)
        self.variablesfile = os.path.join(home_dir, ".ausroller_secrets.json")
        self.read_variables()
        self.kubectl_cmd = 'kubectl --namespace={}'.format(self.tenant)

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
        parser.add_argument('-t', '--tenant', type=str, required=True,
                            help='Which tenant to rollout on')
        args = parser.parse_args()

        self.app_name = args.app
        self.app_version = args.version
        self.tenant = args.tenant
        self.commit_message = args.message
        self.is_dryrun = args.dryrun
        self.configfile = args.config

    def read_config(self):
        cp = ConfigParser.ConfigParser()
        try:
            cp.read(self.configfile)
        except:
            logging.error(
                "Cannot read configuration file \"{}\"!".format(self.configfile))
            sys.exit(1)

        try:
            self.repopath = cp.get('ausroller', 'repopath')
        except:
            logging.error("Cannot read 'repopath' from configuration file \"{}\"!".format(
                self.configfile))
            sys.exit(1)

    def read_variables(self):
        self.variables = {}

        try:
            with open(self.variablesfile) as f:
                self.variables = json.load(f)
        except:
            logging.error("Cannot read variables from \"{}\"!".format(self.variablesfile))
            sys.exit(1)

    def render_template(self, resource):
        '''
            app_name and resource type
        '''
        env = Environment(
            loader=FileSystemLoader(os.path.join(self.templates_path, resource + 's')))
        try:
            template = env.get_template(
                "{}-{}.tpl.yaml".format(self.app_name, resource))
        except exceptions.TemplateNotFound as e:
            logging.error("Template \"{}\" not found.".format(e))
            sys.exit(1)
        return template.render(self.variables, app_version=self.app_version)

    def prepare_rollout(self):
        logging.info("Preparing rollout of {} in version {}".format(
            self.app_name, self.app_version))
        result_map = {}
        for resource in RESOURCES:
            result_map[resource] = self.render_template(resource)
        self.write_yamls(result_map)

    def write_yamls(self, resources):
        repo = repository.GitRepository(self.repopath)
        (repo_is_clean, repo_msg) = repo.is_clean()
        if not repo_is_clean:
            logging.error("Git repo is not in a clean state! Exiting..")
            sys.exit(1)

        files_to_commit = []
        for resource in resources.keys():
            outfile = os.path.join(self.rollout_path, "{}s".format(
                resource), "{}-{}.yaml".format(self.app_name, resource))
            with open(outfile, 'w') as out:
                out.write(resources[resource])
                # flush & sync to avoid git adding an empty file
                out.flush()
                os.fsync(out)
                repo.add_files(outfile)
                files_to_commit.append(outfile)
        self.commit_rollout(files_to_commit)

    def commit_rollout(self, files_to_commit):
        repo = repository.GitRepository(self.repopath)
        (repo_is_clean, repo_msg) = repo.is_clean()

        if not repo_is_clean:
            if self.is_dryrun:
                logging.debug("Dry run: skipping commit")
                return

            repo.commit_files(files_to_commit,
                              "Created rollout for {} with version {}\n\n{}".format(
                                  self.app_name,
                                   self.app_version,
                                   self.commit_message))
            logging.info(repo.show(self.rollout_path))
        else:
            logging.warn(
                "Definition of rollout already exists. Nothing changed.")

    def rollout(self):
        for resource in RESOURCES:
            try:
                cmd = shlex.split(
                    "{} get {} -oname".format(self.kubectl_cmd, resource + "s"))
                out = subprocess.check_output(cmd)
                resource_exists = False
                for res in out.split('\n'):
                    if res.startswith(resource + '/%s-%s' %
                                      (self.app_name, resource)):
                        logging.debug("Found: {}".format(res))
                        cmd = shlex.split(
                            "{} get {}".format(self.kubectl_cmd, res))
                        logging.debug(subprocess.check_output(cmd))
                        resource_exists = True
                if not resource_exists:
                    logging.warn("No {} of \"{}\" found.".format(
                        resource, self.app_name))
            except subprocess.CalledProcessError as e:
                logging.error("Something went wrong while calling kubectl.\n{}".format(e))
                sys.exit(1)

            if self.is_dryrun:
                if resource_exists:
                    logging.info("Dry run: Skipping apply")
                else:
                    logging.info("Dry run: Skipping create")
                return

            if not resource_exists:
                # No resource for app_name found. Start it.
                cmd = shlex.split("{} create -f {}".format(self.kubectl_cmd, os.path.join(
                    self.rollout_path, "{}s".format(resource), "{}-{}.yaml".format(self.app_name, resource))))
                try:
                    create_out = subprocess.check_output(cmd)
                    logging.info("Created {} for \"{}\"".format(
                        resource, self.app_name))
                except:
                    logging.info("Creating {} failed:".format(resource))
                    raise
            else:
                # resource for app_name exists. Let's update!
                cmd = shlex.split("{} apply -f {}".format(self.kubectl_cmd, os.path.join(
                    self.rollout_path, "{}s".format(resource), "{}-{}.yaml".format(self.app_name, resource))))
                try:
                    update_out = subprocess.check_output(cmd)
                except:
                    logging.error("Applying the {} failed:".format(resource))
                    raise


def main():
    a = Ausroller()
    a.prepare_rollout()
    a.rollout()

    logging.debug(a.__dict__)

if __name__ == '__main__':
    main()
