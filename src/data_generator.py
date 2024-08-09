import numpy as np
import random
import math
from datetime import datetime, timedelta
import csv


def round_choose(x, round_to, direction=1):
    if direction == 1:  # ROUND UP
        return x + (round_to - x % round_to)
    elif direction == 0:  # ROUND DOWN
        return x - (x % round_to)


seconds_in_hour = [int(i) for i in np.arange(0, 3600)]

bus_time = [
    1, 0, 0, 0, 0, 0, 0, 0, 6, 13, 11, 8, 16, 14, 9, 6, 6, 7, 13, 15, 12, 8, 6, 0
]


def generate_order_distribution(bus_time, cook_time_base, cook_time_scale, cook_min_time, cook_max_time, cook_extra_time, pickup_max_time):
    tmd = [i for i, bt in enumerate(bus_time) if bt != 0]
    bus_time = [bt for bt in bus_time if bt != 0]

    result = []
    for bt, tm in zip(bus_time, tmd):
        ords = list(range(1, bt + 1))
        cook = generate_cook_times(bt, cook_time_base, cook_time_scale, cook_min_time, cook_max_time)
        wait = generate_pickup_timeouts(bt, pickup_max_time)
        start = random.sample(seconds_in_hour, bt)
        start.sort()

        for i in range(bt):
            order_num = f"{tm}.{ords[i]}"
            cook_time = cook[i]
            wait_time = int(wait[i])
            start_time = int(start[i])
            end_time = start_time + cook_time + cook_extra_time
            pickup_timeout = wait_time
            result.append({
                'order': order_num,
                'hour': tm,
                'cook_time': cook_time,
                'start_time': start_time + 3600 * tm,
                'end_time': end_time + 3600 * tm,
                'pickup_timeout': pickup_timeout
            })

    print("Orders distribution:")
    for row in result[:]:
        print(row)

    return result

def generate_orders(count, cook_time_base, cook_time_scale, cook_min_time, cook_max_time, cook_extra_time, pickup_max_time):
    cook_times = generate_cook_times(count, cook_time_base, cook_time_scale, cook_min_time, cook_max_time)
    pickup_timeouts = generate_pickup_timeouts(count, pickup_max_time)
    return [
        {
            'order': f"order.{i}",
            'hour': 0,
            'cook_time': cook_times[i],
            'start_time': 0,
            'end_time': 0,
            'pickup_timeout': pickup_timeouts[i]
        } for i in range(count)
    ]


def init_seed(seed):
    random.seed(seed)
    np.random.seed(seed)


def generate_pickup_timeouts(count, max_timeout):
    wait = np.random.lognormal(mean=math.log(10), sigma=math.log(2), size=count) * 60
    timeouts = np.minimum(wait, max_timeout)
    return timeouts


def generate_cook_times(count, base_cook_time, scale, min_time, max_time):
    cook_times = np.random.normal(loc=base_cook_time, scale=scale, size=count)
    return [min_time if cook_time <= min_time else (
        max_time if cook_time >= max_time else int(round_choose(cook_time, 30, 0))) for cook_time in cook_times]
