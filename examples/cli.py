import click

from examples.ds.plots import plots_binning, plots_running


@click.group()
def cli():
    pass

cli.add_command(plots_binning)
cli.add_command(plots_running)


if __name__ == "__main__":
    cli()
