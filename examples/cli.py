try:
    import click
except ModuleNotFoundError:
    print("click must be installed to run examples.")
    exit(-1)

from examples.plots import plots_binning, plots_moving, plots_smoothing


@click.group()
def cli():
    pass

cli.add_command(plots_binning)
cli.add_command(plots_moving)
cli.add_command(plots_smoothing)


if __name__ == "__main__":
    cli()
