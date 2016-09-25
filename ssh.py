
import shlex
class ddwrt_ssh():
    """A small wrapper for paramaiko's SSHClient, it supplies most
     of the ssh sppecific functions needed to operate on the router 
    via this medium
    """
    def __init__(self, paramiko_client, get_header_now = False):
        """:paramiko_client: a `paramiko.client.SSHCient` instance
        :get_header_now: `True` if the header for `.chop_header` needs
        to be fetched manually instead of being initialized by `.pipe_to_stdin`
        """
        self.client = paramiko_client
        if get_header_now:
            self.get_header()
        else:
            self.header_length = None
        pass
    
    def pipe_to_stdin(self, command, bufsize = -1, timeout = None):
        """Requests a pty along with some parameters to avoid data loss
        caused by the use of a pseudo-terminal, it's safe to use /dev/tty
        here. Keep in mind that sometimes it might be safer to use sftp
        and temporary files.
        """
        if self.header_length is None: self.fetch_header()
        dont_replace_newline = "stty -onlcr"    #the 'stty -onlcr' command should
                                                #be executed so the binary data
                                                #doesn't get mess up on the way
                                                #(\n gets preserved)
        
        return self.client.exec_command("{}; {}".format(
            dont_replace_newline, command), get_pty =  True, bufsize = bufsize, timeout = timeout)
    
    def chop_header(self, string):
        return string[self.header_length:]

    def fetch_header(self):
        """Some routers print a header when requesting a pty, this function
        is designed to catch it, so it can be removed from the stdout later on
        """
        self.header_length = len(self.client.exec_command('', get_pty = True)[1].read())
    
    def quote(self, string):
        """A wrapper for `shlex.quote` (just for convenience)"""
        return shlex.quote(string)