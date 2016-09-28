import unittest
import paramiko

from nvram import NVRAM, NVRAM_Codec
from ssh import ddwrt_ssh
class NVRAMTests(unittest.TestCase):
    def setUp(self):
        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        self.client.load_system_host_keys()
        self.client.connect(input("Hostname:> "), username = input("Username:> "))
        self.client.exec_command("nvram backup /tmp/nvram.bkp")
    
    def tearDown(self):
        self.client.exec_command("nvram restore /tmp/nvram.bkp && rm /tmp/nvram.bkp")
        self.client.close()
        
    def test_nvram(self):
        nvram = NVRAM(ddwrt_ssh(self.client))
        key, value = ("!#$$$%&%>>><<<", "\n&&!!#$%&/\"")
        nvram.set(key, value)
        self.assertEqual(nvram.get(key).decode('ascii'), value)
        nvram.unset(key)
        with self.assertRaises(KeyError):
            nvram.set("====", ":V")
    
    def test_cache(self):
        nvram = NVRAM(ddwrt_ssh(self.client))
        nvram.enter_cache_mode()
        nvram.set('key1', 'value1')
        nvram.set('key2', 'value2')
        nvram.set('key3', 'value3')
        nvram.set('key4', 'value4')
        self.assertEqual(nvram.get('key1'), b'value1')
        nvram.unset('key1')
        nvram.unset('daljwnd21')
        self.assertEqual(nvram.get('key1'), b'')
        nvram.cache.get_snapshot()
        nvram.cache.get_changes()
        nvram.exit_cache_mode()
        self.assertEqual(nvram.get('key2'), b'value2')
        self.assertEqual(nvram.get('key3'), b'value3')
        self.assertEqual(nvram.get('key4'), b'value4')
            
        

    def test_codec(self):
        memory = NVRAM(ddwrt_ssh(self.client)).backup()
        codec = NVRAM_Codec()
        decoded = codec.decode(memory)
        encoded = codec.encode(decoded)
        decoded_twice = codec.decode(encoded)
        self.assertEqual(decoded_twice, decoded)
        #self.assertEqual(encoded, memory) #this won't be equal if the backup has a duplicated key :'v


from network_common import Port, Protocol, MAC_address, State, httpd_filter_name
class NetCommonTests(unittest.TestCase):
    def test_Port(self):
        with self.assertRaises(ValueError):
            Port(0, False)
        with self.assertRaises(ValueError):
            Port(65536)
        self.assertEqual(int(Port("1")), 1)
        self.assertEqual(str(Port(65535)), "65535")
    
    def test_Protocol(self):
        self.assertEqual(Protocol("tcP").protocol, "tcp")
        self.assertEqual(Protocol("Udp").protocol, "udp")
        self.assertEqual(Protocol("bOth").protocol, "both")
        with self.assertRaises(ValueError):
            Protocol("meme")
        with self.assertRaises(ValueError):
            Protocol("both", False)
    
    def test_MAC_address(self):
        self.assertEqual(str(MAC_address("00:22:33:00:76:99")), "00:22:33:00:76:99")
        with self.assertRaises(ValueError):
            MAC_address(0.0)

    def test_State(self):
        self.assertEqual((State(True).state, State("oN").state, State(1).state), (True, True, True))
        self.assertEqual((State(False).state, State("oFf").state, State(0).state), (False, False, False))
        with self.assertRaises(ValueError):
            State("OnGameFrame")
    def test_Escaper(self):
        chars = "<> :"
        self.assertEqual(httpd_filter_name(httpd_filter_name(chars), True), chars)
        for char in chars:
            self.assertEqual(httpd_filter_name(chars).find(char), -1)

if __name__ == '__main__':
    unittest.main()
