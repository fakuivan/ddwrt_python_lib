
from collections import OrderedDict
import struct
class NVRAM_Codec:
    def __init__(self, header = b'DD-WRT'):
        self.header = header
    
    def decode(self, data, ordered = True, allow_duplicated_key = True):
        """Decodes a DD-WRT nvram backup, if *ordered* is True
        this function will return an OrderedDict instead of a 
        dict. This can be useful when encoding backups again
        since the order is preserved
        """
        self.to_decode = data
        header = self.get_header()
        if header != self.header:
            raise IOError("The NVRAM decoder expected to find {} as a header but instead got {}".format(
                repr(self.header), repr(header)))
        size = len(self.to_decode)
        position = len(self.header) + 2
        if ordered:
            dictionary = OrderedDict()
        else:
            dictionary = {}
        
        while position < size:
            key_size = self.get_key_size(position)
            position += 1
            
            key = self.get_key(position, key_size)
            position += key_size
            
            value_size = self.get_value_size(position)
            position += 2
            
            value = self.get_value(position, value_size)
            position += value_size
            
            if (not allow_duplicated_key) and (key in dictionary):
                raise KeyError("{} already exists in the dictionary, as {}".format(
                    repr(key), repr({key : dictionary[key]})))
            dictionary[key] = value
        expected_length = self.get_items()
        length = len(dictionary) 
        if expected_length != length:
            raise IOError("The NVRAM decoder expected the dictionary of items to be {} elements long, but instead got {}".format(
                                repr(expected_length), repr(length)))
        return dictionary
    
    def get_header(self):
        """Returns the header of the binary
        """
        return self.to_decode[:len(self.header)]
    
    def get_items(self):
        """Returns the number of items stored
        """
        return struct.unpack('H', self.to_decode[len(self.header):len(self.header) + 2])[0]
    
    def get_key_size(self, pos):
        """Reads the size of a key at position *pos*
        """
        subset = self.to_decode[pos : pos + 1]
        try:
            return struct.unpack('B', subset)[0]
        except struct.error as error:
            if len(subset) < 1:
                raise LookupError("The stream ended before we got all the items items." 
                                  "Postion {}, subset {}".format(
                    repr(pos), repr(subset)))
            else: 
                raise error
    
    def get_key(self, pos, size):
        """Reads a key at position *pos* of the size *size*
        """
        return self.to_decode[pos: pos + size]
    
    def get_value_size(self, pos):
        """Reads the size of a value at position *pos*
        """
        subset = self.to_decode[pos : pos + 2]
        try:
            return struct.unpack('H', subset)[0]
        except struct.error as error:
            if len(subset) < 2:
                raise LookupError("The stream ended before we got all the items items." 
                                  "Postion {}, subset {}".format(
                    repr(pos), repr(subset)))
            else: 
                raise error
    
    def get_value(self, pos, size):
        """Reads a value at position *pos* of the size *size*
        """
        return self.to_decode[pos : pos + size]
    
    def encode(self, data):
        length = len(data)
        encoded = self.header + struct.pack('H', length)
        
        for key, value in data.items():
            encoded += struct.pack('B', len(key))[0:1] + key + struct.pack('H', len(value))[0:2] + value

        return encoded


class NVRAM:
    def __init__(self, ssh_router):
        self.router = ssh_router
    
    def set(self, key, value):
        """Sets 'value' for 'key' on the router's nvram dictionary""" 
        if not self.is_valid_key(key):
            raise KeyError("{} is not a valid key, try removing the '='".format(repr(key)))
        command = "nvram set {}".format(self.router.quote("{}={}".format(key, value)))
        self.router.client.exec_command(command)
    
    def unset(self, key):
        """Unsets 'key' on the router's nvram dictionary""" 
        command = "nvram unset {}".format(self.router.quote(key))
        self.router.client.exec_command(command)
    
    def get(self, key):
        """Returns a value for 'key' on the router's nvram dictionary""" 
        command = "nvram get {}".format(self.router.quote(key))
        stdout = self.router.client.exec_command(command)[1]
        return stdout.read()[:-1]
    
    def get_all(self):
        """Returns a dictionary representing the router's nvram dictionary""" 
        return NVRAM_Codec().decode(self.backup())
    
    def commit(self):
        """Writes the changes made (not exclusively by this aplication) 
        to the nvram dictionary since the last commit 
        """
        command = "nvram commit"
        self.router.client.exec_command(command)
    
    def backup(self):
        """Returns a byte array object, ready to be decoded or saved 
        to a local file
        """
        command = "nvram backup /dev/tty"
        stdout = self.router.pipe_to_stdin(command)[1]
        return self.router.chop_header(stdout.read())
    
    def is_valid_key(self, key):
        """Returns true if the key is not going to be misinterpreted by the 
        nvram aplication, since the argument gets splitted by the first equal 
        sign it finds.
        
        Lets say that you want to use the key "is this = to my ip", you would 
        issue a command like:
        
            nvram set "is this = to my ip=yes"
        
        This would end up being stored as:
        
            {"is this " : " to my ip=yes"}
        
        instead of: 

            {"is this = to my ip" : "yes"}
        
        While the name of the key might be valid (in fact, any unique string can be 
        considered valid), the aplication is going to interpret it as a different 
        set of values. Usually this is not a problem, since most aplications that
        use the nvram storage store their data with shell-like key names, if you are
        facing this "problem", you might want to do the same.
        http://svn.dd-wrt.com/browser/src/router/rc/nvram.c#L57
        """
        return str(key).find("=") == -1