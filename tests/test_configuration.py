import unittest
from ausroller import Configuration
from tempfile import NamedTemporaryFile


class ConfigurationTest(unittest.TestCase):

    def test_read_config(self):
        '''
        Check if the config / variable files can be read and parsed.
        '''
        config = '{"test": "test1", "test1":"test2"}'
        with NamedTemporaryFile() as tempfile:
            tempfile.write(config)
            tempfile.flush()
            v = Configuration().read_variables(tempfile.name)
            self.assertDictEqual({"test": "test1", "test1": "test2"}, v)

    def test_custom_json_pairs_hook_bad(self):
        '''
        Check if duplicate keys in the list raises KeyError
        '''
        c = Configuration()
        with self.assertRaises(KeyError):
            c._custom_json_pairs_hook([('key1', 'value'), ('key1', 'value')])

    def test_custom_json_pairs_hook_good(self):
        '''
        Check if an uniqe list returns a valid dict.
        '''
        c = Configuration()
        d = c._custom_json_pairs_hook([('key1', 'value'), ('key', 'value')])
        self.assertIsInstance(d, dict)
        self.assertDictEqual({'key1': 'value', 'key': 'value'}, d)

if __name__ == '__main__':
    unittest.main()
