import time
import threading
import logging
from datetime import datetime
from simulation.taskqueue import TaskQueue
from simulation.task import Task

logger = logging.getLogger('networking')

class Simulation(threading.Thread):
    """
    Manages the simulation lifecycle, processing tasks from a TaskQueue
    in a separate thread.
    """
    def __init__(self, task_queue: TaskQueue):
        """
        Configure the simulation
 
        Attributes:
            task_queue (TaskQueue): task queue to process
        """
        super().__init__(name="MainSimulationThread")
        self.task_queue = task_queue
        self._stop_event = threading.Event()
        self._simulation_start_time = 0
        self.daemon = True # Allows main program to exit even if this thread is running

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

    def run(self):
        """The main simulation loop. Do not call this directly; use start()"""
        self._simulation_start_time = time.monotonic()
        logger.info("Starting simulation...\n")

        while not self._stop_event.is_set():
            next_task = self.task_queue.peek_next_task()

            if not next_task:
                logger.info("Simulation terminated!\n")
                return

            current_sim_time = time.monotonic() - self._simulation_start_time
            
            # If the next task is in the future, wait for it.
            if next_task.start_time > current_sim_time:
                wait_duration = next_task.start_time - current_sim_time
                # Use event.wait() instead of sleep() for immediate interruption
                self._stop_event.wait(wait_duration)
                # If wait was interrupted by stop(), re-check the loop condition
                if self._stop_event.is_set():
                    break
            
            # Process all tasks that are due to run at the current time
            while True:
                task_to_run = self.task_queue.peek_next_task()
                if not task_to_run or task_to_run.start_time > (time.monotonic() - self._simulation_start_time):
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
                    task_thread.start()

        logger.info("Simulation loop has been stopped\n")

    def stop(self):
        """Signals the simulation to stop gracefully."""
        logger.info("Stop signal received. Shutting down simulation...\n")
        self._stop_event.set()
