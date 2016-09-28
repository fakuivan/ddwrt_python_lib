
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

class NVRAM_Cache:
    class void:
        """A dummy class used to specify a key deletion"""
        pass
    """This class provides an easy way to implement a dummy nvram-like 
    interface, it can be used as a fast way of doing large modifications, 
    dumping the resultant changes into a new nvram snapshot (ready to be 
    encoded and uploaded as a restore) or applying a changeset instead 
    issuing a lot of independent ssh commands.
    """
    def __init__(self, snapshot, key_not_found = ''):
        """:snapshot: A dictionary representig the router's nvram
        """
        self.key_not_found = key_not_found.encode()
        self.snapshot = snapshot
        self.changeset = {}
    
    def get(self, key):
        """Returns `value` for :key: on the nvram dictionary
        :key: A key
        """
        if key in self.changeset:
            if self.changeset[key] is self.void:
                return self.key_not_found
            else: return self.changeset[key].encode()
        elif key in self.snapshot:
            return self.snapshot[key]
        else: return self.key_not_found
    
    def set(self, key, value):
        """Adds `key` and `value` to the changeset
        :key: A key
        :value: A value
        """
        self.changeset[key] = value
    
    def unset(self, key):
        """Queues a removal on the changeset
        :key: A key
        """
        self.changeset[key] = self.void
    
    def get_changes(self):
        """Returns `(sets, unsets)` where `sets` is a dictionary containing
        { key: value, key1: value1, ... } the previously queued sets, and
        `unsets` is a list containing [keyrem, keyrem1, ...] the queued unsets
        """
        sets = {}
        unsets = []
        self.do_for_items(lambda key, value: sets.__setitem__(key, value),
                          lambda key: unsets.__iadd__([key]))
        return sets, unsets
            
    def get_snapshot(self):
        snapshot = self.snapshot.copy()
        self.do_for_items(lambda key, value: snapshot.__setitem__(key, value),
                          lambda key: snapshot.pop(key, None))
        return snapshot
    
    def do_for_items(self, set_func, unset_func):
        for key, value in self.changeset.items():
            if value is self.void:
                unset_func(key)
            else:
                set_func(key, value)
        
    def update_snapshot(self, snapshot):
        """Updates the current snapshot to `snapshot`
        """
        self.snapshot = snapshot

class NVRAM:
    def __init__(self, ssh_router):
        self.cache_mode = False
        self.router = ssh_router
    
    def set(self, key, value):
        """Sets 'value' for 'key' on the router's nvram dictionary""" 
        if not self.is_valid_key(key):
            raise KeyError("{} is not a valid key, try removing the '='".format(repr(key)))
        if self.cache_mode:
            self.cache.set(key, value)
        else:
            command = "nvram set {}".format(self.router.quote("{}={}".format(key, value)))
            self.router.client.exec_command(command)
    
    def unset(self, key):
        """Unsets 'key' on the router's nvram dictionary""" 
        if self.cache_mode:
            self.cache.unset(key)
        else:
            command = "nvram unset {}".format(self.router.quote(key))
            self.router.client.exec_command(command)
    
    def get(self, key):
        """Returns a value for 'key' on the router's nvram dictionary""" 
        if self.cache_mode:
            return self.cache.get(key)
        else:
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
    
    def enter_cache_mode(self, fetch_all = True):
        """Enters cache mode (local only), while this mode is active, no 
        commands will be submitted to the client, all changes made to 
        the nvram dictionary will only be local, when you exit this mode 
        all of the changes will be submitted as an nvram restore, only 
        activate this mode if you need to make a lot of changes to be
        worth the overhead of having to push a whole nvram restore.
        """
        if not self.cache_mode:
            memory = self.get_all() if fetch_all else OrderedDict()
            self.cache = NVRAM_Cache(memory)
            self.cache_mode = True
    
    def exit_cache_mode(self, as_changeset = False):
        """Exits cache mode, all of the changes will be submited to the 
        client as a nvram restore or as a change set
        """
        if self.cache_mode:
            command = ""
            sets, unsets = self.cache.get_changes()
            for key, value in sets.items():
                command += "nvram set {}; ".format(self.router.quote("{}={}".format(key, value)))
            for key in unsets:
                command += "nvram unset {}; ".format(self.router.quote(key))
            del self.cache
            self.cache_mode = False
            self.router.client.exec_command(command)
    
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

