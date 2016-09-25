
class MAC_address:
    def __init__(self, address):
        if isinstance(address, str):
            self.address = int(address.replace(':', ''), 16)
        elif isinstance(address, int):
            self.address = address
        else:
            raise ValueError("Expected an instance of {} or {}, got {}".format(
                repr(str), repr(int), repr(address.__class__)))
    
    def __str__(self):
        return "{:02X}:{:02X}:{:02X}:{:02X}:{:02X}:{:02X}".format(
            (self.address >> 40 & 0xff),
            (self.address >> 32 & 0xff),
            (self.address >> 24 & 0xff),
            (self.address >> 16 & 0xff),
            (self.address >> 8  & 0xff),
            (self.address & 0xff)
            )
    
    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(str(self)))
    
    def __int__(self):
        return self.address

class State:
    def __init__(self, state):
        self.state = state
        
    @property
    def state(self):
        return self._state
        
    @state.setter
    def state(self, state):
        if hasattr(state, "lower"): state = state.lower()
        if (state == "on") or (state == True) or (state == 1):
            self._state = True
        elif (state == "off") or (state == False) or (state == 0):
            self._state = False
        else:
            raise ValueError("{} is not a valid state".format(repr(state)))
        
    def __str__(self):
        if self._state:
            return "on"
        else:
            return "off"
    
    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(str(self)))
    
    def __int__(self):
        if self._state:
            return 1
        else:
            return 0
    def __bool__(self):
        return self._state

class Port:
    def __init__(self, number, allow_null = True):
        self.allow_null = allow_null
        self.port = number

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, number):
        _number = int(number)
        if _number >= (0 if self.allow_null else 1) and _number <= 65535:
            self._number = _number
        else:
            raise ValueError("Valid port numbers are between {} and 65535, got {}".format(
                0 if self.allow_null else 1, 
                _number))

    def __int__(self):
        return self._number

    def __str__(self):
        return str(self._number)

    def __repr__(self):
        return "Port({})".format(repr(self._number))

class Protocol:
    def __init__(self, proto, allow_both = True):
        self.allow_both = allow_both
        self.protocol = proto
    
    @property
    def protocol(self):
        if self._proto == 1:
            return "tcp"
        if self._proto == 2:
            return "udp"
        if self._proto == 0:
            return "both"
    
    @protocol.setter
    def protocol(self, proto):
        if proto.lower() == "tcp":
            self._proto = 1
        elif proto.lower() == "udp":
            self._proto = 2
        elif proto.lower() == "both" and self.allow_both:
            self._proto = 0
        else:
            raise ValueError("{} is not a valid protocol".format(repr(proto)))
    
    def __int__(self):
        return self._proto
    
    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(self.protocol))
    
    def __str__(self):
        return self.protocol

def httpd_filter_name(name, unscape = False):
    """This function is a port from base.c, it escapes and unscapes
    names used by ForwardSpec.asp
    http://svn.dd-wrt.com/browser/src/router/httpd/modules/base.c#L2589
    """
    if not unscape:
        return name.replace(" ", "&nbsp;").replace(":", "&semi;").replace("<", "&lt;").replace(">", "&gt;")
    else:
        return name.replace("&nbsp;", " ").replace("&semi;", ":").replace("&lt;", "<").replace("&gt;", ">")