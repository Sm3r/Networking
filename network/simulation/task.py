from dataclasses import dataclass, field
from typing import Callable

@dataclass(order=True)
class Task:
    """
    A dataclass to represent a single task in the simulation.
    The 'order=True' parameter makes this class comparable, which is
    required for it to be used in a priority queue (heapq).
    Priority is determined by the 'start_time'.

    Attributes:
        start_time (float): the time at which the task should be started
        name (str): optional task name for identification
        callback (Callable): function to execute
        args (tuple): tuple of arguments used by the function
        kwargs (dict): dictionary of extra arguments
    """
    start_time: float
    callback: Callable = field(compare=False)
    name: str = field(compare=False, default="Task")
    args: tuple = field(compare=False, default=())
    kwargs: dict = field(compare=False, default_factory=dict)
