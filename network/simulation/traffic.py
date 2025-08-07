import logging
import random
import numpy as np
from typing import Callable
from mininet.node import Host
from mininet.net import Mininet
from urllib.parse import urlunparse
from http.client import responses
from simulation.taskqueue import TaskQueue
from simulation.task import Task

logger = logging.getLogger('networking')

class TrafficGenerator:
    """
    A generator of network traffic
    """
    def __init__(self, net: Mininet):
        """
        Initiailze traffic generation

        Attributes:
            net (Mininet): a Mininet network
        """
        super().__init__()
        self.net = net

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

    def generate(self, mean_requests_count: int, total_duration: float, time_step: float = 0.1) -> TaskQueue:
        """
        Generate random realistic traffic based on probability distributions

        Attributes:
            mean_request_count (int): the total averge number of requests to send
            total_duration (float): the total duration in seconds of the interval
            time_step (float): the discretize time step duration in seconds

        Returns:
            TaskQueue: a queue of randomly distributed random tasks
        """
        queue = TaskQueue()
        if mean_requests_count <= 0:
            return queue

        # Calculate number of discretize events
        interval_count = int(total_duration / time_step)

        # Average rate of requests for each interval
        mean_request_rate = mean_requests_count / interval_count

        for i in range(interval_count):
            # Get number of requests based on Poisson distribution
            request_count = np.random.poisson(lam=mean_request_rate)

            if request_count > 0:
                # Assign timestamp for each request
                t = i * time_step
                for j in range(request_count):
                    # TODO: Generate random tasks from random hosts
                    task = Task(
                        start_time=t,
                        name=f"http_request-{i}-{j}",
                        callback=self.http_request,
                        args=(self.net.get('h1'), 'www.google.com')
                    )
                    queue.add_task_obj(task)
        return queue

    # def random_request(self) -> Callable:
    #     """
    #     Selects and returns a random request
    #
    #     Returns:
    #         Callable: the selected callable request object or None if no other methods are available
    #     """
    #     # Get a list of all methods bound to this instance
    #     all_methods = inspect.getmembers(self, predicate=inspect.ismethod)
    #
    #     # The name of the current method, so we can exclude it
    #     exclude_filter = ('random_request',)
    #
    #     # Create a list of candidate methods, filtering out any "private"
    #     # methods (starting with '_') and the current method itself.
    #     methods = [
    #         method for name, method in all_methods
    #         if not name.startswith('_') and name not in exclude_filter
    #     ]
    #
    #     # Return a random choice from the candidates, or None if the list is empty
    #     if methods:
    #         return random.choice(methods)
    #     return None
