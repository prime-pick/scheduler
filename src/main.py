from datetime import timedelta
from timeit import default_timer as timer
from itertools import cycle

from resources import OPERATION_TYPE, MANIPULATOR_COLD, MANIPULATOR_WARM, OVEN2, OVEN3, WARM_ROOM_15, WARM_ROOM_30, \
    Resource, OvenResource
from scheduler import Scheduler
from plot_schedule import plot_schedule
from data_generator import generate_order_distribution, init_seed, generate_orders


def median(data):
    # Sort the list
    data.sort()
    # Calculate the median
    n = len(data)
    if n % 2 == 1:
        # If odd, the median is the middle element
        return data[n // 2]
    else:
        # If even, the median is the average of the two middle elements
        return (data[n // 2 - 1] + data[n // 2]) / 2


def generate_order_sequence(oven_time, warm_room, warm_time):
    return [
        {
            "resource": MANIPULATOR_COLD,
            "type": OPERATION_TYPE["UNLOAD"],
            "duration": 30,
            "priority": 5
        },
        {
            "resource": MANIPULATOR_WARM,
            "type": OPERATION_TYPE["LOAD"],
            "duration": 30,
            "priority": 7
        },
        {
            "resource": OVEN,
            "type": OPERATION_TYPE["OVEN"],
            "duration": oven_time,
            "priority": 5
        },
        {
            "resource": MANIPULATOR_WARM,
            "type": OPERATION_TYPE["UNLOAD"],
            "duration": 30,
            "priority": 5
        },
        # {
        #     "resource": warm_room,
        #     "type": OPERATION_TYPE["STORE"],
        #     "duration": warm_time,
        #     "priority": 5
        # },
    ]


def generate_pickup_sequence():
    return [
        {
            "resource": MANIPULATOR_WARM,
            "type": OPERATION_TYPE["PICKUP"],
            "duration": 30
        },
    ]


init_seed(123)

COUNT = 100

COOK_TIME_BASE = 7 * 60
COOK_TIME_SCALE = 0
COOK_MIN_TIME = 6.5 * 60
COOK_MAX_TIME = 7.5 * 60
COOK_EXTRA_TIME = 30 * 3
PICKUP_MAX_TIME = 50 * 60


order_distribution = generate_orders(count=COUNT, cook_time_base=COOK_TIME_BASE, cook_time_scale=COOK_TIME_SCALE,
                                     cook_min_time=COOK_MIN_TIME, cook_max_time=COOK_MAX_TIME,
                                     cook_extra_time=COOK_EXTRA_TIME, pickup_max_time=PICKUP_MAX_TIME)


bus_time = [
    1, 0, 0, 0, 0, 0, 0, 0, 6, 13, 11, 8, 16, 14, 9, 6, 6, 7, 13, 15, 12, 8, 6, 0
]
# bus_time = [
#     21
# ]
# order_distribution = generate_order_distribution(bus_time=bus_time, cook_time_base=COOK_TIME_BASE,
#                                                  cook_time_scale=COOK_TIME_SCALE,
#                                                  cook_min_time=COOK_MIN_TIME, cook_max_time=COOK_MAX_TIME,
#                                                  cook_extra_time=COOK_EXTRA_TIME, pickup_max_time=PICKUP_MAX_TIME)

# Resources
OVEN = OVEN3
resources = {}
for r in MANIPULATOR_COLD + MANIPULATOR_WARM + OVEN:
    resources[r] = Resource(r) if r not in OVEN else OvenResource(r, 30)
scheduler = Scheduler(resources)

# Calculate

tasks = {}

start = timer()
# Schedule orders
for order in order_distribution:
    order_tasks = scheduler.schedule_forward(
        sequence=generate_order_sequence(order["cook_time"], WARM_ROOM_30, 7200),
        product_id=order["order"],
        start_time=order["start_time"])
    tasks[order["order"]] = order_tasks
end = timer()

# Schedule pickups
# for order in order_distribution:
#     if order["pickup_timeout"]:
#         order_tasks = tasks[order["order"]]
#         actual_end = order_tasks[-1].end
#         (start, end) = scheduler.insert_sequence(
#             sequence=generate_pickup_sequence(),
#             product_id=order["order"],
#             start_time=actual_end + order["pickup_timeout"])

print("===================================================================")
print(f"Ovens: {len(OVEN)}")
print(f"Oven time: {COOK_TIME_BASE}")
print(f"Orders: {len(order_distribution)}")

scheduler.print_resource_utilization(len(order_distribution))

# Print shifted orders
diffs = []
max_diff = 0
max_diff_order = None
for order in order_distribution:
    # if order["start_time"]:
    order_tasks = tasks[order["order"]]
    actual_start = order_tasks[0].start
    actual_end = order_tasks[-1].end
    diff_start = actual_start - order["start_time"]
    if diff_start != 0:
        diffs.append(diff_start)
        if diff_start > max_diff:
            max_diff = diff_start
            max_diff_order = order
        # print(f"Order {order["order"]} shifted: {diff_start}s ({timedelta(seconds=diff_start)})")

print(f"Total shifted: {len(diffs)}")
avg_diff = int(sum(diffs) / len(diffs)) if diffs else 0
print(f"Average shift: {avg_diff}s ({timedelta(seconds=avg_diff)})")
med_diffs = int(median(diffs)) if diffs else 0
print(f"Median shift: {med_diffs}s ({timedelta(seconds=med_diffs)})")
if max_diff_order:
    print(f"Maximum shift (order {max_diff_order["order"]}): {max_diff}s ({timedelta(seconds=max_diff)})")

### Validate timeline
for r in scheduler.resources.values():
    index, invalid_end = r.validate_timeline()
    if index is not None:
        print(f"Invalid timeline {r.name} at {index} in {invalid_end}:")
        for t in r.tasks:
            print(t)

### Deadlock detection
anomalies = scheduler.resources['WARM_HAND'].detect_unload_anomaly()
print(f"Anomalies: {len(anomalies)}")
for a in anomalies:
    print(a)

plot_schedule(resources)
