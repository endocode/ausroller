import logging
import re
import shlex
import subprocess
import sys

kubectl_format = "{kubectl} --context={context} --namespace={namespace} {subcommand}"
kubectl_default_bin = "kubectl"


class KubeCtlException(Exception):

    def __init__(self, message, cause=None):
        super(Exception, self).__init__(
            "{} [caused by {}]".format(message, cause))
        self.cause = cause


class KubeCtl(object):

    def __init__(self, context, namespace, path=kubectl_default_bin, dryrun=False, skip_verify=False):
        if path != None:
            self.path = path
        else:
            self.path = kubectl_default_bin

        self.namespace = namespace
        self.context = context
        self.dryrun = dryrun

        required_ctx = re.escape(self.context)
        self.ctx_pattern = re.compile(
            "^{}$".format(required_ctx), re.MULTILINE)

        if not skip_verify:
            try:
                self.verify_context_available()
            except KubeCtlException as e:
                logging.error("Configuring kubectl failed. [{}]".format(e))
                sys.exit(1)

    def _run(self, subcmd):
        cmd = shlex.split(kubectl_format.format(
            kubectl=self.path, namespace=self.namespace, context=self.context, subcommand=subcmd))

        if self.dryrun:
            logging.debug("Skipping '{}'".format(" ".join(cmd)))
            return
        else:
            logging.debug("Running '{}'".format(" ".join(cmd)))

        try:
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logging.error("kubectl failed with [{}]".format(e.output))
            raise KubeCtlException("running kubectl failed", e)

    def apply_resourcefile(self, resourcefile):
        subcmd = "apply -f {}".format(resourcefile)
        self._run(subcmd)

    def get_contexts(self):
        subcmd = "config get-contexts -o name"
        return self._run(subcmd).rstrip()

    def verify_context_available(self):
        configured_ctxs = self.get_contexts()
        logging.debug("Found the following contexts: {}".format(
            configured_ctxs.replace("\n", ", ")))
        match = self.ctx_pattern.search(configured_ctxs)
        if not match:
            raise KubeCtlException(
                "The requested kubectl context [{}] is not available.".format(self.context))
