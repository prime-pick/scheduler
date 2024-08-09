import math
from itertools import zip_longest

import plotly.express as px
import pandas as pd
import datetime
from timeit import default_timer as timer

### Resources
MANIPULATOR_COLD = ["COLD_HAND"]
MANIPULATOR_WARM = ["WARM_HAND"]
AIRLOCK = ["TZ 1", "TZ 2"]  # Aka transition zone
OVEN4 = ["OVEN 1", "OVEN 2", "OVEN 3", "OVEN 4"]
OVEN3 = ["OVEN 1", "OVEN 2", "OVEN 3"]
OVEN2 = ["OVEN 1", "OVEN 2"]
OVEN1 = ["OVEN 1"]
DISPENSER = ["DISP 1", "DISP 2"]
WARM_ROOM_15 = [f"WR {x}" for x in range(15)]
WARM_ROOM_30 = [f"WR {x}" for x in range(33)]

ALL_RESOURCES = MANIPULATOR_COLD + MANIPULATOR_WARM + OVEN3 + WARM_ROOM_30

OPERATION_TYPE = {
    "LOAD": "LOAD",
    "UNLOAD": "UNLOAD",
    "OTHER": "OTHER",
    "BOOK": "BOOK",
    "OVEN": "OVEN",
    "PICKUP": "PICKUP",
    "STORE": "STORE",
}

WARM_STORAGE_LIMIT = 7200


class Task:
    def __init__(self, start, duration, product_id, resource, task_type, priority):
        self.start = start
        self.end = start + duration
        self.duration = duration
        self.product_id = product_id
        self.resource = resource
        self.prev_task = None
        self.next_task = None
        self.type = task_type
        self.priority = priority

    def __repr__(self):
        return f'Task(start={self.start}, end={self.end}, duration={self.duration}, product_id={self.product_id}, resource_name={self.resource.name}, type={self.type})'

    def shift(self, delta):
        self.start += delta
        self.end += delta

    def shift_all(self, delta):
        self.shift(delta)

        next_task = self.next_task
        while next_task:
            next_task.shift(delta)
            next_task.resource.align_tasks(start_task=next_task)
            next_task = next_task.next_task


class Resource:
    def __init__(self, name):
        self.name = name
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)
        self._sort_tasks()

    def get_total_time(self):
        for task in reversed(self.tasks):
            if task.type != OPERATION_TYPE["PICKUP"]:
                return task.end

        return 0

    def _sort_tasks(self):
        self.tasks.sort(key=lambda x: x.start)

    def validate_timeline(self):
        pairs = list(zip_longest(self.tasks, self.tasks[1:], fillvalue=None))
        for index, pair in enumerate(pairs):
            if pair[1] == None:
                pass
            elif pair[0].end > pair[1].start:
                return index, pair[0].end
        return None, None

    def detect_unload_anomaly(self):
        pairs = zip_longest(self.tasks, self.tasks[1:])
        anomalies = []
        for pair in pairs:
            if pair[1] is None:
                continue
            if pair[0].product_id != pair[1].product_id:
                if pair[0].type == OPERATION_TYPE["LOAD"] and pair[1].type == OPERATION_TYPE["UNLOAD"]:
                    load_resource = pair[0].next_task.resource.name if pair[0].next_task else None
                    unload_resource = pair[1].prev_task.resource.name if pair[0].prev_task else None
                    if load_resource and load_resource == unload_resource:
                        anomalies.append(pair)
        return anomalies

    def find_time(self, duration, start_time, priority):
        pairs = list(zip_longest(self.tasks, self.tasks[1:], fillvalue=None))
        if not pairs:
            return start_time, 0
        for index, pair in enumerate(pairs):
            if index == 0:
                if start_time + duration < pair[0].start:
                    # insert before pair[0]
                    return start_time, 0

            if pair[1] is None:
                # insert after pair[0]
                start_time = max(pair[0].end, start_time)
                return start_time, start_time - pair[0].end

            # can insert before next

            possibly_start = max(pair[0].end, start_time)
            if possibly_start + duration <= pair[1].start:
                return possibly_start, possibly_start - pair[0].end

            # check priority
            # FIXME: hack to prevent load-unload anomaly
            if pair[1].priority < priority and pair[0].priority != priority and pair[1].priority != priority:
                return possibly_start, possibly_start - pair[0].end

        return None

    # returns: actual_start_time, index_where_insert, shift for the next tasks
    def find_time_to_insert(self, start_time):
        if not self.tasks:
            return start_time, 0
        for index, task in enumerate(self.tasks):
            # insert before task
            if start_time < task.start:
                return start_time, index

            # insert after task but before next if any
            if index + 1 == len(self.tasks) or start_time < self.tasks[index+1].start:
                return max(task.end, start_time), index + 1

        return None

    def insert_task(self, task, index):
        print(f"Resource {self.name}: inserting {task.product_id} with start {task.start} at index {index}...")

        if index is None:
            index = self.find_index_by_time(task.start)

        # insert task
        self.tasks.insert(index, task)

        # align next tasks
        self.align_tasks(index=index)
        print(f"Resource {self.name}: inserted {task.product_id}")

    def find_index_by_time(self, start_time):
        for index, task in enumerate(self.tasks):
            if start_time <= task.start:
                return index
        return len(self.tasks)

    def align_tasks(self, start_task=None, index=None):
        print(f"Resource {self.name}: aligning tasks from {start_task.product_id if start_task else index}...")

        index = index if index is not None else self.tasks.index(start_task) if start_task is not None else 0
        prev_end = self.tasks[index].end

        # shift next tasks
        for i in range(index+1, len(self.tasks)):
            task = self.tasks[i]
            shift = prev_end - task.start
            if shift <= 0:
                break

            print(f"Resource {self.name}: shifting task {task.product_id} at {i} in {task.start} for {shift}")
            task.shift_all(shift)

            prev_end = task.end

    def __repr__(self):
        return f'Resource(name={self.name}, tasks={self.tasks})'


class OvenResource(Resource):
    def __init__(self, name, extra_duration):
        super().__init__(name)
        self.extra_duration = extra_duration

    def find_time(self, duration, start_time, priority):
        pairs = list(zip_longest(self.tasks, self.tasks[1:], fillvalue=None))
        if not pairs:
            return start_time, 0

        extra = self.extra_duration

        for pair in pairs:
            end0 = pair[0].end + self.extra_duration

            if pair[1] is None:
                start_time = max(end0 + extra, start_time)
                return start_time, start_time - end0

            start1 = pair[1].start - self.extra_duration

            if end0 >= start_time - extra:
                if start1 - end0 >= duration + extra:
                    return end0 + extra, 0

            if end0 < (start_time - extra) < start1:
                if start_time + duration + extra < start1:
                    return start_time, start_time - end0

        return None
