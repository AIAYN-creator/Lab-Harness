"""Plots and regressions: the figures that are usually rebuilt by hand in a spreadsheet.

Linear, polynomial, logarithmic, exponential, power and custom fits, with error bars taken
from the data itself and axis labels the module refuses to do without.

Needs the ``plots`` extra.

    from labharness.modules.plots import Series, regression_plot

    regression_plot(
        output="figures/calibration.pdf",
        series=Series(csv="data/calibration.csv", x="conc", y=["abs_1", "abs_2", "abs_3"]),
        x_label=("Concentration", "mM"),
        y_label=("Absorbance", None),
    )
"""

from labharness.modules.plots.data import Points, Series, read_series
from labharness.modules.plots.figure import PlotResult, regression_plot
from labharness.modules.plots.fits import MODELS, Fit, Parameter, fit

__all__ = [
    "MODELS",
    "Fit",
    "Parameter",
    "Points",
    "PlotResult",
    "Series",
    "fit",
    "read_series",
    "regression_plot",
]
