from mininet.node import Host
from urllib.parse import urlunparse
from http.client import responses
import logging

logger = logging.getLogger('networking')

class TrafficGenerator:
    """
    A generator of network traffic
    """
    def __init__(self):
        """
        Create and setup the scheduler for traffic generation
        """
        super().__init__()

    def http_request(self, host: Host, url: str):
        """
        Send a single HTTP requests from an host

        Attributes:
            host (Host): the host from which the request is sent
            url (str): the target url for the request
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

        logger.info(f"Starting {scheme.upper()} request from {host} to {complete_url}\n")
        host.cmd(f"curl -s -o /dev/null {complete_url} &") # TODO: handle and log result

    def ftp_request(self, host: Host, url: str, filepath: str):
        """
        Send multiple FTP requests for a certain amount of time

        Attributes:
            host (Host): the host from which the request is sent
            url (str): the target url for the request
            filepath (str): the path of the file to download
        """
        scheme = 'ftp'
        complete_url = urlunparse((
            scheme,
            url,
            filepath,
            '',
            '',
            ''
        ))

        logger.info(f"Starting {scheme.upper()} request from {host} to {complete_url}\n")
        host.cmd(f"curl -s -o /dev/null {complete_url} &") # TODO: handle and log result
