from mtools.mplotqueries.plottypes.base_type import BasePlotType
import argparse
import types
import numpy as np

try:
    from matplotlib.dates import date2num
except ImportError:
    raise ImportError("Can't import matplotlib. See https://github.com/rueckstiess/mtools/blob/master/INSTALL.md for \
        instructions how to install matplotlib or try mlogvis instead, which is a simplified version of mplotqueries \
        that visualizes the logfile in a web browser.")


from mtools.util.log2code import Log2CodeConverter


class HistogramPlotType(BasePlotType):
    """ plots a histogram plot over all loglines. The bucket size can be specified with the --bucketsize or -b parameter. Unit is in seconds. """

    plot_type_str = 'histogram'
    timeunits = {'sec':1, 's':1, 'min':60, 'm':1, 'hour':3600, 'h':3600, 'day':86400, 'd':86400}
    sort_order = 1
    default_group_by = 'namespace'
    l2cc = Log2CodeConverter()

    def __init__(self, args=None, unknown_args=None):
        BasePlotType.__init__(self, args, unknown_args)

        # parse arguments further to get --bucketsize argument
        self.argparser = argparse.ArgumentParser("mplotqueries --type histogram")
        self.argparser.add_argument('--bucketsize', '-b', action='store', metavar='SIZE', help="histogram bucket size in seconds", default=60)
        sub_args = vars(self.argparser.parse_args(unknown_args))

        self.logscale = args['logscale']
        # get bucket size, either as int (seconds) or as string (see timeunits above)
        bs = sub_args['bucketsize']
        try:
            self.bucketsize = int(bs)
        except ValueError:
            self.bucketsize = self.timeunits[bs]

        self.ylabel = "# occurences per bin"

    def accept_line(self, logline):
        """ return True for each line. We bucket everything. Filtering has to be done before passing to this type of plot. """
        return True

    def log2code(self, logline):
        codeline = self.l2cc(logline.line_str)
        if codeline:
            return ' ... '.join(codeline.pattern)
        else:
            return None

    def plot_group(self, group, idx, axis):
        raise NotImplementedError("Not implemented for histogram plots.")


    def plot(self, axis, ith_plot, total_plots, limits):
        """ Plots the histogram as a whole over all groups, rather than individual groups like other plot types. """
        
        print self.plot_type_str.upper(), "plot"
        print "%5s %9s  %s"%("id", " #points", "group")

        for idx, group in enumerate(self.groups):
            print "%5s %9s  %s"%(idx+1, len(self.groups[group]), group)
        
        print 

        datasets = []
        colors = []
        minx = np.inf
        maxx = -np.inf

        for idx, group in enumerate(self.groups):
            x = date2num( [ logline.datetime for logline in self.groups[group] ] )
            minx = min(minx, min(x))
            maxx = max(maxx, max(x))
            datasets.append(x)
            color, marker = self.color_map(group)
            colors.append(color)
        
        if total_plots > 1:
            # if more than one plot, move histogram to twin axis on the right
            twin_axis = axis.twinx()
            twin_axis.set_ylabel(self.ylabel)
            axis.set_zorder(twin_axis.get_zorder()+1) # put ax in front of ax2 
            axis.patch.set_visible(False) # hide the 'canvas' 
            axis = twin_axis

        n_bins = (maxx-minx)*24.*60.*60./self.bucketsize
        if n_bins > 1000:
            # warning for too many buckets
            print "warning: %i buckets, will take a while to render. consider increasing --bucketsize." % n_bins

        n, bins, artists = axis.hist(datasets, bins=n_bins, align='mid', log=self.logscale, histtype="barstacked", color=colors, edgecolor="white", alpha=0.65, picker=True, label=map(str, self.groups.keys()))
        
        # scale current y-axis to match min and max values
        axis.set_ylim(np.min(n), np.max(n))

        # add meta-data for picking
        if len(self.groups) > 1:
            for g, group in enumerate(self.groups.keys()):
                for i in range(len(artists[g])):
                    artists[g][i]._mt_plot_type = self
                    artists[g][i]._mt_group = group
                    artists[g][i]._mt_n = n[g][i] - (n[g-1][i] if g > 0 else 0)
        else:
            for i in range(len(artists)):
                artists[i]._mt_plot_type = self
                artists[i]._mt_group = group
                artists[i]._mt_n = n[i]

        return artists

    def print_line(self, event):
        """ print group name and number of items in bin. """
        group = event.artist._mt_group
        n = event.artist._mt_n
        print "%4i %s" % (n, group)

