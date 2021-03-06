from netlib import utils, tutils
from netlib.http import Headers

def test_bidi():
    b = utils.BiDi(a=1, b=2)
    assert b.a == 1
    assert b.get_name(1) == "a"
    assert b.get_name(5) is None
    tutils.raises(AttributeError, getattr, b, "c")
    tutils.raises(ValueError, utils.BiDi, one=1, two=1)


def test_hexdump():
    assert utils.hexdump("one\0" * 10)


def test_cleanBin():
    assert utils.clean_bin(b"one") == b"one"
    assert utils.clean_bin(b"\00ne") == b".ne"
    assert utils.clean_bin(b"\nne") == b"\nne"
    assert utils.clean_bin(b"\nne", False) == b".ne"
    assert utils.clean_bin(u"\u2605".encode("utf8")) == b"..."

    assert utils.clean_bin(u"one") == u"one"
    assert utils.clean_bin(u"\00ne") == u".ne"
    assert utils.clean_bin(u"\nne") == u"\nne"
    assert utils.clean_bin(u"\nne", False) == u".ne"
    assert utils.clean_bin(u"\u2605") == u"\u2605"


def test_pretty_size():
    assert utils.pretty_size(100) == "100B"
    assert utils.pretty_size(1024) == "1kB"
    assert utils.pretty_size(1024 + (1024 / 2.0)) == "1.5kB"
    assert utils.pretty_size(1024 * 1024) == "1MB"


def test_parse_url():
    assert not utils.parse_url("")

    u = "http://foo.com:8888/test"
    s, h, po, pa = utils.parse_url(u)
    assert s == "http"
    assert h == "foo.com"
    assert po == 8888
    assert pa == "/test"

    s, h, po, pa = utils.parse_url("http://foo/bar")
    assert s == "http"
    assert h == "foo"
    assert po == 80
    assert pa == "/bar"

    s, h, po, pa = utils.parse_url("http://user:pass@foo/bar")
    assert s == "http"
    assert h == "foo"
    assert po == 80
    assert pa == "/bar"

    s, h, po, pa = utils.parse_url("http://foo")
    assert pa == "/"

    s, h, po, pa = utils.parse_url("https://foo")
    assert po == 443

    assert not utils.parse_url("https://foo:bar")
    assert not utils.parse_url("https://foo:")

    # Invalid IDNA
    assert not utils.parse_url("http://\xfafoo")
    # Invalid PATH
    assert not utils.parse_url("http:/\xc6/localhost:56121")
    # Null byte in host
    assert not utils.parse_url("http://foo\0")
    # Port out of range
    assert not utils.parse_url("http://foo:999999")
    # Invalid IPv6 URL - see http://www.ietf.org/rfc/rfc2732.txt
    assert not utils.parse_url('http://lo[calhost')


def test_unparse_url():
    assert utils.unparse_url("http", "foo.com", 99, "") == "http://foo.com:99"
    assert utils.unparse_url("http", "foo.com", 80, "") == "http://foo.com"
    assert utils.unparse_url("https", "foo.com", 80, "") == "https://foo.com:80"
    assert utils.unparse_url("https", "foo.com", 443, "") == "https://foo.com"


def test_urlencode():
    assert utils.urlencode([('foo', 'bar')])


def test_urldecode():
    s = "one=two&three=four"
    assert len(utils.urldecode(s)) == 2


def test_get_header_tokens():
    headers = Headers()
    assert utils.get_header_tokens(headers, "foo") == []
    headers["foo"] = "bar"
    assert utils.get_header_tokens(headers, "foo") == ["bar"]
    headers["foo"] = "bar, voing"
    assert utils.get_header_tokens(headers, "foo") == ["bar", "voing"]
    headers.set_all("foo", ["bar, voing", "oink"])
    assert utils.get_header_tokens(headers, "foo") == ["bar", "voing", "oink"]


def test_multipartdecode():
    boundary = 'somefancyboundary'
    headers = Headers(
        content_type='multipart/form-data; boundary=%s' % boundary
    )
    content = "--{0}\n" \
              "Content-Disposition: form-data; name=\"field1\"\n\n" \
              "value1\n" \
              "--{0}\n" \
              "Content-Disposition: form-data; name=\"field2\"\n\n" \
              "value2\n" \
              "--{0}--".format(boundary)

    form = utils.multipartdecode(headers, content)

    assert len(form) == 2
    assert form[0] == ('field1', 'value1')
    assert form[1] == ('field2', 'value2')


def test_parse_content_type():
    p = utils.parse_content_type
    assert p("text/html") == ("text", "html", {})
    assert p("text") is None

    v = p("text/html; charset=UTF-8")
    assert v == ('text', 'html', {'charset': 'UTF-8'})
