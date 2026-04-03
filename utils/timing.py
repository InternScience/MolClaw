"""
Timing utilities for measuring execution time of tasks.
"""
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any


class TimingContext:
    """Context manager for measuring execution time."""
    
    def __init__(self, task_name: str = "task"):
        self.task_name = task_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.elapsed_time = self.end_time - self.start_time
        return False
    
    def get_elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        if self.elapsed_time is None:
            if self.start_time is None:
                return 0.0
            return time.time() - self.start_time
        return self.elapsed_time
    
    def get_elapsed_formatted(self) -> str:
        """Get elapsed time in human-readable format."""
        elapsed = self.get_elapsed_seconds()
        if elapsed < 60:
            return f"{elapsed:.2f} seconds"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = elapsed % 60
            return f"{minutes} minutes {seconds:.2f} seconds"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = elapsed % 60
            return f"{hours} hours {minutes} minutes {seconds:.2f} seconds"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert timing information to dictionary."""
        return {
            "task_name": self.task_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_seconds": self.get_elapsed_seconds(),
            "elapsed_formatted": self.get_elapsed_formatted()
        }


@contextmanager
def measure_time(task_name: str = "task", verbose: bool = True):
    """
    Context manager for measuring execution time.
    
    Args:
        task_name: Name of the task being measured
        verbose: Whether to print timing information when exiting
    
    Example:
        with measure_time("data_processing"):
            # Your code here
            process_data()
    """
    timer = TimingContext(task_name)
    with timer:
        yield timer
    
    if verbose:
        print(f"[Timing] {task_name} completed in {timer.get_elapsed_formatted()}")


def record_timing(result_dict: Dict[str, Any], timer: TimingContext) -> Dict[str, Any]:
    """
    Add timing information to result dictionary.
    
    Args:
        result_dict: Result dictionary to add timing info to
        timer: TimingContext instance
    
    Returns:
        Result dictionary with timing information added
    """
    if not isinstance(result_dict, dict):
        # If result is not a dict, wrap it
        result_dict = {"result": result_dict}
    
    if "timing" not in result_dict:
        result_dict["timing"] = {}
    result_dict["timing"][timer.task_name] = timer.to_dict()
    return result_dict

