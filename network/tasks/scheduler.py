from tasks.task import TaskThread

class TaskScheduler:
    """
    A scheduler used to handle multiple task threads
    """

    def __init__(self):
        """
        Initializes the scheduler.
        """
        super().__init__()
        self.tasks = []

    def start_task(self, target_function, duration=20, mean_interval=5, std_dev=1.2, task_name="task", args=(), kwargs=None):
        """
        Create and start a new task on its own thread

        Attributes:
            target_function (lambda): The function to be executed periodically
            duration (int): The total time in seconds for the task to run
            mean_interval (float): The average interval (mu) in seconds between function calls
            std_dev (float): The standard deviation (sigma) in seconds of the interval
            task_name (string): The name of the launched task
            args (tuple): A tuple of arguments to pass to the target function
            kwargs (dict): A dictionary of keyword arguments to pass to the target function
        """
        task = TaskThread(
            target_function=target_function,
            duration=duration,
            mean_interval=mean_interval,
            std_dev=std_dev,
            task_name=task_name,
            args=args,
            kwargs=kwargs
        )
        self.tasks.append(task)
        task.start()

    def join_tasks(self):
        """
        Wait until every task has terminated.
        """
        for task in self.tasks:
            task.join()

    def stop_tasks(self):
        """
        Stop all running tasks.
        """
        for task in self.tasks:
            task.stop()

