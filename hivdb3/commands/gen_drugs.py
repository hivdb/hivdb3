import os
import re
import click
from ..cli import cli
from ..utils.csvv import load_csv, dump_csv


@cli.command()
@click.argument(
    'input_dir',
    type=click.Path(exists=True, file_okay=False))
@click.argument('output_csv', type=click.Path(dir_okay=False))
def generate_drugs(input_dir: str, output_csv: str) -> None:
    click.echo(output_csv)
    drug_lookup = {}

    if os.path.exists(output_csv):
        drugs = load_csv(output_csv)
        drug_lookup = {drug['drug_name']: drug for drug in drugs}

    for filepath in os.listdir(input_dir):
        if not filepath.lower().endswith('.csv'):
            continue
        for row in load_csv(os.path.join(input_dir, filepath)):
            regimen = row.get('Regimen')
            if not regimen:
                continue
            for drug_name in re.split(r'\s*\+\s*', regimen):
                if drug_name and drug_name not in drug_lookup:
                    drug_lookup[drug_name] = {'drug_name': drug_name}

    dump_csv(
        output_csv,
        sorted(
            drug_lookup.values(),
            key=lambda d: str(d['drug_name'])
        ),
        [
            'drug_name',
            'drug_class',
            'approved',
            'drug_full_name',
            'fda_approval_date'
        ]
    )
