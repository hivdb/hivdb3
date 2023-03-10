import os
import click

from ..cli import cli
from ..utils.csvv import load_csv, dump_csv

GENES = ['PR', 'RT', 'IN', 'CA']


@cli.command()
@click.argument(
    'input_worksheet',
    type=click.Path(exists=True, file_okay=True))
@click.argument(
    'output_csv',
    type=click.Path(dir_okay=False))
def generate_isolates(input_worksheet: str, output_csv: str) -> None:
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    click.echo(output_csv)

    isolates = load_csv(input_worksheet)
    records = []
    unique_isolates = set()
    for idx, row in enumerate(isolates):
        if row.get('CanonName'):
            # skip synonyms
            continue
        isoname = row.get('IsolateName')
        if not isoname:
            click.echo("'IsolateName' is missing at row {}"
                       .format(idx + 2), err=True)
            raise click.Abort()
        subtype = row.get('Subtype')
        if isoname not in unique_isolates:
            records.append({
                'isolate_name': isoname,
                'subtype': subtype
            })
            unique_isolates.add(isoname)
    dump_csv(
        output_csv,
        records,
        ['isolate_name', 'subtype']
    )
