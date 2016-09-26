from ssh import ddwrt_ssh
from nvram import NVRAM
from leases import ddwrt_leases
import paramiko

def main():
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
    client.load_system_host_keys()
    hostname = input("Hostname:> ")
    username = input("Username:> ")
    print("Connecting with paramiko...")
    client.connect(hostname, username = username)
    
    print("Setting up ssh objects...")
    router = ddwrt_ssh(client)
    print("Setting up nvram objects...")
    nvram = NVRAM(router)
    
    print("Fetching leases...")
    leases = ddwrt_leases.from_nvram(nvram, True)
    
    print("Printing...")
    pretty = "\nLeases on the router:"
    for lease in leases.leases:
        if lease is not None:
            pretty += "\n   Hostname: {}; IP: {}; MAC: {}".format(lease.hostname, lease.ip, lease.mac)
    print(pretty)

if __name__ == "__main__": main()
