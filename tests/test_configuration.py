import unittest
from ausroller import Configuration
from tempfile import NamedTemporaryFile

class ConfigurationTest(unittest.TestCase):
    def test_duplicate_config_key(self):
        config = '{"test": "test1", "test":"test2"}'
        with NamedTemporaryFile() as tempfile:
            tempfile.write(config)
            tempfile.flush()
            with self.assertRaises(KeyError):
                Configuration().read_variables(tempfile.name)


if __name__ == '__main__':
    unittest.main()
