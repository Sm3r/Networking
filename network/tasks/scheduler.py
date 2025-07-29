from tasks.task import TaskThread
from mininet.log import info

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

