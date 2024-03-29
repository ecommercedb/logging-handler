import http.client
import logging.handlers
import socket
from datetime import datetime

import orjson

HOSTNAME = socket.gethostname()


class JsonHttpHandler(logging.handlers.HTTPHandler):
    """Formatter to dump error message into JSON"""

    def mapLogRecord(self, record):
        """
        Default implementation of mapping the log record into a dict
        that is sent as the CGI data. Overwrite in your class.
        Contributed by Franz Glasner.
        """
        record_dict = record.__dict__
        log_record = {
            "levelname": record_dict.get("levelname"),
            "name": record_dict.get("name"),
            "msg": record_dict.get("msg"),
            "module": record_dict.get("module"),
            "hostname": HOSTNAME,
        }

        try:
            created = datetime.fromtimestamp(record_dict.get("created")).isoformat()
            log_record["created"] = created
        except Exception:
            pass

        return log_record

    def getConnection(self, host, secure):
        """
        get a HTTP[S]Connection.

        Override when a custom connection is required, for example if
        there is a proxy.
        """
        import http.client

        if secure:
            connection = http.client.HTTPSConnection(host, context=self.context, timeout=10)
        else:
            connection = http.client.HTTPConnection(host, timeout=10)
        return connection

    def emit(self, record):
        """
        Emit a record.

        Send the record to the web server as a JSON object.
        """
        try:
            host = self.host
            h: http.client.HTTPConnection | http.client.HTTPSConnection = self.getConnection(host, self.secure)
            url = self.url
            data = orjson.dumps(self.mapLogRecord(record))

            if self.method == "GET":
                if url.find("?") >= 0:
                    sep = "&"
                else:
                    sep = "?"
                url = url + "%c%s" % (sep, data)
            h.putrequest(self.method, url)
            if self.method == "POST":
                h.putheader("Content-type", "application/json")
                h.putheader("Content-length", str(len(data)))
            if self.credentials:
                import base64

                s = ("%s:%s" % self.credentials).encode("utf-8")
                s = "Basic " + base64.b64encode(s).strip().decode("ascii")
                h.putheader("Authorization", s)
            h.endheaders()
            if self.method == "POST":
                chunks = [data[i : i + h.blocksize] for i in range(0, len(data), h.blocksize)]
                for chunk in chunks:
                    h.send(chunk)
            h.getresponse()  # can't do anything with the result
        except Exception:
            self.handleError(record)
