import logging
import shlex
import subprocess

kubectl_format = "{kubectl} --namespace={namespace} {subcommand}"
kubectl_default_bin = "kubectl"

class KubeCtlException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class KubeCtl(object):
    def __init__(self, context, namespace, path=kubectl_default_bin, dryrun=False):
        if path != None:
            self.path = path
        else:
            self.path = kubectl_default_bin

        self.namespace = namespace
        self.context = context
        self.dryrun = dryrun

        if not self.dryrun:
            self.set_context()

    def _run(self, subcmd):
        cmd = shlex.split(kubectl_format.format(kubectl=self.path, namespace=self.namespace, subcommand=subcmd))

        if self.dryrun:
            logging.debug("Skipping '{}'".format(" ".join(cmd)))
            return
        else:
            logging.debug("Running '{}'".format(" ".join(cmd)))

        try:
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logging.error("kubectl failed with [{}]".format(e.output))
            return None

    def apply_resourcefile(self, resourcefile):
        self.verify_context()
        subcmd = "apply -f {}".format(resourcefile)
        self._run(subcmd)

    def set_context(self):
        subcmd = "config set-context {}".format(self.context)
        self._run(subcmd)

    def get_current_context(self):
        subcmd = "config current-context"
        return self._run(subcmd).rstrip()

    def verify_context(self):
        current_ctx = self.get_current_context()
        print(current_ctx)
        if current_ctx != self.context:
            raise KubeCtlException("kubectl uses a wrong context")
