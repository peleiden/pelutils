""" Plotting examples using pelutils.ds.plot """
import click
import matplotlib.pyplot as plt
import numpy as np

from pelutils.ds.plots import (
    log_binning, normal_binning, histogram,
    moving_avg, exp_moving_avg, double_moving_avg, tab_colours,
    Figure,
)
from pelutils.ds.distributions import norm, lognorm


@click.command("plots-binning")
def plots_binning():

    # Sample values
    N = 10 ** 5
    bins = 45
    mu, sigma2 = 2, 2
    y = norm(mu, sigma2).rvs(N)
    y_log = lognorm(mu, sigma2).rvs(N)

    with Figure("plots-binning.png", figsize=(22, 10)):
        # Normal distribution using linear binning
        x = np.linspace(y.min(), y.max(), 100)
        plt.subplot(131)
        plt.plot(x, norm(mu, sigma2).pdf(x))
        plt.plot(*histogram(y, bins=bins), marker=".")
        plt.title("Normal distribution\nLinear binning")
        plt.grid()

        # Normal distribution using normal binning
        plt.subplot(132)
        plt.plot(x, norm(mu, sigma2).pdf(x))
        plt.plot(*histogram(y, binning_fn=normal_binning, bins=bins), marker=".")
        plt.title("Normal distribution\nNormal binning")
        plt.grid()

        # Log normal distribution using logarithmic binning
        x = np.logspace(np.log10(y_log.min()), np.log10(y_log.max()), 100)
        plt.subplot(133)
        plt.plot(x, lognorm(mu, sigma2).pdf(x))
        plt.plot(*histogram(y_log, binning_fn=log_binning, bins=bins), marker=".")
        plt.title("Log normal distribution\nLogarithmic binning")
        plt.grid()
        plt.xscale("log")

@click.command("plots-moving")
def plots_moving():

    # Generate noisy data
    x = np.linspace(-3, 4)
    y = np.sin(x)
    y += np.random.randn(y.size) / 3

    with Figure("plots-moving.png", figsize=(30, 20)):
        # Plot data with moving average function and few neighbors
        plt.subplot(221)
        plt.scatter(x, y)
        plt.plot(*moving_avg(x, y, neighbors=1), c=tab_colours[1])
        plt.title("Moving avg., n=1")
        plt.grid()

        # Same but with higher smoothing
        plt.subplot(222)
        plt.scatter(x, y)
        plt.plot(*moving_avg(x, y, neighbors=4), c=tab_colours[1])
        plt.title("Moving avg., n=4")
        plt.grid()

        # Same but with higher smoothing
        plt.subplot(223)
        plt.scatter(x, y)
        plt.plot(*exp_moving_avg(x, y), c=tab_colours[1])
        plt.title(r"Exp. moving avg., $\alpha=0.2$")
        plt.grid()

        # Same but with higher smoothing
        plt.subplot(224)
        plt.scatter(x, y)
        plt.plot(*exp_moving_avg(x, y, reverse=True), c=tab_colours[1])
        plt.title(r"Reverse exp. moving avg., $\alpha=0.2$")
        plt.grid()

@click.command("plots-smoothing")
def plots_smoothing():

    # Generate noisy data
    n = 100
    x = np.linspace(-5, 5, n)
    y = np.sin(x)
    y += np.random.randn(n) / 3
    subsample = np.random.randint(0, 2, n).astype(bool)
    x, y = x[subsample], y[subsample]

    # Plot data with moving average function and few neighbors
    with Figure("plots-smoothing.png", figsize=(30, 20)):
        plt.subplot(221)
        plt.scatter(x, y)
        plt.plot(*moving_avg(x, y, neighbors=2), c=tab_colours[1])
        plt.title("Moving avg., n=2")
        plt.grid()

        # Plot data with moving average function and few neighbors
        plt.subplot(222)
        plt.scatter(x, y)
        plt.plot(*moving_avg(x, y, neighbors=4), c=tab_colours[1])
        plt.title("Moving avg., n=4")
        plt.grid()

        # Moving avg. with smoothing
        plt.subplot(223)
        plt.scatter(x, y)
        plt.plot(*double_moving_avg(x, y, outer_neighbors=10), c=tab_colours[1])
        plt.title("Moving avg. with smoothing, outer=10")
        plt.grid()

        # Moving avg. with more smoothing
        plt.subplot(224)
        plt.scatter(x, y)
        plt.plot(*double_moving_avg(x, y, outer_neighbors=20), c=tab_colours[1])
        plt.title("Moving avg. with smoothing, outer=20")
        plt.grid()
