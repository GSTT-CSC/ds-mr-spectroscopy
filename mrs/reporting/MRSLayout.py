from plotly.graph_objs import Layout, Annotation, Annotations


class MRSLayout(Layout):  # pragma: no cover
    """
    - Defines graph layout options using plotly.graph_objs.Layout for MRS spectra to ensure consistency
    """

    @classmethod
    def getLayout(cls, similarity):
        return Layout(
            annotations=Annotations([
                Annotation(x=1, y=1, showarrow=False,
                           text='Similarity:<br>{}'.format(similarity),
                           bordercolor='#7f7f7f',
                           font=dict(family='-apple-system-headline, San Francisco, sans-serif', color='#7f7f7f',
                                     size=26, ),
                           xref='paper', yref='paper')]),
            title='Normal Paediatric MRS Spectra',
            font=dict(family='-apple-system-headline, San Francisco, sans-serif', size=18, color='#7f7f7f'),
            xaxis=dict(title='Chemical Shift [PPM]', range=[4, 0.2]),
            yaxis=dict(title='Amplitude (a.u.)'))