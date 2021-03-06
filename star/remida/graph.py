# -*- coding: utf-8 -*-
# pylint: disable=E1101

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rc
import logging
from tempfile import NamedTemporaryFile

import star.remida.plotters as plotters
from star.remida import utils

__all__ = ['TexGraph', 'HTMLGraph']

TICK_LABEL_LIMIT = 3. # xticks labels length limit
TICK_STEP = 2  # Draw an xtick every n values

FIGSIZE = { # (w, h) in inches
    'stamp': (3.200, 2.0), # (3.180, 2.380)
    'dinamic': (6.360, 2.380),
    'square': (6.360, 6.360),
    'flag': (3.180, 9.52),
    'scpaese': (3.5, 2.2),
}


class Plotters(object):
    ''' Plotter factory.
    This class manage instanciation of concrete implementations of
    BasePlotter by ensuring that there is at most one instance of each
    of them.
    '''

    def __init__(self, graph):
        self._graph = graph
        self._logger = logging.getLogger(type(self).__name__)
        self._plotters = dict()

    def __getitem__(self, key):
        ''' Plotters can be accessed with square brackets notation

        Example:
        >>> plotters = Plotters(myGraph)
        >>> plotters['graphtype'].plot(ax, col)

        '''
        try:
            return self._plotters[key]
        except KeyError:
            try:
                self._plotters[key] = plotters.__getattribute__(key)(self._graph)
            except AttributeError:
                raise KeyError("Unhandled graph type '%s'" % key)
            return self._plotters[key]

    def __setitem__(self, key, value):
        ''' Item assignment not allowed.
        '''
        raise TypeError("'%s' object does not support item assignment" %
                        type(self).__name__)

class Graph(object):

    def __init__(self, data, **kwargs):
        self._logger = logging.getLogger(type(self).__name__)
        rc('legend', **{
                'markerscale': 1,
                'labelspacing': 0,
                'columnspacing': 1,
                'borderpad': 0,
                })
        self._title = data.md.graph.title
        self._footnote = data.md.graph.footnote
        self._df = data.df
        self._y_meta = {}
        self._x_meta = list()
        self._fontsize = data.md.graph.fontsize
        self._lax = None
        try:
            self._size = FIGSIZE[data.md.graph.size]
        except (KeyError, TypeError), e:
            if isinstance(data.md.graph.size, (tuple, list)):
                self._size = data.md.graph.size
            else:
                raise e
        self._legend = data.md.graph.legend
        self._plotters = Plotters(self)
        self.parse_md(data.md.graph.vars)
        self._figure = self.make_graph()

    def _make_legend(self, figure, handles, labels):
        ''' Create legend for the graph, evaluate how the whole figure
        must be scaled to make room for the legend.

        @ param figure: Figure object that must contain the legend
        @ param hadles: list of Line an Path objects used to populate the
             graph.
        @ param labels: list of string used as labels in the legend
        @ return: the new Legend created.

        '''
        # Evaluate number of columns
        ncol = 3
        if len(handles) < 3:
            ncol = 1
        elif len(handles) < 5:
            ncol = 2
        # Estimate new hight needed for the legend
        dheight = ((len(handles)/ncol) + 1) * self._fontsize * 0.01
        dheight_perc = dheight / figure.get_figheight()
        # Scale figure and adjust subplot
        figure.set_figheight(figure.get_figheight() + dheight)
        figure.subplots_adjust(top=(0.9-dheight_perc))
        # Make legend
        leg = figure.legend(handles, labels, ncol=ncol, loc='upper left',
                            bbox_to_anchor=(0.10, 1.0))
        # Remove legend border
        leg.get_frame().set_linewidth(0)

        return leg

    def _unroll_cum(self, md, val):
        ''' Visit bag's md dictionary and make an ordered list of
        those variables that are cumulative to each other. This list
        will be used to stack variables in bar and hbar graphs.
        Orger is top to bottom, so the last value is the one that goes
        to the base.

        @ param md : an md dictionary
        @ param val: an md dictionary entry

        '''
        ret = list()
        if val.get('cumulate'):
            ret = [val.get('cumulate', None)]
            ret += self._unroll_cum(md, md[val['cumulate']])
        return ret

    def parse_md(self, md):
        ''' Parse Bag's md dictionary and estract the following non-public
        attrubutes:

        _lax: Series to use as x axes
        _y_meta: metadata for y ax series
        _x_meta: metadata for x ax series

        '''
        for key, val in md.iteritems():
            val = dict(val)
            if val['type'] == 'lax':
                self._lax = self._df[key].map(float)
                self._x_meta.append(val)
            else:
                val['key'] = key
                val['cumulate'] = self._unroll_cum(md, val)
                var_list = self._y_meta.get(val['type'], [])
                var_list.append(val)
                self._y_meta[val['type']] = var_list

    def _rotate_ticklabels(self, ax):
        ''' Rotate labels on x axes of 30° if they are longer than
        TICK_LABEL_LIMIT
        '''
        for label in ax.get_xticklabels():
            if len(label.get_text()) > TICK_LABEL_LIMIT:
                ax.set_xticklabels([label.get_text() for label in ax.get_xticklabels()], 
                                   rotation=30)
                break

    def make_graph(self):
        ''' Create a Figure and plot a graph in it following what was
        specified in Bag.md.

        @ return: the Figure instance created

        '''
        fig = plt.figure(figsize=self._size)
        ax = fig.add_subplot(1, 1, 1, axisbg='w', autoscale_on=True,
                             adjustable="datalim")
        ax.grid(True)
        lines = []
        labels = []
        for graph_type, cols in self._y_meta.items():
            try:
                line = self._plotters[graph_type].plot(ax, cols)
            except KeyError, err:
                if err.args[0].startswith("Unhandled graph type"):
                    self._logger.warning(
                        "Unhandled graph type '%s', I will ignore entry '%s'",
                        graph_type, [col['key'] for col in cols])
                    continue
                else:
                    raise 
            lines.extend(line)
            labels.extend([col['label'] for col in cols])

        self._rotate_ticklabels(ax)
        if self._legend:
            handles = [line[0] for line in lines]
            self._make_legend(fig, handles, labels)
        return fig

    def out(self):
        ''' You have to extend this class and override this method in
        order to generate a different report format.

        '''
        import cStringIO
        out = cStringIO.StringIO()
        self._figure.savefig(out, format='png')
        out.seek(0)
        return out


class TexGraph(Graph):
    ''' Extends Graph to generate LaTeX rendered graphs; implements out()
    method so that it produce a LaTeX tag ready to be substitued in the
    template.
    '''

    def __init__(self, data, **kwargs):
        ''' Just set some rc params
        '''
        super(TexGraph, self).__init__(data, **kwargs)
        # Tell matplotlib to use LaTeX to render text
        rc('font', **{
                'family': 'serif',
                'serif':['Computer Modern Roman'],
                'size':self._fontsize})
        rc('text', usetex=True)

    def _make_legend(self, figure, handles, labels):
        labels = [utils.escape(label) for label in labels]
        return super(TexGraph, self)._make_legend(figure, handles, labels)

    def out(self):
        ''' Produce a LaTeX compatible tag to be substituted in the
        template.
        '''
        delete = True
        if self._logger.getEffectiveLevel() <= logging.DEBUG:
            delete = False
        fd = NamedTemporaryFile(suffix='.pdf', delete=delete)
        self._figure.savefig(fd, format='pdf')
        # TODO: convert inches to cm
        ret = "\\includegraphics[width=%sin, height=%sin, keepaspectratio=True]{%s}" %\
              (self._size[0], self._size[1], fd.name)
        self._logger.debug("graph file name is '%s'", fd.name)
        return ret, fd

class HTMLGraph(Graph):

    def out(self):
        import base64
        buf = super(HTMLGraph, self).out()
        png_base64 = base64.b64encode(buf.read())
        return '<img src="data:image/png;base64,%s" />' % png_base64
