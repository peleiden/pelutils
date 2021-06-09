""" Plotting examples using pelutils.ds.plot """
import matplotlib.pyplot as plt
import numpy as np

from pelutils.ds.plots import linear_binning, log_binning, normal_binning, get_bins, figsize_wide, rc_params_small, update_rc_params
from pelutils.ds.distributions import norm, lognorm


def plots_example():
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

if __name__ == "__main__":
    plots_example()
