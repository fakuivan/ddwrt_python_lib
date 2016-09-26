
from network_common import MAC_address
from ipaddress import ip_address

class Lease:
    def __init__(self, mac, hostname, ip):
        self.mac = MAC_address(mac)
        self.ip = ip_address(ip)
        self.hostname = hostname
    
    @classmethod
    def from_static_leases(cls, lease):
        details = lease.split("=", 3)
        if len(details) >= 3:
            return cls(*(details[:3]))
    
    def __list__(self):
        return [self.mac, self.hostname, self.ip]
    
    def __repr__(self):
        return "{}(mac = {} hostname = {}, ip = {})".format(
            self.__class__.__name__, repr(self.mac), repr(self.hostname), repr(self.ip))

class ddwrt_leases:
    """This class wraps around Lease, to provide
    a simple way to convert a static_leases nvram string
    into multiple objects and back into a static_leases string
    these can be edited by accessing the leases attibute
    """
    def __init__(self, leases_string):
        self.leases = []
        for lease in leases_string.split(" "):
            new_lease = Lease.from_static_leases(lease)
            if new_lease is not None:
                self.leases += [new_lease]

    @classmethod
    def from_nvram(cls, nvram, check_entries = True):
        leases = cls(nvram.get("static_leases").decode("ascii"))
        if check_entries:
            expected_leases = int(nvram.get("static_leasenum").decode("ascii"))
            if len(leases) != expected_leases:
                raise IOError("Expected to parse {} leases, but instead parsed {}".format(
                    repr(expected_leases), repr(len(leases))))
            else:
                return leases
        else:
            return leases
    
    def write_to_nvram(self, nvram):
        nvram.set("static_leases", str(self))
        nvram.set("static_leasenum", len(self))

    def __str__(self):
        formatted = ""
        for lease in self.leases:
            formatted += "{}={}={}= ".format(str(lease.mac), 
                                             str(lease.hostname), 
                                             str(lease.ip))
        return formatted
    
    def __len__(self):
        return len(self.leases)