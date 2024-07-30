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
# OVEN = ["OVEN 1", "OVEN 2", "OVEN 3"]
OVEN = ["OVEN 1", "OVEN 2"]
DISPENSER = ["DISP 1", "DISP 2"]
WARM_ROOM_1 = [f"WR {x}" for x in range(15)]  # Temp 45 Deg Celsius
WARM_ROOM_2 = [f"WR {15 + x}" for x in range(15)]  # Temp 60 Deg Celsius

ALL_RESOURCES = MANIPULATOR_COLD + MANIPULATOR_WARM + OVEN + WARM_ROOM_1  # + WARM_ROOM_2
PRIORITY_UTILIZATION = OVEN
PRIORITY_AVAILABILITY = WARM_ROOM_1  # + WARM_ROOM_2

OPERATION_TYPE = {
    "LOAD": "LOAD",
    "UNLOAD": "UNLOAD",
    "OTHER": "OTHER",
    "BOOK": "BOOK",
    "OVEN": "OVEN",
}

WARM_STORAGE_LIMIT = 7200


def generate_sequence(oven_time, warm_storage):
    return [
        {
            "resource": MANIPULATOR_COLD,
            "type": OPERATION_TYPE["UNLOAD"],
            "duration": 30
        },
        # {
        #     "resource": AIRLOCK,
        #     "type": OPERATION_TYPE["OTHER"],
        #     "duration": 5
        # },
        {
            "resource": MANIPULATOR_WARM,
            "type": OPERATION_TYPE["LOAD"],
            "duration": 30
        },
        {
            "resource": OVEN,
            "type": OPERATION_TYPE["OVEN"],
            "duration": oven_time
        },
        {
            "resource": MANIPULATOR_WARM,
            "type": OPERATION_TYPE["UNLOAD"],
            "duration": 30
        },
        # {
        #     "resource": warm_storage,
        #     "type": OPERATION_TYPE["OTHER"],
        #     "duration": WARM_STORAGE_LIMIT
        # },

    ]


# production_sequence =
generate_sequence(180, WARM_ROOM_1)
# production_sequence

static_colors = [
    '#1f77b4',  # blue
    '#ff7f0e',  # orange
    '#2ca02c',  # green
    '#d62728',  # red
    '#9467bd',  # purple
    '#8c564b',  # brown
    '#e377c2',  # pink
    '#7f7f7f',  # gray
    '#bcbd22',  # yellow-green
    '#17becf',  # teal
    '#393b79',  # dark blue
    '#ff9896',  # light red
    '#98df8a',  # light green
    '#c5b0d5',  # light purple
    '#c49c94',  # light brown
    '#f7b6d2',  # light pink
    '#c7c7c7',  # light gray
    '#dbdb8d',  # light yellow-green
    '#9edae5',  # light teal
]


class Task:
    def __init__(self, start, duration, product_id, resource_name=None, task_type=None, prev_task=None, next_task=None):
        self.start = start
        self.end = start + duration
        self.duration = duration
        self.product_id = product_id
        self.resource_name = resource_name
        self.prev_task = prev_task
        self.next_task = next_task
        self.type = task_type

    def __repr__(self):
        return f'Task(start={self.start}, end={self.end}, duration={self.duration}, product_id={self.product_id}, resource_name={self.resource_name}, type={self.type})'


class Resource:
    def __init__(self, name, time):
        self.name = name
        self.time = time
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)
        self._sort_tasks()

    def _sort_tasks(self):
        self.tasks.sort(key=lambda x: x.start)

    def validate_timeline(self):
        pairs = list(zip_longest(self.tasks, self.tasks[1:], fillvalue=None))
        for pair in pairs:
            if pair[1] == None:
                pass
            elif pair[0].end > pair[1].start:
                return False
        return True

    def detect_unload_anomaly(self):
        pairs = zip_longest(self.tasks, self.tasks[1:])
        anomalies = []
        for pair in pairs:
            if pair[1] is None:
                continue
            if pair[0].product_id != pair[1].product_id:
                if pair[0].type == OPERATION_TYPE["LOAD"] and pair[1].type == OPERATION_TYPE["UNLOAD"]:
                    load_resource = pair[0].next_task.resource_name if pair[0].next_task else None
                    unload_resource = pair[1].prev_task.resource_name if pair[0].prev_task else None
                    if load_resource and load_resource == unload_resource:
                        anomalies.append(pair)
        return anomalies

    def find_time(self, duration, start_time):
        pairs = list(zip_longest(self.tasks, self.tasks[1:], fillvalue=None))
        if not pairs:
            return max(self.time, start_time), 0
        for pair in pairs:
            if pair[1] is None:
                start_time = max(pair[0].end, self.time, start_time)
                return start_time, start_time - pair[0].end

            if pair[0].end >= start_time:
                if pair[1].start - pair[0].end >= duration:
                    return pair[0].end, 0
            if pair[0].end < start_time < pair[1].start:
                if pair[1].start - start_time >= duration:
                    return start_time, start_time - pair[0].end

        return None

    def __repr__(self):
        return f'Resource(name={self.name}, tasks={self.tasks})'


class OvenResource(Resource):
    def __init__(self, name, time, extra_duration):
        super().__init__(name, time)
        self.extra_duration = extra_duration

    def find_time(self, duration, start_time):
        pairs = list(zip_longest(self.tasks, self.tasks[1:], fillvalue=None))
        if not pairs:
            return max(self.time, start_time), 0

        extra = self.extra_duration

        for pair in pairs:
            extra0 = pair[0].next_task.duration if pair[0].next_task else 0
            end0 = pair[0].end + extra0

            if pair[1] is None:
                start_time = max(end0 + extra, self.time, start_time)
                return start_time, start_time - end0

            extra1 = pair[1].prev_task.duration if pair[1].prev_task else 0
            start1 = pair[1].start - extra1

            if end0 >= start_time - extra:
                if start1 - end0 >= duration + 2 * self.extra_duration:
                    return end0 + extra, 0

            if end0 < (start_time - extra) < start1:
                if start_time + duration + extra < start1:
                    return start_time, start_time - end0

        return None


class Scheduler:
    def __init__(self, resources, ovens, time=0):
        self.resources = {}
        self.colors = {}
        self.ovens = ovens
        self.time = time
        for r in resources:
            self.resources[r] = Resource(r, time) if r not in ovens else OvenResource(r, time, 30)

    def print_resource_utilization(self, count):
        ends = [r.tasks[-1].end if r.tasks else 0 for r in self.resources.values()]
        total_time = max(ends)

        print(f"Total time: {datetime.timedelta(seconds=total_time)} ({total_time} sec)")
        products_in_day = 86400 / total_time * count
        print(f"Max products in 24h: {products_in_day}")

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
            (available_start, distance) = resource.find_time(duration, start_time)
            print(f"Planning {product_id}: candidate resource {resource.name} "
                  f"with time slot started at {available_start}, distance = {distance}")
            if available_start < min_start or (available_start == min_start and distance > min_distance):
                min_start = available_start
                target_resource = resource
                min_distance = distance
        task = Task(min_start, duration, product_id, target_resource.name, task_data['type'])
        return target_resource, task

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

    def schedule_forward(self, sequence, product_id):
        self.colors[product_id] = static_colors[len(self.colors) % len(static_colors)]

        # Try to schedule the sequence
        tasks = []
        base_start_time = self.time
        while True:
            print(f"Planning {product_id}: base_start_time = {base_start_time}")
            (tasks, delta) = self.schedule_forward_impl(sequence, base_start_time, product_id)
            if delta > 0:
                base_start_time += delta
            else:
                break

        # Add the tasks to the resources
        for (resource, task) in tasks:
            resource.add_task(task)

    def plot_schedule(self):
        tasks = []

        for resource_name, resource in self.resources.items():
            for task in resource.tasks:
                tasks.append(dict(
                    Task=resource_name,
                    Start=datetime.datetime.fromtimestamp(task.start, datetime.UTC),
                    Finish=datetime.datetime.fromtimestamp(task.end, datetime.UTC),
                    Duration=task.duration,
                    Product=task.product_id,
                    Type=task.type,
                    color=self.colors[task.product_id],
                    product_id=task.product_id
                ))

        df = pd.DataFrame(tasks)
        # df['Start'] = pd.to_datetime(df['Start'])
        # df['Finish'] = pd.to_datetime(df['Finish'])

        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color="Product",
            custom_data=["product_id", "Type"],
            hover_data={"Start": True, "Finish": True, "Duration": True, "Type": True, "Task": False},
        )
        fig.update_layout(
            title='Resource Schedule',
            yaxis_title='Resource',
            showlegend=True,
            xaxis=dict(
                title='Time (seconds)',
                tickformat="%s",
            ),
            clickmode='event+select'
        )

        # fig.update_traces(marker=dict(line=dict(width=0)))

        fig.show()


COUNT = 100
input_data_full = [generate_sequence(x, WARM_ROOM_1) for x in
                   [120, 180, 120, 180, 300, 240, 120, 180, 240, 240, 120] * 10]
# input_data_full = [generate_sequence(x, WARM_ROOM_1) for x in [420, 390, 420, 420, 450, 420, 450, 420, 390, 450] * 10]
# input_data_full = [generate_sequence(x, WARM_ROOM_1) for x in [300, 270, 300, 300, 330, 300, 330, 300, 270, 330] * 10]
input_data = input_data_full[0:COUNT]
print("input len", len(input_data))
initial_time = 0
scheduler = Scheduler(ALL_RESOURCES, PRIORITY_UTILIZATION, initial_time)

start = timer()
for idx, data in enumerate(input_data):
    scheduler.schedule_forward(data, f"product-{idx}")
end = timer()
print(f"Calculation time: {end - start}")

scheduler.print_resource_utilization(COUNT)

### Validate timeline
for r in scheduler.resources.values():
    v = r.validate_timeline()
    if v == False:
        print("Timeline", r.name, v)

### Deadlock detection
anomalies = scheduler.resources['WARM_HAND'].detect_unload_anomaly()
print("Anomalies", len(anomalies))
for a in anomalies:
    print(a)

scheduler.plot_schedule()
