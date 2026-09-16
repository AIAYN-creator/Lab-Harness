# figures/calibration.pdf -- calibration curve, three replicates per point
#
# The CSV is a spreadsheet export in a language that uses the comma as the decimal mark;
# LabHarness reads it as it is. The error bars are the standard deviation of the replicates,
# and the fitted slope is written to figures/calibration.fit.tex for the text to cite.
from labharness.modules.plots import Series, regression_plot

regression_plot(
    output="figures/calibration.pdf",
    series=Series(csv="data/calibration.csv", x="conc", y=["abs_1", "abs_2", "abs_3"]),
    model="linear",
    x_label=("Concentration", "mM"),
    y_label=("Absorbance", None),
)
