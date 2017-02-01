# encoding: utf-8

from jinja2 import Template, Environment, FileSystemLoader, exceptions
from gbp.git import repository
from kube import KubeCtl, KubeCtlException
import subprocess
import shlex
import logging
import os
import sys


RESOURCES = ["configmap", "deployment", "secrets",
             "service", "pod", "replicationcontroller"]


class Ausroller(object):

    def __init__(self, configurator):
        self.c = configurator
        self.kubectl = KubeCtl(self.c.context, self.c.namespace, self.c.kubectlpath,
                               (self.c.is_dryrun or
                                self.c.is_dryrun_but_templates))

    def render_template(self, resource):
        env = Environment(
            loader=FileSystemLoader(os.path.join(self.c.templates_path, resource + 's')))
        try:
            template = env.get_template(
                "{}-{}.tpl.yaml".format(self.c.app_name, resource))
        except exceptions.TemplateNotFound as e:
            logging.debug("Template \"{}\" not found.".format(e))
            return
        return template.render(self.c.variables, app_version=self.c.app_version, namespace=self.c.namespace, **self.c.extra_variables)

    def prepare_k8s_resources(self):
        logging.info("Preparing k8s resources of {} in version {}".format(
            self.c.app_name, self.c.app_version))
        result_map = {}
        for resource in RESOURCES:
            rendered_template = self.render_template(resource)
            if rendered_template:
                result_map[resource] = self.render_template(resource)
        return result_map

    def write_k8s_resources(self, resources):
        repo = repository.GitRepository(self.c.repopath)
        (repo_is_clean, repo_msg) = repo.is_clean()
        if not repo_is_clean:
            logging.error("Git repo is not in a clean state! Exiting..")
            sys.exit(1)

        if not self.c.is_dryrun:
            files_to_commit = []
            for resource in resources.keys():
                # make sure path exists
                outdir = os.path.join(
                    self.c.rollout_path, "{}s".format(resource))
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
                    outdir, "{}-{}.yaml".format(self.c.app_name, resource))
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
        repo = repository.GitRepository(self.c.repopath)
        (repo_is_clean, repo_msg) = repo.is_clean()

        if not repo_is_clean:
            if self.c.is_dryrun or self.c.is_dryrun_but_templates:
                logging.debug("Dry run: skipping commit")
                return

            repo.commit_files(files_to_commit,
                              "[{}] Created rollout for {} with version {}\n\n{}".format(
                                  self.c.namespace,
                                  self.c.app_name,
                                  self.c.app_version,
                                  self.c.commit_message))
            logging.debug("Commited changes:\n{}".format(
                repo.show(self.c.rollout_path)))
        else:
            logging.warn(
                "Definition of rollout already exists. Nothing changed.")

    def rollout(self, resources):
        if self.c.is_dryrun or self.c.is_dryrun_but_templates:
            logging.info("Dry-run: skip applying changes to Kubernetes")
        else:
            logging.info("Rolling out resources {}".format(resources))
        for resource in resources:
            resourcefile = os.path.join(self.c.rollout_path,
                                        "{}s".format(resource),
                                        "{}-{}.yaml".format(
                                            self.c.app_name,
                                            resource))
            try:
                self.kubectl.apply_resourcefile(resourcefile)
            except KubeCtlException as e:
                logging.error("Rolling out failed. [{}]".format(e))
                sys.exit(1)

    def deploy(self):
        '''
        Prepare, write and rollout the k8s resources
        '''
        # render all templates for the given application
        resources = self.prepare_k8s_resources()

        # write rendered templates as filesystem
        res_names = self.write_k8s_resources(resources)

        # rollout kubernetes resources
        self.rollout(res_names)
