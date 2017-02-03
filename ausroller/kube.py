import logging
import re
import shlex
import subprocess
import sys

kubectl_format = "{kubectl} --context={context} --namespace={namespace} {subcommand}"
kubectl_default_bin = "kubectl"
min_version = (1, 4, 0)


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
                self.verify_version()
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

    def verify_version(self):
        subcmd = "version --short"
        versions = self._run(subcmd)
        version_pattern = re.compile(
            "Client Version: v(\d+)\.(\d+)\.(\d+)\nServer Version: v(\d+)\.(\d+)\.(\d+)")
        match = version_pattern.match(versions)
        if not match:
            raise KubeCtlException(
                "Failed to get kubectl versions. The api server might not be available.")
        else:
            client_version = (int(match.group(1)), int(
                match.group(2)), int(match.group(3)))
            server_version = (int(match.group(4)), int(
                match.group(5)), int(match.group(6)))

            logging.debug("Found versions: client[{}] server[{}]".format(
                '.'.join(map(str, client_version)),
                '.'.join(map(str, server_version))
            ))
            if client_version < min_version:
                logging.error("kubectl client version is too old. Please upgrade to at least [{}.{}.{}]".format(
                    *list(min_version)))
                raise KubeCtlException("kubectl client version is too old.")

            if client_version < server_version:
                logging.warn(
                    "kubectl client version is older than the server's version. Please consider upgrading your client.")
