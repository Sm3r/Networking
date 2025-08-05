import logging
from mininet.node import Host
from http.client import responses
from urllib.parse import urlunparse
from typing import Any

logger = logging.getLogger('networking')

class Traffic:
    """
    Network traffic generator
    """
    def __init__(self):
        """
        Setup the traffic generator
        """
        super().__init__()

    def _http_success(self, result: Any):
        """
        Function to execute on HTTP request success

        Attributes:
            result (Any): the request result
        """
        logger.debug(f"{result}\n")

    def _http_failure(self, e: Exception):
        """
        Function to execute on HTTP request failure

        Attributes:
            e (Exception): the raised exception
        """
        logger.warning(f"{type(e).__name__}\n")

    def _http_request(self, host: Host, url: str):
        """
        Send a single HTTP GET request from an host to another

        The target host, which IP is located inside the URL, may be either an
        host of the local network or an outside host (internet)

        Attributes:
            host (Host): the host that sends a GET request
            url (str): the target URL of the request
        """
        scheme = 'https'
        path = ''
        complete_url = urlunparse((
            scheme,
            url,
            path,
            '',
            '',
            ''
        ))
        format: str = "%{http_code}"
        result: int = int(host.cmd(f"curl -s -o /dev/null -w '{format} {complete_url}"))
        if result != 200:
            return Exception(f"{result} {responses[result]}")
        return f"{result} {responses[result]}"

