from mininet.node import Host
from tasks.scheduler import TaskScheduler
from urllib.parse import urlunparse
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
        self.scheduler = TaskScheduler()

    def http_request(self, host: Host, url: str, duration: int = 20):
        """
        Send multiple HTTP requests for a certain amount of time

        Attributes:
            host (Host): the host from which the request is sent
            url (str): the target url for the request
            duration (int): the maximum amount of time allowed for request to be sent
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

        http_request = lambda host, url : host.cmd(f"curl -s -o /dev/null {url}; echo $?")
        self.scheduler.start_task(
            task_name='http_request',
            target_function=http_request,
            duration=duration,
            args=(host, complete_url)
        )

    def ftp_request(self, host: Host, url: str, filepath: str, duration: int = 20):
        """
        Send multiple FTP requests for a certain amount of time

        Attributes:
            host (Host): the host from which the request is sent
            url (str): the target url for the request
            filepath (str): the path of the file to download
            duration (int): the maximum amount of time allowed for request to be sent
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

        ftp_request = lambda host, url : host.cmd(f"curl -s -o /dev/null {url}; echo $?")
        self.scheduler.start_task(
            task_name='ftp_request',
            target_function=ftp_request,
            duration=duration,
            args=(host, complete_url)
        )

    def wait_for_completion(self):
        """
        Wait for the completion of the current task
        """
        self.scheduler.join_tasks()

    def stop(self):
        """
        Stop the current task terminating its execution
        """
        self.scheduler.stop_tasks()
