
import ipaddress
from network_common import State, Protocol, Port, httpd_filter_name

class Name:
    def __init__(self, name, escaped = False):
        if escaped:
            self.escaped = str(name)
        else:
            self.unescaped = str(name)
    @property
    def escaped(self):
        return httpd_filter_name(self.unescaped)
    @escaped.setter
    def escaped(self, name):
        self.unescaped = httpd_filter_name(str(name), True)
    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(self.unescaped))
    def __str__(self):
        return self.escaped

class PortForward:
    """This class represents a PortForward stored in a DD-WRT's NVRAM memory
    """
    def __init__(self, 
                 name, 
                 state, 
                 proto, 
                 to_port, 
                 to_ip, 
                 from_port, 
                 escaped_name = False, 
                 from_ip = None):
        
        self.name = Name(name, escaped_name)
        self.state = State(state)
        self.proto = Protocol(proto)
        self.to_port = Port(to_port)
        self.to_ip = ipaddress.ip_address(to_ip)
        self.from_port = Port(from_port)
        if from_ip is not None:
            self.set_from_ip(from_ip)
        else:
            self.from_ip = None
        
    def set_from_ip(self, from_ip):
        try:
            self.from_ip = ipaddress.ip_address(from_ip)
        except ValueError:
            self.from_ip = ipaddress.ip_interface(from_ip)
    
    @classmethod
    def from_forward_spec(cls, string):
        """Parses an encoded forward_spec forward,
        The format follows this general rule:
            
            "{escaped_name}:{state}:{protocol}:{from_port}>{to_ip}:{to_port}<{from_ip}"

                or

            "{escaped_name}:{state}:{protocol}:{from_port}>{to_ip}:{to_port}"

        """
        name, state, proto, from_port_to_ip, to_port_from_ip = string.split(":")
        from_port, to_ip = from_port_to_ip.split(">")
        
        if to_port_from_ip.find("<") == -1:
            to_port = to_port_from_ip
            from_ip = None
        else:
            to_port, from_ip = to_port_from_ip.split("<")
        
        return cls(name, state, proto, to_port, to_ip, from_port, True, from_ip)
        
    def __repr__(self):
        return "{}(name = {}, state = {}, proto = {}, to_port = {}, to_ip = {}, from_port = {}, from_ip = {})".format(
                   self.__class__.__name__, 
                   repr(self.name), 
                   repr(self.state), 
                   repr(self.proto), 
                   repr(self.to_port), 
                   repr(self.to_ip), 
                   repr(self.from_port), 
                   repr(self.from_ip))

    def __str__(self):
        if self.from_ip is not None:
            return "{}:{}:{}:{}>{}:{}<{}".format(
                self.name, self.state, self.proto, self.from_port, self.to_ip, self.to_port, self.from_ip)
        else: 
            return "{}:{}:{}:{}>{}:{}".format(
                self.name, self.state, self.proto, self.from_port, self.to_ip, self.to_port)

class ddwrt_forwards:
    def __init__(self, forward_spec_string):
        self.forwards = []
        for forward in forward_spec_string.split(" "):
            self.forwards += [PortForward.from_forward_spec(forward)]
    
    @classmethod
    def from_nvram(cls, nvram, check_entries = True):
        forwards = cls(nvram.get("forward_spec").decode("ascii"))
        if check_entries:
            expected_forwards = int(nvram.get("forwardspec_entries").decode("ascii"))
            if len(forwards) != expected_forwards:
                raise IOError("Expected to parse {} forwards, but instead parsed {}".format(
                    repr(expected_forwards), repr(len(forwards))))
        
        return forwards
    
    def write_to_nvram(self, nvram):
        """Saves the forwards into the router's nvram (without committing)
        """
        nvram.set("forward_spec", str(self))
        nvram.set("forwardspec_entries", len(self))
    
    def __str__(self):
        forward_spec = ""
        for forward in self.forwards:
            forward_spec += str(forward)
        return forward_spec
    
    def __len__(self):
        return len(self.forwards)
