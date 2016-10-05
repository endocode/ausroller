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


class Ausroller(object):

    def __init__(self):
        # read cli parameters
        self.parse_args()
        home_dir = os.path.expanduser("~")
        # read config file
        if not self.configfile:
            self.configfile = os.path.join(home_dir, ".ausroller.ini")
        self.read_config()
        # set paths and read in the json file with the secrets
        self.templates_path = os.path.join(self.repopath, 'templates')
        self.rollout_path = os.path.join(self.repopath, 'rollout')
        self.variablesfile = os.path.join(home_dir, ".ausroller_secrets.json")
        self.read_variables()
        self.kubectl_cmd = ['kubectl',
                            '--namespace=%s' % self.tenant]

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
            print "Cannot read from configfile \"%s\"!" % self.configfile
            sys.exit(1)

        try:
            self.repopath = cp.get('ausroller', 'repopath')
        except:
            print "Cannot read 'repopath' from configfile \"%s\"!"\
                  % self.configfile
            sys.exit(1)

    def read_variables(self):
        self.variables = {}

        try:
            with open(self.variablesfile) as f:
                self.variables = json.load(f)
        except:
            print "Cannot read from variablesfile \"%s\"!" % self.variablesfile
            sys.exit(1)

    def render_template(self, resource):
        '''
            app_name and resource type
        '''
        env = Environment(
            loader=FileSystemLoader(os.path.join(self.templates_path, resource + 's')))
        try:
            template = env.get_template(self.app_name + '-' +
                                        resource + '.tpl.yaml')
        except exceptions.TemplateNotFound as e:
            print "Template \"%s\" not found." % e
            sys.exit(1)
        return template.render(self.variables, app_version=self.app_version)

    def prepare_rollout(self):
        print "Rollout %s in version %s" % (self.app_name, self.app_version)
        d_yaml = self.render_template('deployment')
        c_yaml = self.render_template('configmap')
        self.write_yamls({'deployment': d_yaml, 'configmap': c_yaml})

    def write_yamls(self, resources):
        repo = repository.GitRepository(self.repopath)
        (repo_is_clean, repo_msg) = repo.is_clean()
        if not repo_is_clean:
            print "Git repo is not in a clean state! Exiting.."
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
            repo.commit_files(files_to_commit,
                              "Created rollout for %s with version %s\n\n%s" %
                              (self.app_name,
                               self.app_version,
                               self.commit_message))
            print repo.show(self.rollout_path)
        else:
            print "Definition of rollout already exists. Nothing changed."

    def rollout(self):
        for resource in ['configmap', 'deployment']:
            try:
                cmd = self.kubectl_cmd + ['get', resource + 's', '-oname']
                out = subprocess.check_output(cmd)
                resource_exists = False
                for res in out.split('\n'):
                    if res.startswith(resource + '/%s-%s' %
                                      (self.app_name, resource)):
                        print "Found: %s" % res
                        cmd = self.kubectl_cmd + ['get', res]
                        print subprocess.check_output(cmd)
                        resource_exists = True
                if not resource_exists:
                    print "No %s of \"%s\" found." % (resource,
                                                      self.app_name)
            except subprocess.CalledProcessError as e:
                print "Something went wrong while calling kubectl."
                print e
                sys.exit(1)

            if not resource_exists:
                # No resource for app_name found. Start it.
                cmd = self.kubectl_cmd + ['create', '-f', self.rollout_path +
                                          '%ss/%s-%s.yaml' %
                                          (resource, self.app_name, resource)]
                try:
                    create_out = subprocess.check_output(cmd)
                    print "Created %s for \"%s\"" % (resource, self.app_name)
                except:
                    print "Creating %s failed:" % resource
                    raise
            else:
                # resource for app_name existing. Let's update!
                cmd = self.kubectl_cmd + ['apply', '-f', self.rollout_path +
                                          '%ss/%s-%s.yaml' % (resource,
                                                              self.app_name,
                                                              resource)]
                try:
                    update_out = subprocess.check_output(cmd)
                except:
                    print "Applying the %s failed:" % resource
                    raise


def main():
    a = Ausroller()
    a.prepare_rollout()
    a.rollout()

    print a.__dict__

if __name__ == '__main__':
    main()
