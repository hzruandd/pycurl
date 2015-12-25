'''A high-level interface to the pycurl extension'''

# ** mfx NOTE: the CGI class uses "black magic" using COOKIEFILE in
#    combination with a non-existant file name. See the libcurl docs
#    for more info.

import sys, pycurl

py3 = sys.version_info[0] == 3

# python 2/3 compatibility
if py3:
    import urllib.parse as urllib_parse
    from urllib.parse import urljoin
    from io import BytesIO
else:
    import urllib as urllib_parse
    from urlparse import urljoin
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass


class Curl:
    "High-level interface to pycurl functions."
    def __init__(self, base_url="", fakeheaders=[]):
        self.handle = pycurl.Curl()
        # These members might be set.
        self.set_url(base_url)
        self.verbosity = 0
        self.fakeheaders = fakeheaders
        # Nothing past here should be modified by the caller.
        self.payload = None
        self.payload_io = BytesIO()
        self.hrd = ""
        # Verify that we've got the right site; harmless on a non-SSL connect.
        self.set_option(pycurl.SSL_VERIFYHOST, 2)
        # Follow redirects in case it wants to take us to a CGI...
        self.set_option(pycurl.FOLLOWLOCATION, 1)
        self.set_option(pycurl.MAXREDIRS, 5)
        self.set_option(pycurl.NOSIGNAL, 1)
        # Setting this option with even a nonexistent file makes libcurl
        # handle cookie capture and playback automatically.
        self.set_option(pycurl.COOKIEFILE, "/dev/null")
        # Set timeouts to avoid hanging too long
        self.set_timeout(30)
        # Use password identification from .netrc automatically
        self.set_option(pycurl.NETRC, 1)
        self.set_option(pycurl.WRITEFUNCTION, self.payload_io.write)
        def header_callback(x):
            self.hdr += x.decode('ascii')
        self.set_option(pycurl.HEADERFUNCTION, header_callback)

    def set_timeout(self, timeout):
        "Set timeout for a retrieving an object"
        self.set_option(pycurl.TIMEOUT, timeout)

    def set_url(self, url):
        "Set the base URL to be retrieved."
        self.base_url = url
        self.set_option(pycurl.URL, self.base_url)

    def set_option(self, *args):
        "Set an option on the retrieval."
        self.handle.setopt(*args)

    def set_verbosity(self, level):
        "Set verbosity to 1 to see transactions."
        self.set_option(pycurl.VERBOSE, level)

    def __request(self, relative_url=None):
        "Perform the pending request."
        if self.fakeheaders:
            self.set_option(pycurl.HTTPHEADER, self.fakeheaders)
        if relative_url:
            self.set_option(pycurl.URL, urljoin(self.base_url, relative_url))
        self.payload = None
        self.hdr = ""
        self.handle.perform()
        self.payload = self.payload_io.getvalue()
        return self.payload

    def get(self, url="", params=None):
        "Ship a GET request for a specified URL, capture the response."
        if params:
            url += "?" + urllib_parse.urlencode(params)
        self.set_option(pycurl.HTTPGET, 1)
        return self.__request(url)

    def post(self, cgi, params):
        "Ship a POST request to a specified CGI, capture the response."
        self.set_option(pycurl.POST, 1)
        self.set_option(pycurl.POSTFIELDS, urllib_parse.urlencode(params))
        return self.__request(cgi)

    def body(self):
        "Return the body from the last response."
        return self.payload

    def header(self):
        "Return the header from the last response."
        return self.hdr

    def get_info(self, *args):
        "Get information about retrieval."
        return self.handle.getinfo(*args)

    def info(self):
        "Return a dictionary with all info on the last response."
        #NOTE(hzruandd):optimized code here.
        m = {}
        keys = ["effective-url", "http-code", "total-time",
                "namelookup-time", "connect-time", "pretransfer-time",
                "redirect-time", "redirect-count", "size-upload",
                "size-download", "speed-upload", "header-size", "request-size"
                "content-length-download", "content-length-upload",
                "content-type", "response-code", "speed-download"
                "ssl-verifyresult", "filetime", "starttransfer-time",
                "starttransfer-time", "redirect-time", "redirect-count",
                "http-connectcode", "httpauth-avail", "proxyauth-avail",
                "os-errno", "num-connects", "ssl-engines", "ftp-entry-path"
                ]
        for k in keys:
            v = getattr(pycurl, k.replace("-", "_").upper())
            m[k] = self.handle.getinfo(v)

        m['filetime'] = self.handle.getinfo(pycurl.INFO_FILETIME)
        m['cookielist'] = self.handle.getinfo(pycurl.INFO_COOKIELIST)

        return m

    def answered(self, check):
        "Did a given check string occur in the last payload?"
        return self.payload.find(check) >= 0

    def close(self):
        "Close a session, freeing resources."
        if self.handle:
            self.handle.close()
        self.handle = None
        self.hdr = ""
        self.payload = ""

    def __del__(self):
        self.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        url = 'http://curl.haxx.se'
    else:
        url = sys.argv[1]
    c = Curl()
    c.get(url)
    print(c.body())
    print('='*74 + '\n')
    import pprint
    pprint.pprint(c.info())
    print(c.get_info(pycurl.OS_ERRNO))
    print(c.info()['os-errno'])
    c.close()
