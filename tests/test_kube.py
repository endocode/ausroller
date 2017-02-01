import unittest
from ausroller import KubeCtl, KubeCtlException


class KubeCtlTest(unittest.TestCase):

    def test_run_dryrun(self):
        '''
        Check that no command is executed when using dryrun.
        '''
        l = KubeCtl('unittest', 'unittest',
                    path="/does/not/exist", dryrun=True, skip_verify=True)
        retval = l._run('version')
        self.assertEqual(None, retval)

    def test_run_with_unsuccessful_cmd(self):
        '''
        Check that an Exception is raised when the command fails.
        '''
        l = KubeCtl('unittest', 'unittest', path='/bin/false', dryrun=False, skip_verify=True)
        with self.assertRaises(KubeCtlException):
            l._run('a')

    def test_apply_resourcefile(self):
        '''
        Check that the sub command is properly constructed.
        We let the command execution fail on purpose to get
        an exception back from the called method so we can check the
        complete command.
        '''
        t = KubeCtl('unittest', namespace='doctest', path='/bin/false', skip_verify=True)
        with self.assertRaises(KubeCtlException) as e:
            t.apply_resourcefile('/path/to/resourcefile')
        self.assertEqual(e.exception.cause.cmd, ['/bin/false',
                                                 '--context=unittest',
                                                 '--namespace=doctest',
                                                 'apply', '-f',
                                                 '/path/to/resourcefile'])

    def test_KubeCtl_defaults(self):
        '''
        Check that KubeCtl uses sane defaults.
        '''
        k = KubeCtl('unittest', 'unittest', path=None, skip_verify=True)
        self.assertEqual('kubectl', k.path)
        self.assertEqual(False, k.dryrun)
