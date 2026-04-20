import os
import time
import sched
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from logger import LoggerColors
from simulation.traffic import PlaybookEntry, TrafficGenerator
from mininet.net import Mininet
from typing import List, Optional

logger = logging.getLogger('networking')

class Simulation():

    def __init__(self, net: Mininet, traffic_distribution_csv_path: str, website_list_path: str, file_list_path: str, start_time_of_day: float, total_requests_count: int, total_duration: float, time_step: float = 0.1, is_real_time: bool = False, max_workers: int = 20):
        """
        Setup the simulation by generating random requests

        Attributes:
            net (Mininet): a Mininet network
            traffic_distribution_csv_path (str): path to the CSV file with the traffic distribution over a day
            website_list_path (str): path to the JSON website list file
            file_list_path (str): path to the JSON file list file
            start_time_of_day (float): the time of the day when to start the simulation in seconds
            total_requests_count (int): the total number of requests
            total_duration (float): the total duration of the simulation in seconds
            time_step (float): the discretize time step duration in seconds
            is_real_time (bool): True if the simulation time should match the real time False otherwise
        """
        super().__init__()
        traffic = TrafficGenerator(net, website_list_path, file_list_path)
        self.playbook: List[PlaybookEntry] = traffic.generate(total_duration, total_requests_count, traffic_distribution_csv_path, start_time_of_day, time_step)

        self.is_real_time = is_real_time
        self._lock = threading.Lock()
        self.simulation_start_time = 0
        self.start_time_of_day = start_time_of_day
        self.t = 0
        self.scheduler_t = 0
        self._virtual_anchor_t = 0.0
        self._virtual_anchor_wall = 0.0
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix='simulation-worker')
        self._futures = []

        self.scheduler = sched.scheduler(self._clock_time, self._clock_sleep)
        self._due_task_log = None


    # Formats monotonic time into a 'MM:SS.ss' string
    def _format_time(self, t: float) -> str:

        minutes, seconds = divmod(t, 60)
        return f"{int(minutes):02d}:{seconds:05.2f}"

    def _format_time_pretty(self, t: float) -> str:

        return f"{LoggerColors.CYAN}[{self._format_time(t)}]{LoggerColors.RESET}"


    def _clock_time(self) -> float:

        if self.is_real_time:
            return time.monotonic() - self.simulation_start_time
        with self._lock:
            return self.scheduler_t

    def _clock_sleep(self, duration: float):

        if duration <= 0:
            return

        if self.is_real_time:
            time.sleep(duration)
            with self._lock:
                now = time.monotonic() - self.simulation_start_time
                self.scheduler_t = now
                self.t = now
            return

        with self._lock:
            self.scheduler_t += duration
            # Keep a wall-clock anchor so virtual time can continue to progress
            # even when there are no more scheduled events.
            self._virtual_anchor_t = self.scheduler_t
            self._virtual_anchor_wall = time.monotonic()

    def _task_runner(self, task: PlaybookEntry, t: float):
        """
        A wrapper to run each task in its own thread and handle errors

        Attributes:
            task (Task): the task to run
            t (float): the current time
        """
        try:
            with self._lock:
                self.t = max(self.t, task.start_time)

            logger.info(f"{self._format_time_pretty(task.start_time)} Starting task {task.name}...\n")
            task.host.popen(task.command, shell=True)
            logger.debug(f"{self._format_time_pretty(task.start_time)} Succesfully executed task {task.name}\n")
        except Exception as e:
            logger.warning(f"{self._format_time_pretty(task.start_time)} Task {task.name} failed with error {e}\n", exc_info=False)

    def _dispatch_task(self, task: PlaybookEntry):

        if self._due_task_log:
            self._due_task_log.write(f"{task.start_time},{task.start_time},{task.time_of_day},{task.name}\n")

        future = self.executor.submit(self._task_runner, task, task.start_time)
        self._futures.append(future)

    def get_time(self) -> float:

        with self._lock:
            if self.is_real_time or self.simulation_start_time == 0:
                return self.t

            # In virtual mode, continue advancing from the latest scheduler anchor
            # using wall-clock time so packet timestamps do not freeze after the
            # final scheduled event is dispatched.
            now = time.monotonic()
            current_t = self._virtual_anchor_t + max(0.0, now - self._virtual_anchor_wall)
            if current_t > self.t:
                self.t = current_t
            return self.t

    def get_time_of_day(self) -> float:

        return self.get_time() + self.start_time_of_day

    def start(self):

        self.simulation_start_time = time.monotonic()
        with self._lock:
            self.t = 0
            self.scheduler_t = 0
            self._virtual_anchor_t = 0
            self._virtual_anchor_wall = self.simulation_start_time

        logger.info(f"{self._format_time_pretty(0)} Starting simulation...\n")

        due_task_filename = os.getpid() + "-due-task.log"
        due_task_path = os.path.join("debug", due_task_filename)
        self._due_task_log = open(due_task_path, "w")
        self._due_task_log.write("simulation_time,start_time,time_of_day,name\n")

        for task in self.playbook:
            self.scheduler.enterabs(task.start_time, priority=1, action=self._dispatch_task, argument=(task,))

        self.scheduler.run()

        self._due_task_log.close()
        self._due_task_log = None

    def wait_for_completion(self, timeout: Optional[float] = None):

        if not self._futures:
            self.executor.shutdown(wait=True)
            return

        if timeout is None:
            wait(self._futures)
            self.executor.shutdown(wait=True)
            return

        wait(self._futures, timeout=timeout)
        self.executor.shutdown(wait=False)

