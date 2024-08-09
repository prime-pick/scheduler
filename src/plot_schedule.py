import plotly.express as px
import pandas as pd
import datetime


def plot_schedule(resources):
    tasks = []

    for resource_name, resource in resources.items():
        for task in resource.tasks:
            tasks.append(dict(
                Task=resource_name,
                Start=datetime.datetime.fromtimestamp(task.start, datetime.UTC),
                Finish=datetime.datetime.fromtimestamp(task.end, datetime.UTC),
                Duration=task.duration,
                Product=task.product_id,
                Type=task.type,
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

    fig.show()
