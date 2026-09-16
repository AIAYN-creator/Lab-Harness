# figures/kapp.pdf -- apparent rate constant against applied current density
from labharness.modules.plots import Series, regression_plot

regression_plot(
    output="figures/kapp.pdf",
    series=Series(csv="data/kapp.csv", x="i", y="k"),
    model="linear",
    x_label=("Current density", "mA cm$^{-2}$"),
    y_label=(r"$k_\mathrm{app}$", "min$^{-1}$"),
)
