import unittest
from ausroller.kube import KubeCtl, KubeCtlException
from tempfile import NamedTemporaryFile

class KubeCtlTest(unittest.TestCase):
    def test_wrong_context(self):
        kubectl = KubeCtl("anyfoobarctx", "anyfoobarnamespace")
        kubectl.context = "anybarfooctx"
        with self.assertRaises(KubeCtlException):
            kubectl.verify_context()


if __name__ == '__main__':
    unittest.main()
