import unittest
from ausroller import KubeCtl
from subprocess import CalledProcessError


class KubeCtlTest(unittest.TestCase):

    def test_run_dryrun(self):
        '''
        Check that no command is executed when using dryrun.
        '''
        l = KubeCtl('unittest', path="/does/not/exist", dryrun=True)
        retval = l._run('version')
        self.assertEqual(None, retval)

    def test_run_with_unsuccessful_cmd(self):
        '''
        Check that an Exception is raised when the command fails.
        '''
        l = KubeCtl('unittest', path='/bin/false', dryrun=False)
        with self.assertRaises(CalledProcessError):
            l._run('a')

    def test_apply_resourcefile(self):
        '''
        Check that the sub command is proper constructed.
        We let the command execution fail on purpose to get
        an exception back from the called method so we can check the
        complete command.
        '''
        t = KubeCtl(namespace='doctest', path='/bin/false')
        with self.assertRaises(CalledProcessError) as e:
            t.apply_resourcefile('/path/to/resourcefile')
        self.assertEqual(e.exception.cmd, ['/bin/false',
                                           '--namespace=doctest',
                                           'apply', '-f',
                                           '/path/to/resourcefile'])

    def test_KubeCtl_defaults(self):
        '''
        Check that KubeCtl uses sane defaults.
        '''
        k = KubeCtl('unittest', path=None)
        self.assertEqual('kubectl', k.path)
        self.assertEqual(False, k.dryrun)
