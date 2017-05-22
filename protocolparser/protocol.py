import asyncio
import re

from collections import deque


class LineReader(asyncio.Protocol):
    """
    Line reader protocol allowing to process incoming data as raw binary messages or lines of a text message.
    """

    def __init__(self, delimiter=b"\r\n", buffer_limit=8192):
        """Create a new instance of LineReader protocol.

        :param delimiter: line delimiter (the default delimiter is "\r\n")
        :type delimiter: bytes
        :param buffer_limit: maximum length of a line (the default limit is 8192 bytes)
        :type buffer_limit: int
        """
        self.__delimiter = delimiter
        self.__buffer = bytes()
        self.__buffer_limit = buffer_limit
        self.__raw_mode = False
        self.__processing = False

    def data_received(self, data):
        """
        Incoming data handler.

        :param data: received data
        :type data: bytes
        """
        self.__processing = True
        try:
            consumed = 0
            while consumed < len(data):
                consumed += self.process_data(data[consumed:])
                # process all possibly buffered data in case the raw mode has been enabled
                if self.__raw_mode and len(self.__buffer) > 0:
                    data = self.__buffer + data[consumed:]
                    self.__buffer = bytes()
                    consumed = 0
        finally:
            self.__processing = False

    def process_data(self, data):
        """
        Single data processing step. The method should be called repeatedly (with increasing offset)
        until the whole buffer is processed.

        :param data: data to be processed
        :type data: bytes
        :returns: number of processed bytes
        """
        if self.__raw_mode:
            return self.raw_data_received(data)

        consumed = self.__buffer_limit - len(self.__buffer)
        if consumed <= 0:
            self.line_length_exceeded()
            self.__buffer = bytes()
            return len(data)

        if consumed > len(data):
            consumed = len(data)

        dlen = len(self.__delimiter)
        start = len(self.__buffer) - dlen
        if start < 0:
            start = 0

        self.__buffer += data[:consumed]

        pos = self.__buffer.find(self.__delimiter, start)
        while not self.__raw_mode and pos >= 0:
            line = self.__buffer[:pos]
            rest = self.__buffer[pos + dlen:]
            self.__buffer = rest
            self.line_received(line)
            pos = self.__buffer.find(self.__delimiter)

        return consumed

    def set_raw_mode(self, raw):
        """
        Set raw mode. (Note: If raw == True and the internal line buffer
        contains any data, the buffered data will be processed again.)

        :param raw: raw mode flag
        :type raw: bool
        """
        if self.__raw_mode == raw:
            return
        self.__raw_mode = raw
        # process all possibly buffered data in case the raw mode has
        # been enabled and we are not inside of the processing loop
        if raw and not self.__processing and len(self.__buffer) > 0:
            data = self.__buffer
            self.__buffer = bytes()
            self.data_received(data)

    def line_received(self, line):
        """
        This method is called in text mode when a complete line is received.
        The default implementation does nothing.

        :param line: received line
        :type line: bytes
        """
        return

    def line_length_exceeded(self):
        """
        This method is called in text mode when the current line is longer
        than the internal buffer capacity.
        """
        return

    def raw_data_received(self, data):
        """This method is called in raw mode for every piece of received data.
        """
        return len(data)


class HeaderField:
    """
    Header field envelope.
    """

    def __init__(self, name, value):
        """
        Create a new header field with a given name and value.

        :param name: header name
        :type name: str
        :param value: header value
        :type value: str
        """
        self.name = name
        self.value = value


class HttpLikeMessageReader(LineReader):
    """
    HTTP like message reader protocol.
    """
    first_line_re = re.compile(r"^(?P<first_line>.*)$")

    def __init__(self, max_headers=512, max_line_length=8192):
        """
        Create a new instance of HTTP message reader.

        :param max_headers: maximum number of header fields per message
        :type max_headers: int
        :param max_line_length: maximum length of a single header line
        :type max_line_length: int
        """
        super().__init__(b"\r\n", max_line_length)

        self.__process_line = self.__process_header_line
        self.__header_lines = 0
        self.__last_header_field = None
        self.__header_fields = {}
        self.__max_header_fields = max_headers
        self.__expected = 0

    def reset(self):
        """
        Reset the protocol state and prepare the reader for reading a new
        message.
        """
        self.__process_line = self.__process_header_line
        self.__header_lines = 0
        self.__last_header_field = None
        self.__header_fields = {}
        self.__expected = 0

        self.set_raw_mode(False)

        if not self.is_persistent():
            self.close_connection()

    def get_header(self, name):
        """
        Get request header with a given name.

        :param name: header field name
        :type name: bytes
        :returns: HttpHeader or None
        """
        return self.__header_fields.get(name.lower())

    def get_headers(self):
        """
        Get list of all request headers.
        """
        return self.__header_fields.items()

    def is_persistent(self):
        """
        Check if this is a persistent connection (i.e. the Connection: close
        header is NOT present).
        """
        connection = self.get_header(b"connection")
        if not connection:
            return True
        connection = connection.value.lower()
        return connection != b"close"

    def has_body(self):
        """
        Check if a body is expected.
        """
        return True

    def is_chunked(self):
        """
        Check if the chunked transfer encoding should be used.
        """
        return False

    def get_content_length(self):
        """
        Get content length. None is returned if the header field is not present.
        In such case, the body length should be determined either by the chunked encoding or by closing the connection.
        """
        clength = self.get_header(b"content-length")
        if not clength:
            return None
        return int(clength.value)

    def data_received(self, data):
        try:
            super().data_received(data)
        except Exception as ex:
            self.internal_error(str(ex))

    def line_received(self, line):
        self.__process_line(line)

    def line_length_exceeded(self):
        self.parse_error('line length exceeded')

    def __process_header_line(self, line):
        """
        Process a given header line.
        """
        self.__header_lines += 1

        if self.__header_lines == 1:
            self.first_line_received(line)
        elif len(line) == 0:
            self.__header_end_received()
        else:
            self.__header_line_received(line)

    def __header_line_received(self, line):
        """
        Handle a given header line.
        """
        if line[0] in b" \t":
            if self.__last_header_field:
                self.__last_header_field.value += line.strip()
            else:
                self.parse_error('first header field cannot be a continuation')
        else:
            self.__header_field_received(line)

    def __header_end_received(self):
        """
        Handle header end.
        """
        self.header_received()
        if not self.has_body():
            self.reset()
        elif self.is_chunked():
            self.__process_line = self.__process_chunk_size
        else:
            try:
                self.__expected = self.get_content_length()
                self.set_raw_mode(True)
            except ValueError:
                self.parse_error('unable to decode content length')

    def __header_field_received(self, field):
        """
        Handle a given header field.
        """
        pos = field.find(b":")
        if pos >= 0:
            if len(self.__header_fields) < self.__max_header_fields:
                name = field[:pos].strip()
                value = field[pos + 1:].strip()
                header = HeaderField(name, value)
                name = name.lower()
                self.__header_fields[name] = header
                self.__last_header_field = header
            else:
                self.parse_error('max header fields exceeded')
        else:
            self.parse_error('header field line does not contain ":"')

    def __process_chunk_size(self, line):
        """
        Process a given message line containing the current chunk size.
        """
        ext = line.find(b";")
        if ext >= 0:
            line = line[:ext]

        try:
            self.__expected = int(line, 16)
        except ValueError:
            self.parse_error('unable to decode chunk size')

        if self.__expected > 0:
            self.set_raw_mode(True)
        else:
            self.__process_line = self.__process_trailer

    def __process_chunk_end(self, line):
        """
        Process a given chunk end.
        """
        if len(line) > 0:
            self.parse_error('non-empty line after chunk data')
        else:
            self.__process_line = self.__process_chunk_size

    def __process_trailer(self, line):
        """
        Process a given chunk trailer (we ignore all trailer lines).
        """
        if len(line) > 0:
            return
        self.message_end_received()
        self.reset()

    def raw_data_received(self, data):
        """
        Process received raw data (HTTP message body or chunk).

        :param data: received data
        :type data: bytes
        :returns: number of consumed bytes
        """
        consume = self.__expected
        if consume is None or consume > len(data):
            consume = len(data)
        if self.__expected is not None:
            self.__expected -= consume

        self.body_data_received(data[:consume])

        if self.__expected is None or self.__expected > 0:
            return len(data)

        if self.is_chunked():
            self.__process_line = self.__process_chunk_end
            self.set_raw_mode(False)
        else:
            self.message_end_received()
            self.reset()

        return consume

    def first_line_received(self, line):
        """
        This method is called when the first line of this message is received.

        Dynamically set attrs defined as named params in regexp self.first_line_re

        :param line: the first message line
        :type line: bytes
        """

        line = line.decode('utf-8', 'replace')
        m = self.first_line_re.match(line)
        if m:
            for name, value in m.groupdict().items():
                setattr(self, name, value)
        else:
            self.parse_error('invalid first line')

    def header_received(self):
        """
        This method is called when all HTTP header fields of the current message have been received.
        """
        return

    def body_data_received(self, data):
        """
        This method is called whenever a new piece of body data is received.

        :param data: data
        :type data: bytes
        """
        return

    def message_end_received(self):
        """
        Message end indicator.
        """
        return

    def parse_error(self, msg):
        """
        Process a HTTP request parsing error.

        :param msg: error message
        :type msg: str
        """
        return

    def internal_error(self, msg):
        """
        Process a given internal server error.

        :param msg: error message
        :type msg: str
        """
        return

    def close_connection(self):
        """
        This method is called whenever the underlying connection should be closed.
        """
        return


class HttpLikeRequestReader(HttpLikeMessageReader):
    """
    HTTP like request reader protocol.
    """

    def __init__(self, max_headers=512, max_line_length=8192):
        """
        Create a new HTTP request reader.
        """
        super().__init__(max_headers, max_line_length)

        self.version = None
        self.method = None
        self.url = None

    def get_content_length(self):
        clength = super().get_content_length()
        return clength or 0


class HttpLikeResponseReader(HttpLikeMessageReader):
    """
    HTTP like response reader protocol.
    """

    def __init__(self, max_headers=512, max_line_length=8192):
        """
        Create a new HTTP like response reader.
        """
        super().__init__(max_headers, max_line_length)

        self.version = None
        self.status_code = None
        self.reason_phrase = None

        self.__request_queue = deque()

    def reset(self):
        super().reset()
        if self.__request_queue:
            self.__request_queue.popleft()
        self.version = None
        self.status_code = None
        self.reason_phrase = None

    def push_request(self, method):
        """
        Inform the protocol handler about a request for which a response is expected.

        :param method: request method (e.g. GET, POST, HEAD, etc.)
        :type method: str
        """
        self.__request_queue.append(method.upper())

    def has_body(self):
        if self.__request_queue and self.__request_queue[0] == "HEAD":
            return False
        if self.status_code and 100 <= self.status_code < 200:
            return False
        if self.status_code == 204 or self.status_code == 304:
            return False
        return True
