import logging
import threading
import heapq
from typing import Callable, Optional
from simulation.task import Task

logger = logging.getLogger('networking')

class TaskQueue:
    """
    A priority queue for storing and retrieving tasks based on their
    scheduled start time.
    """
    def __init__(self):
        self._tasks = []
        self._lock = threading.Lock()

    def size(self):
        return len(self._tasks)

    def add_task_obj(self, task: Task):
        with self._lock:
            heapq.heappush(self._tasks, task)
        logger.debug(f"Task '{task.name}' scheduled at T={task.start_time:.2f}s\n")

    def add_task(self, start_time: float, simulation_t: float, callback: Callable, name: str = None, args: tuple = None, kwargs: dict = None):
        """
        Adds a new task to the queue.

        Attributes:
            start_time (float): the simulation time (in seconds) when the task should run
            simulation_t (float): the time of the day (in seconds) when the task should run
            callback (Callable): the function to execute for this task
            name (str): an optional name for the task for logging
            args (tuple): a tuple of arguments for the target function
            kwargs (dict): a dictionary of keyword arguments for the target function
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        if name is None:
            name = callback.__name__

        task = Task(
            time_of_day=simulation_t,
            start_time=start_time,
            name=name,
            callback=callback,
            args=args,
            kwargs=kwargs
        )
        self.add_task_obj(task)

    def get_next_task(self) -> Optional[Task]:
        """
        Pops and returns the next task with the lowest start time

        Returns:
            Task | None: the task to execute or None if none
        """
        with self._lock:
            if self._tasks:
                return heapq.heappop(self._tasks)
            return None

    def peek_next_task(self) -> Optional[Task]:
        """
        Returns the next task without removing it from the queue

        Returns:
            Task | None: the task to execute or None if none
        """
        with self._lock:
            if self._tasks:
                return self._tasks[0]
            return None

