import plotly
import os

import plotly.graph_objs as go
import pandas as pd

from mrs.reporting.MRSLayout import MRSLayout


class Chart:

    def __init__(self, chart_name):
        self.name = chart_name
        self.graph = go

    def create(self, traces: list = None, filename: str = None, figure=None):

        if filename:
            self.name = filename + '_chart.html'
        if figure:
            return plotly.offline.plot(figure, filename=self.name, auto_open=False)
        elif traces:
            return plotly.offline.plot(traces, filename=self.name, auto_open=False)
        else:
            raise Exception('No trace or figure defined.')


class MRSNormalChart(Chart):  # pragma: no cover
    """
    Plotly Trace and 2DHistogram of normal MRS data for comparison with patient data
    """

    def __init__(self):
        self.chart = super().__init__('normal_mrs')

    def get_trace(self):
        normal_mrs = pd.read_csv(SETTINGS.get('mrs', 'normal_mrs_csv'))

        # clip data
        # cols = ['PPMScale']
        # normal_mrs[cols] = normal_mrs[normal_mrs[cols] > 0.2 ][cols]
        # normal_mrs.dropna()
        # normal_mrs[cols] = normal_mrs[normal_mrs[cols] < 4 ][cols]
        # normal_mrs.dropna()

        x_data = normal_mrs['PPMScale']
        y_data = normal_mrs['Fit']

        trace = self.graph.Histogram2dContour(x=x_data, y=y_data,
                                              name='density',
                                              colorscale='Jet',
                                              contours={'coloring': 'heatmap'},
                                              nbinsx=150, nbinsy=150)

        return trace

    def get_chart(self):
        if os.path.isfile(self.chart.name):
            return self.chart.name

        trace = self.get_trace()

        layout = MRSLayout.get

        fig = self.graph.Figure(data=[trace], layout=layout)

        return self.chart.create(filename=self.chart.name, figure=fig)
