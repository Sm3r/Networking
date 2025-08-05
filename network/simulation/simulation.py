import time
import threading
import logging
from datetime import datetime
from simulation.taskqueue import TaskQueue
from simulation.task import Task
from typing import Optional

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
   
        # Track active threads with a list
        self._active_threads = []
        self._threads_lock = threading.Lock()

    def _task_runner(self, task: Task):
        """
        A wrapper to run each task in its own thread and handle errors

        Attributes:
            task (Task): the task to run
        """
        try:
            logger.info(f"[{datetime.now().strftime('%H:%M:%S.%f')}] Starting task {task.name}...\n")
            result = task.callback(*task.args, **task.kwargs)
            logger.debug(f"[{datetime.now().strftime('%H:%M:%S.%f')}]: Succesfully executed task {task.name}\n")

            # If an on_success callback exists, call it with the result
            if task.on_success:
                try:
                    task.on_success(result)
                except Exception as cb_e:
                    logger.warning(f"On_success callback for task '{task.name}' failed with error {cb_e}\n")
        except Exception as e:
            logger.warning(f"[{datetime.now().strftime('%H:%M:%S.%f')}] Task {task.name} failed with error {e}\n", exc_info=False)

            # If an on_failure callback exists, call it with the exception
            if task.on_failure:
                try:
                    task.on_failure(e)
                except Exception as cb_e:
                    logger.warning(f"On_error callback for task '{task.name}' failed with error {cb_e}\n")

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
                    # Track active thread
                    with self._threads_lock:
                        self._active_threads.append(task_thread)
                    task_thread.start()

        logger.info("Simulation loop has been stopped\n")

    def stop(self):
        """Signals the simulation to stop gracefully."""
        logger.info("Stop signal received. Shutting down simulation...\n")
        self._stop_event.set()

    def join(self, timeout: Optional[float] = None):
        """
        Overrides the default join method

        It first waits for the main simulation loop (the thread itself) to
        finish, and then waits for all dispatched task threads to complete.

        Attributes:
            timeout (float): maximum allowed amount of time to wait for the execution
        """
        # Wait for the main scheduler thread to finish
        super().join(timeout)
        
        logger.info('Waiting for all dispatched tasks to complete...\n')
        with self._threads_lock:
            threads_to_wait_for = list(self._active_threads)

        for thread in threads_to_wait_for:
            thread.join() # This blocks until the individual task thread is done
        
        logger.info("All dispatched tasks have completed!\n")
