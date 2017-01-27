import logging
import shlex
import subprocess

kubectl_format = "{kubectl} --namespace={namespace} {subcommand}"
kubectl_default_bin = "kubectl"


class KubeCtl(object):

    def __init__(self, namespace, path=kubectl_default_bin, dryrun=False):
        if path is not None:
            self.path = path
        else:
            self.path = kubectl_default_bin
        self.namespace = namespace
        self.dryrun = dryrun

    def _run(self, subcmd):
        '''
        (str) -> str or None
        Run the given Str subcmd as sub command of kubectl
        and return the output as string.

        >>> k = KubeCtl('doctest', path='echo kubectl')
        >>> k._run('version')
        'kubectl --namespace=doctest version\\n'
        >>>
        '''
        cmd = shlex.split(kubectl_format.format(
            kubectl=self.path, namespace=self.namespace, subcommand=subcmd))

        if self.dryrun:
            logging.debug("Skipping '{}'".format(" ".join(cmd)))
            return
        else:
            logging.debug("Running '{}'".format(" ".join(cmd)))

        try:
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logging.error("kubectl failed with [{}]".format(e.output))
            raise

    def apply_resourcefile(self, resourcefile):
        '''
        (str)
        Runs 'kubectl apply -f' with the given resource file.
        '''
        subcmd = "apply -f {}".format(resourcefile)
        self._run(subcmd)
