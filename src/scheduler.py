import math
from typing import Dict, Tuple, List
from datetime import timedelta

from resources import Resource, OvenResource, Task


class Scheduler:
    def __init__(self, resources: Dict[str, Resource]):
        self.resources = resources

    def print_resource_utilization(self, count):
        ends = [r.tasks[-1].end if r.tasks else 0 for r in self.resources.values()]
        total_time = max(ends)

        print(f"Total time: {timedelta(seconds=total_time)} ({total_time} sec)")
        products_in_day = 86400 / total_time * count
        print(f"Max products in 24h: {products_in_day}")
        print(f"Max products in 1h: {products_in_day / 24}")

        for r in self.resources.values():
            active_time = sum([task.duration for task in r.tasks])
            if active_time:
                print(
                    f"Resource {r.name}: total time = {total_time}, active_time = {active_time}, utilization = {active_time / total_time}")

    def find_resource(self, task_data, start_time, product_id):
        duration = task_data['duration']
        min_start = math.inf
        target_resource = None
        min_distance = -math.inf
        for resource_name in task_data['resource']:
            resource = self.resources[resource_name]
            (available_start, distance) = resource.find_time(duration, start_time, task_data["priority"])
            print(f"Planning {product_id}: candidate resource {resource.name} "
                  f"with time slot started at {available_start}, distance = {distance}")
            if available_start < min_start or (available_start == min_start and distance > min_distance):
                min_start = available_start
                target_resource = resource
                min_distance = distance
        task = Task(min_start, duration, product_id, target_resource, task_data["type"], task_data["priority"])
        return target_resource, task

    def find_resource_to_insert(self, task_data, start_time, product_id):
        duration = task_data['duration']
        min_start = math.inf
        target_resource = None
        target_index = None
        for resource_name in task_data['resource']:
            resource = self.resources[resource_name]
            (available_start, index) = resource.find_time_to_insert(start_time)
            print(f"Inserting for {product_id}: candidate resource {resource.name} "
                  f"with time slot started at {available_start} at index {index}")
            if available_start < min_start:
                min_start = available_start
                target_resource = resource
                target_index = index
        task = Task(min_start, duration, product_id, target_resource, task_data["type"], task_data["priority"])
        return target_resource, task, target_index

    def schedule_forward_impl(self, sequence, base_start_time, product_id):
        tasks = []  # (resource, task)
        prev_task = None
        for step in sequence:
            if prev_task is None:
                start = base_start_time  # initial start time
            else:
                start = prev_task.end  # start time of the next task

            print(f"Planning {product_id}: task for resource {step["resource"]}, duration {step["duration"]}. "
                  f"Desired start time = {start}")
            (resource, task) = self.find_resource(step, start, product_id)
            print(f"Planning {product_id}: found resource {resource.name} with time slot started at {task.start}")
            task.prev_task = prev_task
            if prev_task:
                prev_task.next_task = task
            tasks.append((resource, task))

            # check if any shift is required
            actual_start = task.start
            delta = actual_start - start
            if delta > 0:
                print(f"Planning {product_id}: schedule shift detected {delta}. Replanning...")
                return tasks, delta

            prev_task = task

        return tasks, 0

    def schedule_forward(self, sequence, product_id, start_time=0) -> List[Task]:
        # Try to schedule the sequence
        base_start_time = start_time
        while True:
            print(f"Planning {product_id}: base_start_time = {base_start_time}")
            (tasks, delta) = self.schedule_forward_impl(sequence, base_start_time, product_id)
            if delta > 0:
                base_start_time += delta
            else:
                break

        # Add the tasks to the resources
        for (resource, task) in tasks:
            resource.insert_task(task, None)

        return [task[1] for task in tasks]

    def insert_sequence(self, sequence, start_time, product_id):
        print(f"Inserting {product_id}: start_time = {start_time}")
        tasks = []  # (resource, task)
        prev_task = None
        for step in sequence:
            if prev_task is None:
                start = start_time  # initial start time
            else:
                start = prev_task.end  # start time of the next task

            print(f"Inserting {product_id}: task for resource {step["resource"]}, duration {step["duration"]}. "
                  f"Desired start time = {start}")
            (resource, task, index) = self.find_resource_to_insert(step, start, product_id)
            print(f"Inserting {product_id}: found resource {resource.name} "
                  f"with time slot started at {task.start} at index {index}")
            task.prev_task = prev_task
            if prev_task:
                prev_task.next_task = task
            tasks.append((resource, task))

            resource.insert_task(task, index)

            prev_task = task

        return tasks[0][1].start, tasks[-1][1].end
