import json
import logging
import numpy as np
from dataclasses import dataclass
from typing import List
from typing import Optional
from mininet.node import Host
from mininet.net import Mininet
from urllib.parse import urlunparse

logger = logging.getLogger('networking')


@dataclass(frozen=True)
class PlaybookEntry:
    """
    A precomputed traffic action to execute at an absolute simulation timestamp.
    """
    start_time: float
    time_of_day: float
    name: str
    host: Host
    command: str

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

    def _build_http_command(self, url: str) -> str:

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

        return f"curl -s -o /dev/null {complete_url}"

    def _build_ftp_command(self, url: str, filepath: str) -> str:

        scheme = 'ftp'
        complete_url = urlunparse((
            scheme,
            url,
            filepath,
            '',
            '',
            ''
        ))

        return f"curl -s -o /dev/null {complete_url}"

    def _generate_local(self, net: Mininet, simulation_t: float, timestamp: float) -> Optional[PlaybookEntry]:
        """
        Generate random local traffic

        Attributes:
            net (Mininet): a Mininet network
            simulation_t (float): the simulation time of the initial request in seconds
            timestamp (float): the actual time of the day of the initial request in seconds

        Returns:
            Optional[PlaybookEntry]: the randomly generated action or None on failure
        """

        # Get random host to make the request
        host: Host = np.random.choice(net.hosts)
        server: str = np.random.choice(net.topo.servers)

        task = None
        choice = np.random.randint(2)
        if choice == 0:
            task = PlaybookEntry(
                time_of_day=timestamp,
                start_time=simulation_t,
                name=f"local_http_request-{host.name}-{server}",
                host=host,
                command=self._build_http_command(net.get(server).IP())
            )
        elif choice == 1:
            task = PlaybookEntry(
                time_of_day=timestamp,
                start_time=simulation_t,
                name=f"local_ftp_request-{host.name}-{server}",
                host=host,
                command=self._build_ftp_command(net.get(server).IP(), f"file_from_{server}.txt")
            )
        return task
    
    def _generate_remote(self, net: Mininet, simulation_t: float, timestamp: float):
        """
        Generate random remote traffic

        Attributes:
            net (Mininet): a Mininet network
            simulation_t (float): the simulation time of the initial request in seconds
            timestamp (float): the actual time of the day of the initial request in seconds

        Returns:
            Optional[PlaybookEntry]: the randomly generated action or None on failure
        """

        # Get random host to make the request
        host: Host = np.random.choice(net.hosts)

        task = None
        choice = np.random.randint(10)
        if choice < 8:
            url = np.random.choice(self.remote_websites['http_sites'])
            task = PlaybookEntry(
                time_of_day=timestamp,
                start_time=simulation_t,
                name=f"remote_http_request-{host.name}-{url}",
                host=host,
                command=self._build_http_command(url)
            )
        else:
            file = np.random.choice(self.remote_files['ftp_files'])
            base_url = file['base_url']
            filepath = file['file_path']
            
            task = PlaybookEntry(
                time_of_day=timestamp,
                start_time=simulation_t,
                name=f"remote_ftp_request-{host.name}-{base_url}/{filepath}",
                host=host,
                command=self._build_ftp_command(base_url, filepath)
            )
        return task

    def generate(self, total_duration: float, total_requests_count: int,
                 traffic_distribution_csv_path: str, start_time_of_day: float,
                 time_step: float = 0.1) -> List[PlaybookEntry]:
        """
        Generate random realistic traffic based on probability distributions

        Attributes:
            total_duration (float): the total duration in seconds of the interval
            total_request_count (int): the total number of requests to send
            traffic_distribution_csv_path (str): CSV file containing the traffic distribution
            start_time_of_day (float): the time of the day to start sampling from
            time_step (float): the discretize time step duration in seconds

        Returns:
            List[PlaybookEntry]: a sorted static playbook
        """
        playbook: List[PlaybookEntry] = []
        if total_requests_count <= 0 or total_duration <= 0:
            return playbook

        # Load CSV data
        try:
            data = np.loadtxt(traffic_distribution_csv_path, delimiter=',', skiprows=1)
            timestamp = data[:, 0]
            packet_count = data[:, 1]
        except FileNotFoundError:
            logger.error(f"{traffic_distribution_csv_path} not found\n")
            return playbook
        except Exception as e:
            logger.error(f"Error while reading {traffic_distribution_csv_path}: {e}\n")
            return playbook

        # Sample and interpolate traffic data
        seconds_in_an_hour = 60 * 60;
        interval_count = int(total_duration / time_step)
        time_steps = np.arange(interval_count) * time_step 
        timestamps = (start_time_of_day + time_steps) % seconds_in_an_hour 
        sampled_packet_count = np.interp(timestamps, timestamp, packet_count, period=seconds_in_an_hour)
 
        # Add noise
        noise_range = (max(sampled_packet_count) - min(sampled_packet_count)) * 0.06
        noise_packet_count = sampled_packet_count + np.random.uniform(-noise_range, noise_range, len(sampled_packet_count))
        noise_packet_count = noise_packet_count.clip(min=0)
         
        # Rescale to fit total packet count 
        rescaled_packet_count = noise_packet_count - np.min(noise_packet_count)
        rescaled_packet_count /= np.sum(rescaled_packet_count)

        # Distribute packets based on probability distribution 
        expected_packet_count = np.round(total_requests_count * rescaled_packet_count).astype(int)
        diff_packet_count = int(np.floor(total_requests_count - np.sum(expected_packet_count)))

        # Correct packet count error
        if diff_packet_count != 0:
            indices = np.argsort(rescaled_packet_count)[::-1]

            for i in range(abs(diff_packet_count)):
                idx = indices[i % len(indices)]
                if diff_packet_count > 0:
                    expected_packet_count[idx] += 1
                else:
                    expected_packet_count[idx] -= 1

        for i in range(interval_count):
            request_count = expected_packet_count[i]
        
            if request_count > 0:
                simulation_timestamp = time_steps[i]
                t = timestamps[i]
                for _ in range(request_count):
                    # Scegli tra task remoto e locale
                    task = self._generate_local(net=self.net, simulation_t=simulation_timestamp, timestamp=t) if np.random.randint(10) < 7 else self._generate_remote(net=self.net, simulation_t=simulation_timestamp, timestamp=t)
                    if task:
                        playbook.append(task)

        playbook.sort(key=lambda item: item.start_time)

        logger.info(f"Scheduled tasks: {len(playbook)}\n")
        if logger.level >= logging.DEBUG:
            scheduled_filename = "scheduled-task.log"
            logger.debug(f"Logging scheduled task to {scheduled_filename}\n")
            
            scheduled_log = open(scheduled_filename, "w")
            scheduled_log.write("start_time,time_of_day,name\n");
            for task in playbook:
                scheduled_log.write(f"{task.start_time},{task.time_of_day},{task.name}\n")
            scheduled_log.close()
        return playbook
