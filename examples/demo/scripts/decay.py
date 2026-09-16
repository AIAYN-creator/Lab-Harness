# figures/decay.pdf -- relative concentration against time, with a first-order fit
#
# The decay is fitted as an exponential, not by taking logarithms of the concentrations:
# linearising the data would distort the error bars and bias the rate constant.
from labharness.modules.plots import Series, regression_plot

regression_plot(
    output="figures/decay.pdf",
    series=Series(csv="data/decay.csv", x="t", y="c"),
    model="exp",
    x_label=("Time", "min"),
    y_label=("$C/C_0$", None),
)
