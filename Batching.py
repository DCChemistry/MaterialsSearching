import multiprocess
import atexit
from functools import wraps

_common_pool = None
def setup():
    global _common_pool
    _common_pool = multiprocess.Pool()
def _join_pool():
    if _common_pool is not None:
        _common_pool.close()
        _common_pool.join()
atexit.register(_join_pool)

import math

class _BatchSentinel():
    pass
BATCH_NONE_RESULT = _BatchSentinel()


@staticmethod
def batch(batch_size):
    def wrap(func):
        @wraps(func)
        def wrapper(results):
            return batch_map(func, results, batch_size)
        return wrapper
    return wrap

def batch_map(func, input_args: list, batch_size: int, callback=None, with_batch=None) -> list:
    """Batch runs a function in different processes using a ProcessPoolExecutor

    Args:
        func: The function to batch
        input_args: A 2d array where each element is the arguments to pass to the function for a given task
        batch_size: The number of tasks to run before collecting
        callback: (optional) A function taking one argument, returning None.
            Called after the completion of each task
            Args:
                result: The result of the task
        with_batch: (optional) A function taking one argument, returning None. 
            Called after the completion of each batch. 
            Args:
                batch_results: An array containing the results of the batch
        
    Returns:
        The array of results
    """
    results = []

    iterations = math.ceil(len(input_args) / batch_size)

    for batch_idx in range(iterations):
        slice_min = batch_idx*batch_size
        slice_max = min((batch_idx+1)*batch_size, len(input_args))

        sliced = input_args[slice_min:slice_max]

        futures = []
        for task in sliced:
            if type(task) != list:
                task = [task]
            future = _common_pool.apply_async(func, task, callback=callback)
            futures.append(future)

        batch = []        
        for future in futures:
            result = future.get()
            if result is not None:
                if result is not BATCH_NONE_RESULT:
                    batch.append(result)
                else:
                    batch.append(None)
        if with_batch is not None:
            with_batch(batch)

        results.extend(batch)

    return results

if __name__ == "__main__":
    import unittest

    setup()

    def chunk(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    TASKS = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11], [11, 12], [12, 13]]
    TASKS_RESULTS = [task[0]*task[1] for task in TASKS]
    BATCH_3_RESULTS = list(chunk(TASKS_RESULTS, 3))
    
    class BatchTest(unittest.TestCase):
        def test_batch_sizes(self):
            """
                Simple canary test for many batch sizes
            """
            def foo(a, b):
                return a * b

            for i in range(0, 5):
                with self.subTest(i=i):
                    results = batch_map(foo, TASKS, i+1)
                    self.assertListEqual(results, TASKS_RESULTS)
        
        def test_batch_results(self):
            """
                Simple canary test for batch results
            """
            def foo(a, b):
                return a * b
            
            batches = []
            results = batch_map(foo, TASKS, 3, with_batch=lambda batch: batches.append(batch))

            self.assertListEqual(results, TASKS_RESULTS)
            self.assertListEqual(batches, BATCH_3_RESULTS)

        def test_lambda(self):
            """
                Simple canary test for batch results
            """
            batches = []
            results = batch_map(lambda a, b: a * b, TASKS, 3, callback=lambda task: print(task), with_batch=lambda batch: batches.append(batch))

            self.assertListEqual(results, TASKS_RESULTS)
            self.assertListEqual(batches, BATCH_3_RESULTS)

        def test_decorator(self):
            @batch(2)
            def foo(value):
                return value * value

            inputs = [1, 2, 3, 4, 5, 6]
            expected = [input*input for input in inputs]
            results = foo(inputs)
            self.assertListEqual(results, expected)

    unittest.main()
