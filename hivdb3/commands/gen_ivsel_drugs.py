import os
import re
import click

from ..cli import cli
from ..utils.csvv import load_csv, dump_csv

from .gen_invitro_selection import gen_isolate_names


@cli.command()
@click.argument(
    'input_worksheet',
    type=click.Path(exists=True, file_okay=True))
@click.argument(
    'output_csv',
    type=click.Path(dir_okay=False))
def generate_ivsel_drugs(input_worksheet: str, output_csv: str) -> None:
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    click.echo(output_csv)

    # Load the data from the input worksheet using the csvv.load_csv() function
    rows = load_csv(input_worksheet)
    results = {}
    # Process each row in the input worksheet
    for row in gen_isolate_names(rows):
        regimen = row.get('Regimen')
        if not regimen:
            continue
        # Split the "Regimen" column into a list of drug names
        drugs = re.split(r'\s*\+\s*', regimen)
        for drug in drugs:
            if drug:
                results[(
                    row['RefName'],
                    row['IsolateName'],
                    drug
                )] = {
                    'ref_name': row['RefName'],
                    'isolate_name': row['IsolateName'],
                    'drug_name': drug
                }

    # Dump the processed data to the output CSV file
    # using the csvv.dump_csv() function
    headers = ['ref_name', 'isolate_name', 'drug_name']
    dump_csv(output_csv, results.values(), headers=headers)
