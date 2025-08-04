from threading import Thread
from threading import Event
from datetime import datetime
import time
import random
import logging

logger = logging.getLogger('networking')

class TaskThread(Thread):
    """
    A thread that executes a target function at intervals following a
    normal distribution for a specified total duration

    This is useful for simulating realistic, non-uniform event timings
    """

    def __init__(self, target_function, duration=20, mean_interval=5, std_dev=1.2, task_name="task", args=(), kwargs=None):
        """
        Initializes the thread.

        Attributes:
            target_function (lambda): The function to be executed periodically
            duration (int): The total time in seconds for the task to run
            mean_interval (float): The average interval (mu) in seconds between function calls
            std_dev (float): The standard deviation (sigma) in seconds of the interval
            task_name (string): The name of the launched task
            args (tuple): A tuple of arguments to pass to the target function
            kwargs (dict): A dictionary of keyword arguments to pass to the target function
        """
        super().__init__()
        if kwargs is None:
            kwargs = {}
        self.target_function = target_function
        self.duration = duration
        self.mean_interval = mean_interval
        self.std_dev = std_dev
        self.task_name = task_name
        self.args = args
        self.kwargs = kwargs
        
        # An Event object allows for gracefully stopping the thread
        self._stop_event = Event()
        
        # Make the thread a daemon so it exits when the main program does
        self.daemon = True

    def run(self):
        """
        The main execution method of the thread. This will be started
        by calling the .start() method on the thread object.
        """
        logger.debug(f"[{datetime.now().strftime('%H:%M:%S.%f')}] ({self.name}): Starting task {self.task_name} for {self.duration} seconds.\n")
        end_time = time.time() + self.duration

        while time.time() < end_time and not self._stop_event.is_set():
            # Execute the target function with its arguments
            res = int(self.target_function(*self.args, **self.kwargs))

            if res != 0:
                logger.warning(f"[{datetime.now().strftime('%H:%M:%S.%f')}] ({self.name}): {self.task_name} request failed (return code {res})\n")
            else:
                logger.debug(f"[{datetime.now().strftime('%H:%M:%S.%f')}] ({self.name}): {self.task_name} request completed (return code {res})\n")

            # Calculate the next wait time from a Gaussian distribution
            # Ensure the wait time is not negative, which can happen if std_dev is large.
            wait_time = random.gauss(self.mean_interval, self.std_dev)
            actual_wait_time = max(0, wait_time)

            # Wait for 'actual_wait_time' seconds or until the event is set.
            self._stop_event.wait(actual_wait_time)
            
        logger.debug(f"[{datetime.now().strftime('%H:%M:%S.%f')}] ({self.name}): Task {self.task_name} finished or was stopped.\n")

    def stop(self):
        """
        Signals the thread to stop its execution loop.
        """
        self._stop_event.set()

