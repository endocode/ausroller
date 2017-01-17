#!/usr/bin/env python2
# encoding: utf-8

"""Ausroller

Usage:
    ausroller (-h | --help)
    ausroller -n <namespace> [-c <config>] [-e <extra_vars>] [-s <secret_vars>] [--dryruntemp | --dryrun] [--verbose] (-a <app_name> -v <app_version>)

Options:
      -c --config <config>          Path to config file [defaults to $HOME/.ausroller.ini]
      -a --app <app_name>           Name of an app to roll out
      -v --version <app_version>    Version of the app to roll out
      -d --dryrun                   Dry run: just print but don't write nor apply
      -D --dryruntemp               Dry run: run template engine but do not commit nor apply
      -n --namespace <namespace>    Specify the namespace to rollout on
      -e --extravars <extra_vars>   Path to file holding extra variables
      -s --secret <secret_vars>     Path to file holding secret variables [defaults to <repopath>/secrets/<namespace>/secret_vars.json]
      -h --help                     Show this screen
      -V --verbose                  Be verbose; print debug messages

"""

import sys
from jinja2 import Template, Environment, FileSystemLoader, exceptions
from gbp.git import repository
import subprocess
import ConfigParser
import os
import json
import shlex
import logging
from docopt import docopt
from config import Configuration

RESOURCES = ["configmap", "deployment", "secrets",
             "service", "pod", "replicationcontroller"]

class Ausroller(object):
    def __init__(self, args):
        self.config = Configuration(args)

    def render_template(self, resource):
        '''
            app_name and resource type
        '''
        env = Environment(
            loader=FileSystemLoader(os.path.join(self.config.templates_path, resource + 's')))
        try:
            template = env.get_template(
                "{}-{}.tpl.yaml".format(self.config.deployment['name'], resource))
        except exceptions.TemplateNotFound as e:
            logging.debug("Template \"{}\" not found.".format(e))
            return
        return template.render(self.config.secrets, app_version=self.config.deployment["version"], namespace=self.config.namespace, **self.config.extra_variables)

    def prepare_rollout(self):
        logging.info("Preparing rollout of {} in version {}".format(
            self.config.deployment['name'], self.config.deployment['version']))
        result_map = {}
        for resource in RESOURCES:
            rendered_template = self.render_template(resource)
            if rendered_template:
                result_map[resource] = self.render_template(resource)
        return self.write_yamls(result_map)

    def write_yamls(self, resources):
        repo = repository.GitRepository(self.config.repopath)
        (repo_is_clean, repo_msg) = repo.is_clean()
        if not repo_is_clean:
            logging.error("Git repo is not in a clean state! Exiting..")
            sys.exit(1)

        if not self.config.is_dryrun:
            files_to_commit = []
            for resource in resources.keys():
                # make sure path exists
                outdir = os.path.join(
                    self.config.rollout_path, "{}s".format(resource))
                if not os.path.exists(outdir):
                    try:
                        os.makedirs(outdir)
                    except OSError:
                        # this is still not completely safe as we could run
                        # into a (next) race-condition, but it is suitable for
                        # out needs
                        if not os.path.exists(outdir):
                            logging.error(
                                "Can not create rollout directory for resource \"{}\"".format(resource))

                outfile = os.path.join(
                    outdir, "{}-{}.yaml".format(self.config.deployment['name'], resource))
                with open(outfile, 'w') as out:
                    out.write(resources[resource])
                    # flush & sync to avoid git adding an empty file
                    out.flush()
                    os.fsync(out)
                    repo.add_files(outfile)
                    files_to_commit.append(outfile)
            self.commit_rollout(files_to_commit)
        else:
            logging.info(
                "Dry-run: skip writing files for {}".format(resources.keys()))
        return resources.keys()

    def commit_rollout(self, files_to_commit):
        repo = repository.GitRepository(self.config.repopath)
        (repo_is_clean, repo_msg) = repo.is_clean()

        if not repo_is_clean:
            if self.config.is_dryrun or self.config.is_dryrun_but_templates:
                logging.debug("Dry run: skipping commit")
                return

            repo.commit_files(files_to_commit,
                              "[{}] Created rollout for {} with version {}\n\n{}".format(
                                  self.config.namespace,
                                  self.config.deployment['name'],
                                  self.config.deployment['version'],
                                  self.config.commit_message))
            logging.debug("Commited changes:\n{}".format(
                repo.show(self.config.rollout_path)))
        else:
            logging.warn(
                "Definition of rollout already exists. Nothing changed.")

    def rollout(self, resources):
        if self.config.is_dryrun or self.config.is_dryrun_but_templates:
            logging.info("Dry-run: skip applying changes to Kubernetes")
        else:
            logging.info("Rolling out resources {}".format(resources))
        for resource in resources:
            cmd = shlex.split("{} apply -f {}".format(self.config.kubectl_cmd, os.path.join(
                self.config.rollout_path, "{}s".format(resource), "{}-{}.yaml".format(self.config.deployment['name'], resource))))
            if self.config.is_dryrun or self.config.is_dryrun_but_templates:
                logging.debug("Skipping '{}'".format(" ".join(cmd)))
                continue
            else:
                logging.debug("Running '{}'".format(" ".join(cmd)))

            try:
                update_out = subprocess.check_output(cmd)
            except:
                logging.error("Applying the {} failed:".format(resource))
                sys.exit(1)


def main():
    arguments = docopt(__doc__)
    # configure logging
    log_level = logging.INFO
    if arguments["--verbose"]:
        log_level = logging.DEBUG
    logging.basicConfig(
        format='%(levelname)s: %(message)s', level=log_level)
    logging.debug("Commandline arguments:\n{}".format(arguments))
    # repair gbp logging
    gbplogger = logging.getLogger("gbp")
    gbplogger.propagate = False

    a = Ausroller(arguments)
    resources = a.prepare_rollout()
    a.rollout(resources)

if __name__ == '__main__':
    main()
