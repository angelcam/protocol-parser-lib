import re

from .protocol import HttpLikeRequestReader, HttpLikeResponseReader


class RtspRequestReader(HttpLikeRequestReader):
    """
    HTTP request reader protocol.

    There are several methods which are called during processing request. Default implementation do nothing.

    header_received(self): This method is called when all HTTP header fields of the current message have been received.
    body_data_received(self, data): This method is called whenever a new piece of body data is received.
    message_end_received(self): This method is called when message end is reached.
    parse_error(self, msg): This method is called when parse error occurred.
    internal_error(self, msg): This method is called when internal server error occurred.
    close_connection(self): This method is called whenever the underlying connection should be closed.
    """
    first_line_re = re.compile(r"^(?P<method>\S+) (?P<url>\S*) RTSP/(?P<version>\d\.\d)$")


class RtspResponseReader(HttpLikeResponseReader):
    """
    HTTP response reader protocol.

    There are several methods which are called during processing request. Default implementation do nothing.

    header_received(self): This method is called when all HTTP header fields of the current message have been received.
    body_data_received(self, data): This method is called whenever a new piece of body data is received.
    message_end_received(self): This method is called when message end is reached.
    parse_error(self, msg): This method is called when parse error occurred.
    internal_error(self, msg): This method is called when internal server error occurred.
    close_connection(self): This method is called whenever the underlying connection should be closed.
    """

    first_line_re = re.compile(r"^RTSP/(?P<version>\d\.\d) (?P<status_code>\d{3}) (?P<reason_phrase>.*)$")
