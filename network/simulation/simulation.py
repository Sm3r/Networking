import time
import logging
import threading
from datetime import datetime
from customlogger.colors import LoggerColors
from simulation.taskqueue import TaskQueue
from simulation.task import Task
from simulation.traffic import TrafficGenerator
from mininet.net import Mininet
from typing import Optional

logger = logging.getLogger('networking')

class Simulation():
    """
    Manages the simulation lifecycle, processing tasks from a TaskQueue
    in a separate thread.
    """
    def __init__(self, net: Mininet, traffic_distribution_csv_path: str, website_list_path: str, file_list_path: str, start_time_of_day: float, total_requests_count: int, total_duration: float, time_step: float = 0.1, is_real_time: bool = False):
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
        traffic = TrafficGenerator(
            net=net,
            website_list_path=website_list_path,
            file_list_path=file_list_path
        )
        self.task_queue = traffic.generate(
            total_duration=total_duration,
            total_requests_count=total_requests_count,
            traffic_distribution_csv_path=traffic_distribution_csv_path,
            start_time_of_day=start_time_of_day,
            time_step=time_step
        )
        self.is_real_time = is_real_time

        self._lock = threading.Lock()
        self.simulation_start_time = 0
        self.start_time_of_day = start_time_of_day
        self.t = 0
        self.active_tasks = []


    def _format_time(self, t: float) -> str:
        """
        Formats monotonic time into a 'MM:SS.ss' string

        Attributes:
            t (float): the total elapsed time in seconds

        Returns:
            str: the formatted time string
        """
        minutes, seconds = divmod(t, 60)
        return f"{int(minutes):02d}:{seconds:05.2f}"

    def _format_time_pretty(self, t: float) -> str:
        """
        Formats monotonic time in a pretty way to be logged

        Attributes:
            t (float): the total elapsed time in seconds

        Returns:
            str: the formatted time string
        """
        return f"{LoggerColors.CYAN}[{self._format_time(t)}]{LoggerColors.RESET}"


    def _task_runner(self, task: Task, t: float):
        """
        A wrapper to run each task in its own thread and handle errors

        Attributes:
            task (Task): the task to run
            t (float): the current time
        """
        try:
            logger.info(f"{self._format_time_pretty(t)} Starting task {task.name}...\n")
            task.callback(*task.args, **task.kwargs)
            logger.debug(f"{self._format_time_pretty(t)} Succesfully executed task {task.name}\n")
        except Exception as e:
            logger.warning(f"{self._format_time_pretty(t)} Task {task.name} failed with error {e}\n", exc_info=False)

    def get_time(self) -> float:
        """
        Get the simulation time

        Returns:
            float: the simulation time
        """
        with self._lock:
            return self.t

    def get_time_of_day(self) -> float:
        """
        Get the simulation time

        Returns:
            float: the simulation time
        """
        with self._lock:
            return self.t + self.start_time_of_day

    def start(self):
        """
        Main simulation loop
        """
        self.simulation_start_time = time.monotonic()

        logger.info(f"{self._format_time_pretty(0)} Starting simulation...\n")

        while True:
            next_task = self.task_queue.peek_next_task()

            if not next_task:
                return
            t = 0

            # Check if simulation is real time
            if self.is_real_time:
                with self._lock:
                    t = self.t = time.monotonic() - self.simulation_start_time

                # If the next task is in the future, wait for it.
                if next_task.start_time > t:
                    wait_duration = next_task.start_time - t
                    time.sleep(wait_duration)
            else:
                with self._lock:
                    t = self.t = next_task.start_time
                # Wait a bit to execute the next task to slow down excessive network traffic
                time.sleep(50 * 1e-3)

            # Run task
            due_task = self.task_queue.get_next_task()
            if due_task:
                task_thread = threading.Thread(
                    target=self._task_runner,
                    args=(due_task, t),
                    name=f"Task-{due_task.name}",
                    daemon=True
                )
                self.active_tasks.append(task_thread)
                task_thread.start()

        logger.warning("{self._format_time_pretty(t)} Simulation loop has been stopped!\n")

    def wait_for_completion(self, timeout: Optional[float] = None):
        """
        Wait for the completion of all tasks

        Attributes:
            timeout (Optional[float]): the maximum allowed time for the completion of all tasks or None to wait indefinitely
        """
        if not timeout:
            [task.join() for task in self.active_tasks]
        else:
            t_end = time.monotonic() + timeout
            for task in self.active_tasks:
                remaining = t_end - time.monotonic()
                task.join(timeout=remaining)

