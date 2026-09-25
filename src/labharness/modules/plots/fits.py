"""Fitting a model to measurements, with honest uncertainties.

Non-linear models are fitted as they are, not by taking logarithms: linearising an
exponential distorts the errors and biases the parameters. The linear version is only used to
find a starting point.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from labharness.core.errors import LabHarnessError
from labharness.core.extras import require
from labharness.core.numbers import round_together

MODELS = ("linear", "polynomial", "log", "exp", "power")


@dataclass(frozen=True)
class Parameter:
    name: str
    value: float
    uncertainty: float

    def rounded(self) -> tuple[str, str]:
        """Value and uncertainty rounded together, the way a result is reported."""
        return _round_together(self.value, self.uncertainty)


@dataclass
class Fit:
    model: str
    parameters: tuple[Parameter, ...]
    r_squared: float
    predict: Callable[[Any], Any]
    equation: str

    def __getitem__(self, name: str) -> Parameter:
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter
        raise KeyError(name)


def fit(
    x: Any,
    y: Any,
    error: Any | None = None,
    model: str = "linear",
    degree: int = 2,
    function: Callable[..., Any] | None = None,
    p0: Sequence[float] | None = None,
) -> Fit:
    """Fit ``model`` to the points, weighting by the error bars when there are real ones."""
    numpy = require("numpy", extra="plots")

    if function is None and model not in MODELS:
        raise LabHarnessError(
            f"unknown model '{model}'. Available: {', '.join(MODELS)}, or pass your own function."
        )
    if len(x) <= 1:
        raise LabHarnessError("a fit needs at least two points")

    weights = _weights(numpy, error)

    if function is not None:
        return _fit_function(numpy, x, y, error, function, p0)
    if model == "linear":
        return _fit_polynomial(numpy, x, y, weights, degree=1)
    if model == "polynomial":
        return _fit_polynomial(numpy, x, y, weights, degree=degree)
    if model == "log":
        return _fit_log(numpy, x, y, weights)
    return _fit_curve(numpy, x, y, error, model)


def _weights(numpy: Any, error: Any | None) -> Any | None:
    if error is None:
        return None
    error = numpy.asarray(error, dtype=float)
    if not numpy.all(numpy.isfinite(error)) or numpy.all(error == 0):
        return None
    safe = numpy.where(error > 0, error, numpy.nanmin(error[error > 0]))
    return 1.0 / safe


def _fit_polynomial(numpy: Any, x: Any, y: Any, weights: Any | None, degree: int) -> Fit:
    if len(x) <= degree + 1:
        raise LabHarnessError(
            f"a degree {degree} fit needs at least {degree + 2} points to have an uncertainty"
        )

    coefficients, covariance = numpy.polyfit(x, y, degree, w=weights, cov=True)
    uncertainties = numpy.sqrt(numpy.diag(covariance))
    names = ["slope", "intercept"] if degree == 1 else [f"c{degree - i}" for i in range(degree + 1)]
    parameters = tuple(
        Parameter(name, float(value), float(uncertainty))
        for name, value, uncertainty in zip(names, coefficients, uncertainties, strict=True)
    )

    def predict(values: Any) -> Any:
        return numpy.polyval(coefficients, values)

    equation = (
        f"y = {coefficients[1]:.4g} + {coefficients[0]:.4g}x"
        if degree == 1
        else f"polynomial of degree {degree}"
    )
    return Fit(
        "linear" if degree == 1 else "polynomial",
        parameters,
        _r_squared(numpy, y, predict(x)),
        predict,
        equation,
    )


def _fit_log(numpy: Any, x: Any, y: Any, weights: Any | None) -> Fit:
    if numpy.any(x <= 0):
        raise LabHarnessError("a logarithmic fit needs every x to be greater than zero")

    coefficients, covariance = numpy.polyfit(numpy.log(x), y, 1, w=weights, cov=True)
    uncertainties = numpy.sqrt(numpy.diag(covariance))
    parameters = (
        Parameter("b", float(coefficients[0]), float(uncertainties[0])),
        Parameter("a", float(coefficients[1]), float(uncertainties[1])),
    )

    def predict(values: Any) -> Any:
        return coefficients[1] + coefficients[0] * numpy.log(values)

    equation = f"y = {coefficients[1]:.4g} + {coefficients[0]:.4g} ln x"
    return Fit("log", parameters, _r_squared(numpy, y, predict(x)), predict, equation)


def _fit_curve(numpy: Any, x: Any, y: Any, error: Any | None, model: str) -> Fit:
    optimize = require("scipy.optimize", extra="plots")

    if model == "exp":
        if numpy.any(y <= 0):
            raise LabHarnessError("an exponential fit needs every y to be greater than zero")
        start = numpy.polyfit(x, numpy.log(y), 1)
        guess = [float(numpy.exp(start[1])), float(start[0])]

        def curve(values: Any, a: float, b: float) -> Any:
            return a * numpy.exp(b * values)

        equation_form = "y = {a:.4g} exp({b:.4g}x)"
    else:  # power
        if numpy.any(x <= 0) or numpy.any(y <= 0):
            raise LabHarnessError("a power fit needs every x and y to be greater than zero")
        start = numpy.polyfit(numpy.log(x), numpy.log(y), 1)
        guess = [float(numpy.exp(start[1])), float(start[0])]

        def curve(values: Any, a: float, b: float) -> Any:
            return a * values**b

        equation_form = "y = {a:.4g} x^{b:.4g}"

    values, covariance = _curve_fit(optimize, curve, x, y, error, guess)
    uncertainties = numpy.sqrt(numpy.diag(covariance))
    parameters = (
        Parameter("a", float(values[0]), float(uncertainties[0])),
        Parameter("b", float(values[1]), float(uncertainties[1])),
    )

    def predict(points: Any) -> Any:
        return curve(points, *values)

    equation = equation_form.format(a=values[0], b=values[1])
    return Fit(model, parameters, _r_squared(numpy, y, predict(x)), predict, equation)


def _fit_function(
    numpy: Any,
    x: Any,
    y: Any,
    error: Any | None,
    function: Callable[..., Any],
    p0: Sequence[float] | None,
) -> Fit:
    optimize = require("scipy.optimize", extra="plots")

    values, covariance = _curve_fit(optimize, function, x, y, error, p0)
    uncertainties = numpy.sqrt(numpy.diag(covariance))
    names = list(function.__code__.co_varnames[1 : function.__code__.co_argcount])
    parameters = tuple(
        Parameter(name, float(value), float(uncertainty))
        for name, value, uncertainty in zip(names, values, uncertainties, strict=True)
    )

    def predict(points: Any) -> Any:
        return function(points, *values)

    return Fit(
        "custom",
        parameters,
        _r_squared(numpy, y, predict(x)),
        predict,
        getattr(function, "__name__", "custom model"),
    )


def _curve_fit(
    optimize: Any,
    function: Callable[..., Any],
    x: Any,
    y: Any,
    error: Any | None,
    p0: Sequence[float] | None,
) -> tuple[Any, Any]:
    usable_error = error if error is not None and getattr(error, "any", bool)() else None
    try:
        return optimize.curve_fit(
            function,
            x,
            y,
            p0=p0,
            sigma=usable_error,
            absolute_sigma=usable_error is not None,
            maxfev=10000,
        )
    except RuntimeError as failure:
        raise LabHarnessError(
            f"the fit did not converge: {failure}. Try another model, or pass a starting point "
            "with p0."
        ) from failure


def _r_squared(numpy: Any, y: Any, predicted: Any) -> float:
    residual = float(numpy.sum((y - predicted) ** 2))
    total = float(numpy.sum((y - numpy.mean(y)) ** 2))
    return 1.0 - residual / total if total else 1.0


def _round_together(value: float, uncertainty: float) -> tuple[str, str]:
    """Round a value to the precision its uncertainty justifies: 0.0123 +/- 0.0004.

    Two significant figures in the uncertainty, as for every fitted parameter, rounded in
    decimal on the shortest representation of each float, like the tables.
    """
    from math import isfinite

    if not isfinite(uncertainty) or uncertainty <= 0:
        return f"{value:.4g}", f"{uncertainty:.1g}"
    return round_together(Decimal(repr(value)), Decimal(repr(uncertainty)), significant=2)
