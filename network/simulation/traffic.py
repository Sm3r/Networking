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

    def _generate_local(self, net: Mininet, simulation_t: float, timestamp: float) -> Optional[Task]:
        """
        Generate random local traffic

        Attributes:
            net (Mininet): a Mininet network
            simulation_t (float): the simulation time of the initial request in seconds
            timestamp (float): the actual time of the day of the initial request in seconds

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
                time_of_day=simulation_t,
                start_time=timestamp,
                callback=self.http_request,
                name=f"local_http_request-{host.name}-{server}",
                args=(host, net.get(server).IP())
            )
        elif choice == 1:
            task = Task(
                time_of_day=simulation_t,
                start_time=timestamp,
                callback=self.ftp_request,
                name=f"local_ftp_request-{host.name}-{server}",
                args=(host, net.get(server).IP(), f"file_from_{server}.txt")
            )
        return task
    
    def _generate_remote(self, net: Mininet, simulation_t: float, timestamp: float):
        """
        Generate random remote traffic

        Attributes:
            net (Mininet): a Mininet network
            simulation_t (float): the simulation time of the initial request in seconds
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
                time_of_day=simulation_t,
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
                time_of_day=simulation_t,
                start_time=timestamp,
                callback=self.ftp_request,
                name=f"remote_ftp_request-{host.name}-{base_url}/{filepath}",
                args=(host, base_url, filepath)
            )
        return task
        pass

    def generate(self, total_duration: float, total_requests_count: int,
                 traffic_distribution_csv_path: str, start_time_of_day: float,
                 time_step: float = 0.1) -> TaskQueue:
        """
        Generate random realistic traffic based on probability distributions

        Attributes:
            total_duration (float): the total duration in seconds of the interval
            total_request_count (int): the total number of requests to send
            traffic_distribution_csv_path (str): CSV file containing the traffic distribution
            start_time_of_day (float): the time of the day to start sampling from
            time_step (float): the discretize time step duration in seconds

        Returns:
            TaskQueue: a queue of randomly distributed random tasks
        """
        queue = TaskQueue()
        if total_requests_count <= 0 or total_duration <= 0:
            return queue

        # Load CSV data
        try:
            data = np.loadtxt(traffic_distribution_csv_path, delimiter=',', skiprows=1)
            timestamp = data[:, 0]
            packet_count = data[:, 1]
        except FileNotFoundError:
            logger.error(f"{traffic_distribution_csv_path} not found")
            return queue
        except Exception as e:
            logger.error(f"Error while reading {traffic_distribution_csv_path}: {e}")
            return queue

        # Sample and interpolate traffic data
        seconds_in_a_day = 86400
        interval_count = int(total_duration / time_step)
        time_steps = np.arange(interval_count) * time_step 
        timestamps = (start_time_of_day + time_steps) % seconds_in_a_day
        sampled_packet_count = np.interp(timestamps, timestamp, packet_count, period=seconds_in_a_day)

        # Add noise
        noise_range = (max(sampled_packet_count) - min(sampled_packet_count)) * 0.05
        noise_packet_count = sampled_packet_count + np.random.uniform(-noise_range, noise_range, len(sampled_packet_count))
        noise_packet_count = noise_packet_count.clip(min=0)
        
        # Rescale to fit total packet count 
        sum_of_weights = np.sum(noise_packet_count)
        scaling_factor = total_requests_count / sum_of_weights
        rescaled_packet_count = noise_packet_count * scaling_factor
        rescaled_packet_count = np.round(rescaled_packet_count)

        for i in range(interval_count):
            request_count = rescaled_packet_count[i]
        
            if request_count > 0:
                simulation_timestamp = time_steps[i]
                t = timestamps[i]
                for _ in range(request_count):
                    # Scegli tra task remoto e locale
                    task = self._generate_local(net=self.net, simulation_t=simulation_timestamp, timestamp=t) if np.random.randint(2) else self._generate_remote(net=self.net, simulation_t=simulation_timestamp, timestamp=t)
                    queue.add_task_obj(task)

        return queue
