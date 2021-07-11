""" Plotting examples using pelutils.ds.plot """
import click
import matplotlib.pyplot as plt
import numpy as np

from pelutils.ds.plots import (
    linear_binning, log_binning, normal_binning, get_bins,
    figsize_wide, rc_params, rc_params_small, update_rc_params,
    running_avg, exp_running_avg, running_avg_smoothing, tab_colours
)
from pelutils.ds.distributions import norm, lognorm


@click.command("plots-binning")
def plots_binning():
    # Update params to make them fit nicely with the used figure size
    update_rc_params(rc_params_small)

    # Sample values
    N = 10 ** 5
    bins = 45
    mu, sigma2 = 2, 2
    y = norm(mu, sigma2).rvs(N)
    y_log = lognorm(mu, sigma2).rvs(N)

    # Use a wide figure
    plt.figure(figsize=figsize_wide)

    # Normal distribution using linear binning
    x = np.linspace(y.min(), y.max(), 100)
    plt.subplot(131)
    plt.plot(x, norm(mu, sigma2).pdf(x))
    plt.plot(*get_bins(y, bins=bins), marker=".")
    plt.title("Normal distribution\nLinear binning")
    plt.grid()

    # Normal distribution using normal binning
    plt.subplot(132)
    plt.plot(x, norm(mu, sigma2).pdf(x))
    plt.plot(*get_bins(y, binning_fn=normal_binning, bins=bins), marker=".")
    plt.title("Normal distribution\nNormal binning")
    plt.grid()

    # Log normal distribution using logarithmic binning
    x = np.logspace(np.log10(y_log.min()), np.log10(y_log.max()), 100)
    plt.subplot(133)
    plt.plot(x, lognorm(mu, sigma2).pdf(x))
    plt.plot(*get_bins(y_log, binning_fn=log_binning, bins=bins), marker=".")
    plt.title("Log normal distribution\nLogarithmic binning")
    plt.grid()
    plt.xscale("log")

    plt.tight_layout()
    plt.show()

@click.command("plots-running")
def plots_running():
    update_rc_params(rc_params_small)
    plt.figure(figsize=(30, 20))

    # Generate noisy data
    x = np.linspace(-3, 4)
    y = np.sin(x)
    y += np.random.randn(y.size) / 3

    # Plot data with running average function and few neighbors
    plt.subplot(221)
    plt.scatter(x, y)
    plt.plot(*running_avg(x, y, neighbors=1), c=tab_colours[1])
    plt.title("Running avg., n=1")
    plt.grid()

    # Same but with higher smoothing
    plt.subplot(222)
    plt.scatter(x, y)
    plt.plot(*running_avg(x, y, neighbors=4), c=tab_colours[1])
    plt.title("Running avg., n=4")
    plt.grid()

    # Same but with higher smoothing
    plt.subplot(223)
    plt.scatter(x, y)
    plt.plot(*exp_running_avg(x, y), c=tab_colours[1])
    plt.title(r"Exp. running avg., $\alpha=0.2$")
    plt.grid()

    # Same but with higher smoothing
    plt.subplot(224)
    plt.scatter(x, y)
    plt.plot(*exp_running_avg(x, y, reverse=True), c=tab_colours[1])
    plt.title(r"Reverse exp. running avg., $\alpha=0.2$")
    plt.grid()

    plt.show()


@click.command("plots-smoothing")
def plots_smoothing():
    update_rc_params(rc_params_small)
    plt.figure(figsize=(30, 20))

    # Generate noisy data
    n = 100
    x = np.linspace(-3, 4, n)
    y = np.sin(x)
    y += np.random.randn(n) / 3
    subsample = np.random.randint(0, 2, n).astype(bool)
    subsample[n//2-10:n//2+5] = False
    x, y = x[subsample], y[subsample]

    # Plot data with running average function and few neighbors
    plt.subplot(221)
    plt.scatter(x, y)
    plt.plot(*running_avg(x, y, neighbors=2), c=tab_colours[1])
    plt.title("Running avg., n=2")
    plt.grid()

    # Plot data with running average function and few neighbors
    plt.subplot(222)
    plt.scatter(x, y)
    plt.plot(*running_avg(x, y, neighbors=4), c=tab_colours[1])
    plt.title("Running avg., n=4")
    plt.grid()

    # Running avg. with smoothing
    plt.subplot(223)
    plt.scatter(x, y)
    plt.plot(*running_avg_smoothing(x, y, neighbors=12, samples=300), c=tab_colours[1])
    plt.title("With smoothing, n=12, samples=300")
    plt.grid()

    # Running avg. with more smoothing
    plt.subplot(224)
    plt.scatter(x, y)
    plt.plot(*running_avg_smoothing(x, y, neighbors=20, samples=300), c=tab_colours[1])
    plt.title("With smoothing, n=20, samples=300")
    plt.grid()

    plt.show()
