import click

from examples.ds.plots import plots_binning, plots_running, plots_smoothing


@click.group()
def cli():
    pass

cli.add_command(plots_binning)
cli.add_command(plots_running)
cli.add_command(plots_smoothing)


if __name__ == "__main__":
    cli()
