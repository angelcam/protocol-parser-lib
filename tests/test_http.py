from protocolparser.http import HttpRequestReader
from protocolparser.http import HttpResponseReader


class TestRequest:

    def setup_method(self):
        stream = bytes(b'GET /test HTTP/1.0\r\n'
                       b'Transfer-Encoding: identity\r\n'
                       b'Content-Length: 20\r\n'
                       b'Test: foo\r\n bar\r\n'
                       b'\r\n'
                       b'1234567890123456789'
                       )
        self.hrr = HttpRequestReader()
        self.hrr.data_received(stream)

    def test_headers_count(self):
        to_test = len(self.hrr.get_headers())
        assert to_test == 3

    def test_header_value(self):
        hdr = self.hrr.get_header(b'Test').value
        assert hdr == b'foobar'


class TestRequestChunked:

    def setup_method(self):
        stream = bytes(b'GET /test HTTP/1.1\r\n'
                       b'Transfer-Encoding: chunked\r\n'
                       b'Test: foo\r\n bar\r\n'
                       b'\r\n'
                       b'body text')
        self.hrr = HttpRequestReader()
        self.hrr.data_received(stream)

    def test_headers_count(self):
        to_test = len(self.hrr.get_headers())
        assert to_test == 2

    def test_header_value(self):
        hdr = self.hrr.get_header(b'Test').value
        assert hdr == b'foobar'


class TestResponse:

    def setup_method(self):
        stream = bytes(b'HTTP/1.1 200 OK\r\n'
                       b'Transfer-Encoding: chunked\r\n'
                       b'Test: foo\r\n bar\r\n'
                       b'\r\n'
                       b'body text')
        self.hrr = HttpResponseReader()
        self.hrr.data_received(stream)

    def test_headers_count(self):
        to_test = len(self.hrr.get_headers())
        assert to_test == 2

    def test_header_value(self):
        hdr = self.hrr.get_header(b'Test').value
        assert hdr == b'foobar'
