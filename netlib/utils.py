from __future__ import (absolute_import, print_function, division)
import os.path
import cgi
import urllib
import urlparse
import string
import re
import six
import unicodedata


def isascii(s):
    try:
        s.decode("ascii")
    except ValueError:
        return False
    return True


# best way to do it in python 2.x
def bytes_to_int(i):
    return int(i.encode('hex'), 16)


def clean_bin(s, keep_spacing=True):
    """
        Cleans binary data to make it safe to display.

        Args:
            keep_spacing: If False, tabs and newlines will also be replaced.
    """
    if isinstance(s, six.text_type):
        if keep_spacing:
            keep = u" \n\r\t"
        else:
            keep = u" "
        return u"".join(
            ch if (unicodedata.category(ch)[0] not in "CZ" or ch in keep) else u"."
            for ch in s
        )
    else:
        if keep_spacing:
            keep = b"\n\r\t"
        else:
            keep = b""
        return b"".join(
            ch if (31 < ord(ch) < 127 or ch in keep) else b"."
            for ch in s
        )


def hexdump(s):
    """
        Returns a set of tuples:
            (offset, hex, str)
    """
    parts = []
    for i in range(0, len(s), 16):
        o = "%.10x" % i
        part = s[i:i + 16]
        x = " ".join("%.2x" % ord(i) for i in part)
        if len(part) < 16:
            x += " "
            x += " ".join("  " for i in range(16 - len(part)))
        parts.append(
            (o, x, clean_bin(part, False))
        )
    return parts


def setbit(byte, offset, value):
    """
        Set a bit in a byte to 1 if value is truthy, 0 if not.
    """
    if value:
        return byte | (1 << offset)
    else:
        return byte & ~(1 << offset)


def getbit(byte, offset):
    mask = 1 << offset
    if byte & mask:
        return True


class BiDi(object):

    """
        A wee utility class for keeping bi-directional mappings, like field
        constants in protocols. Names are attributes on the object, dict-like
        access maps values to names:

        CONST = BiDi(a=1, b=2)
        assert CONST.a == 1
        assert CONST.get_name(1) == "a"
    """

    def __init__(self, **kwargs):
        self.names = kwargs
        self.values = {}
        for k, v in kwargs.items():
            self.values[v] = k
        if len(self.names) != len(self.values):
            raise ValueError("Duplicate values not allowed.")

    def __getattr__(self, k):
        if k in self.names:
            return self.names[k]
        raise AttributeError("No such attribute: %s", k)

    def get_name(self, n, default=None):
        return self.values.get(n, default)


def pretty_size(size):
    suffixes = [
        ("B", 2 ** 10),
        ("kB", 2 ** 20),
        ("MB", 2 ** 30),
    ]
    for suf, lim in suffixes:
        if size >= lim:
            continue
        else:
            x = round(size / float(lim / 2 ** 10), 2)
            if x == int(x):
                x = int(x)
            return str(x) + suf


class Data(object):

    def __init__(self, name):
        m = __import__(name)
        dirname, _ = os.path.split(m.__file__)
        self.dirname = os.path.abspath(dirname)

    def path(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.join(self.dirname, '../test/', path)
        if not os.path.exists(fullpath):
            raise ValueError("dataPath: %s does not exist." % fullpath)
        return fullpath


def is_valid_port(port):
    if not 0 <= port <= 65535:
        return False
    return True


def is_valid_host(host):
    try:
        host.decode("idna")
    except ValueError:
        return False
    if "\0" in host:
        return None
    return True


def parse_url(url):
    """
        Returns a (scheme, host, port, path) tuple, or None on error.

        Checks that:
            port is an integer 0-65535
            host is a valid IDNA-encoded hostname with no null-bytes
            path is valid ASCII
    """
    try:
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    except ValueError:
        return None
    if not scheme:
        return None
    if '@' in netloc:
        # FIXME: Consider what to do with the discarded credentials here Most
        # probably we should extend the signature to return these as a separate
        # value.
        _, netloc = string.rsplit(netloc, '@', maxsplit=1)
    if ':' in netloc:
        host, port = string.rsplit(netloc, ':', maxsplit=1)
        try:
            port = int(port)
        except ValueError:
            return None
    else:
        host = netloc
        if scheme.endswith("https"):
            port = 443
        else:
            port = 80
    path = urlparse.urlunparse(('', '', path, params, query, fragment))
    if not path.startswith("/"):
        path = "/" + path
    if not is_valid_host(host):
        return None
    if not isascii(path):
        return None
    if not is_valid_port(port):
        return None
    return scheme, host, port, path


def get_header_tokens(headers, key):
    """
        Retrieve all tokens for a header key. A number of different headers
        follow a pattern where each header line can containe comma-separated
        tokens, and headers can be set multiple times.
    """
    if key not in headers:
        return []
    tokens = headers[key].split(",")
    return [token.strip() for token in tokens]


def hostport(scheme, host, port):
    """
        Returns the host component, with a port specifcation if needed.
    """
    if (port, scheme) in [(80, "http"), (443, "https")]:
        return host
    else:
        return "%s:%s" % (host, port)


def unparse_url(scheme, host, port, path=""):
    """
        Returns a URL string, constructed from the specified compnents.
    """
    return "%s://%s%s" % (scheme, hostport(scheme, host, port), path)


def urlencode(s):
    """
        Takes a list of (key, value) tuples and returns a urlencoded string.
    """
    s = [tuple(i) for i in s]
    return urllib.urlencode(s, False)


def urldecode(s):
    """
        Takes a urlencoded string and returns a list of (key, value) tuples.
    """
    return cgi.parse_qsl(s, keep_blank_values=True)


def parse_content_type(c):
    """
        A simple parser for content-type values. Returns a (type, subtype,
        parameters) tuple, where type and subtype are strings, and parameters
        is a dict. If the string could not be parsed, return None.

        E.g. the following string:

            text/html; charset=UTF-8

        Returns:

            ("text", "html", {"charset": "UTF-8"})
    """
    parts = c.split(";", 1)
    ts = parts[0].split("/", 1)
    if len(ts) != 2:
        return None
    d = {}
    if len(parts) == 2:
        for i in parts[1].split(";"):
            clause = i.split("=", 1)
            if len(clause) == 2:
                d[clause[0].strip()] = clause[1].strip()
    return ts[0].lower(), ts[1].lower(), d


def multipartdecode(headers, content):
    """
        Takes a multipart boundary encoded string and returns list of (key, value) tuples.
    """
    v = headers.get("content-type")
    if v:
        v = parse_content_type(v)
        if not v:
            return []
        boundary = v[2].get("boundary")
        if not boundary:
            return []

        rx = re.compile(r'\bname="([^"]+)"')
        r = []

        for i in content.split("--" + boundary):
            parts = i.splitlines()
            if len(parts) > 1 and parts[0][0:2] != "--":
                match = rx.search(parts[1])
                if match:
                    key = match.group(1)
                    value = "".join(parts[3 + parts[2:].index(""):])
                    r.append((key, value))
        return r
    return []
