import time
import logging
import threading
from datetime import datetime
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
    def __init__(self, net: Mininet, mean_requests_count: int, total_duration: float, time_step: float = 0.1):
        """
        Setup the simulation by generating random requests

        Attributes:
            net (Mininet): a Mininet network
            mean_request_count (int): the total averge number of requests
            total_duration (float): the total duration of the simulation in seconds
            time_step (float): the discretize time step duration in seconds
        """
        super().__init__()
        traffic = TrafficGenerator(net)
        self.task_queue = traffic.generate(
            mean_requests_count=mean_requests_count,
            total_duration=total_duration,
            time_step=time_step
        )

        self.simulation_start_time = 0
        self.active_tasks = []

    def _task_runner(self, task: Task):
        """
        A wrapper to run each task in its own thread and handle errors

        Attributes:
            task (Task): the task to run
        """
        try:
            logger.info(f"[{datetime.now().strftime('%H:%M:%S.%f')}]: Starting task {task.name}...\n")
            task.callback(*task.args, **task.kwargs)
            logger.debug(f"[{datetime.now().strftime('%H:%M:%S.%f')}]: Succesfully executed task {task.name}\n")
        except Exception as e:
            logger.warning(f"[{datetime.now().strftime('%H:%M:%S.%f')}]: Task {task.name} failed with error {e}\n", exc_info=False)

    def start(self):
        """
        Main simulation loop
        """
        self.simulation_start_time = time.monotonic()
        logger.info("Starting simulation...\n")

        while True:
            next_task = self.task_queue.peek_next_task()

            if not next_task:
                return

            current_sim_time = time.monotonic() - self.simulation_start_time
            
            # If the next task is in the future, wait for it.
            if next_task.start_time > current_sim_time:
                wait_duration = next_task.start_time - current_sim_time
                time.sleep(wait_duration)
            
            # Process all tasks that are due to run at the current time
            while True:
                task_to_run = self.task_queue.peek_next_task()
                if not task_to_run or task_to_run.start_time > (time.monotonic() - self.simulation_start_time):
                    break # No more tasks due right now
                
                # Get the task and run it in a new thread for concurrency
                due_task = self.task_queue.get_next_task()
                if due_task:
                    task_thread = threading.Thread(
                        target=self._task_runner,
                        args=(due_task,),
                        name=f"Task-{due_task.name}",
                        daemon=True
                    )
                    self.active_tasks.append(task_thread)
                    task_thread.start()

        logger.warning("Simulation loop has been stopped!\n")

    def wait_for_completion(self, timeout: Optional[float] = None):
        """
        Wait for the completion of all tasks

        Attributes:
            timeout (Optioanl[float]): the maximum allowed time for the completion of all tasks or None to wait indefinitely
        """
        if timeout:
            [task.join() for task in self.active_tasks]
        else:
            t_end = time.monotonic() + timeout
            for task in self.active_tasks:
                remaining = t_end - time.monotonic()
                task.join(timeout=remaining)

