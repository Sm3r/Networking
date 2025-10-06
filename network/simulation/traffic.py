import json
import logging
import random
import numpy as np
from typing import Callable
from typing import Optional
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
    def __init__(self, net: Mininet, website_list_path: str, file_list_path: str):
        """
        Initiailze traffic generation

        Attributes:
            net (Mininet): a Mininet network
            website_list_path (str): path to the JSON website list file
            file_list_path (str): path to the JSON file list file
        """
        super().__init__()
        self.net = net

        with open(website_list_path, 'r') as f:
            self.remote_websites = json.load(f)
        with open(file_list_path, 'r') as f:
            self.remote_files = json.load(f)

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

        logger.debug(f"Starting {scheme.upper()} request from {host} to {complete_url}\n")
        host.cmd(f"curl -s -o /dev/null {complete_url} &")

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

        logger.debug(f"Starting {scheme.upper()} request from {host} to {complete_url}\n")
        host.cmd(f"curl -s -o /dev/null {complete_url} &")

    def _generate_local(self, net: Mininet, timestamp: float) -> Optional[Task]:
        """
        Generate random local traffic

        Attributes:
            net (Mininet): a Mininet network
            timestamp (float): the time of the initial request in seconds

        Returns:
            Optional[Task]: the randomly generated task or None on failure
        """

        # Get random host to make the request
        host: Host = np.random.choice(net.hosts)
        server: str = np.random.choice(net.topo.servers)

        task = None
        choice = np.random.randint(2)
        if choice == 0:
            task = Task(
                start_time=timestamp,
                callback=self.http_request,
                name=f"local_http_request-{host.name}-{server}",
                args=(host, net.get(server).IP())
            )
        elif choice == 1:
            task = Task(
                start_time=timestamp,
                callback=self.ftp_request,
                name=f"local_ftp_request-{host.name}-{server}",
                args=(host, net.get(server).IP(), f"file_from_{server}.txt")
            )
        return task
    
    def _generate_remote(self, net: Mininet, timestamp: float):
        """
        Generate random remote traffic

        Attributes:
            net (Mininet): a Mininet network
            timestamp (float): the time of the initial request in seconds

        Returns:
            Optional[Task]: the randomly generated task or None on failure
        """

        # Get random host to make the request
        host: Host = np.random.choice(net.hosts)

        task = None
        choice = np.random.randint(2)
        if choice == 0:
            url = np.random.choice(self.remote_websites['http_sites'])
            task = Task(
                start_time=timestamp,
                callback=self.http_request,
                name=f"remote_http_request-{host.name}-{url}",
                args=(host, url)
            )
        elif choice == 1:
            file = np.random.choice(self.remote_files['ftp_files'])
            base_url = file['base_url']
            filepath = file['file_path']
            
            task = Task(
                start_time=timestamp,
                callback=self.ftp_request,
                name=f"remote_ftp_request-{host.name}-{base_url}/{filepath}",
                args=(host, base_url, filepath)
            )
        return task
        pass

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
                t: float = i * time_step
                for j in range(request_count):
                    # Choose between remote and local hosts
                    task = self._generate_local(net=self.net, timestamp=t) if np.random.randint(2) else self._generate_remote(net=self.net, timestamp=t)
                    queue.add_task_obj(task)
        return queue
