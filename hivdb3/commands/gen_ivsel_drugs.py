import os
import re
import click

from ..cli import cli
from ..utils.csvv import load_csv, dump_csv, CSVWriterRow

from .gen_invitro_selection import gen_isolate_names

VALID_UNITS = {
    'um': '\u00b5M',  # use micro symbol "µ" not greek letter "μ"
    '\u03bcm': '\u00b5M',
    '\u00b5m': '\u00b5M',
    'pm': 'pM',
    'nm': 'nM',
    'ng/ml': 'ng/ml'
}


def norm_range(start: str, end: str) -> float:
    num: float = float(start)
    if end:
        num = (num + float(end)) / 2
    return round(num, 3)


def norm_unit(unit: str) -> str:
    lower = unit.lower()
    if lower not in VALID_UNITS:
        click.echo(f'Invalid unit {unit}', err=True)
        raise click.Abort()
    return VALID_UNITS[lower]


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
    for idx, row in enumerate(gen_isolate_names(rows)):
        regimen = row.get('Regimen')
        concentration = row.get('Concentration')
        if not regimen:
            click.echo("'Regimen' is empty at row {}"
                       .format(idx + 2), err=True)
            raise click.Abort()
        if not concentration:
            click.echo("'Concentration' is empty at row {}"
                       .format(idx + 2), err=True)
            raise click.Abort()
        # Split the "Regimen" column into a list of drug names
        drugs = re.split(r'\s*\+\s*', regimen)
        dosages = re.split(r'\s*\+\s*', concentration)
        if len(drugs) != len(dosages):
            click.echo("The sizes of 'Regimen' and 'Concentration' "
                       "are not the same at row {}"
                       .format(idx + 2), err=True)
            raise click.Abort()
        for drug, dosage in zip(drugs, dosages):
            if not drug:
                click.echo("A drug is empty in 'Regimen' of row {}"
                           .format(idx + 2), err=True)
                raise click.Abort()
            if not dosage:
                click.echo("A dosage is empty in 'Concentration' of row {}"
                           .format(idx + 2), err=True)
                raise click.Abort()
            is_unknown = dosage.lower() == 'unknown'
            mat = re.match(
                r'^([=><~]?)\s*(\d+\.?\d*)(?:\s*-\s*(\d+\.?\d*))?\s*([^\d]+)$',
                dosage)

            if not is_unknown and not mat:
                click.echo('Invalid dosage format: {} at row {}'
                           .format(dosage, idx + 2), err=True)
                raise click.Abort()

            dosage_results: CSVWriterRow = {
                'concentration_cmp': None,
                'concentration': None,
                'concentration_unit': None,
                'concentration_unknown': True
            }

            if not is_unknown and mat:
                cmp: str = mat.group(1) or '='
                num: float = norm_range(mat.group(2), mat.group(3))
                unit: str = norm_unit(mat.group(4))
                dosage_results.update({
                    'concentration_cmp': cmp,
                    'concentration': num,
                    'concentration_unit': unit,
                    'concentration_unknown': False
                })

            results[(
                row['RefName'],
                row['IsolateName'],
                drug
            )] = {
                'ref_name': row['RefName'],
                'isolate_name': row['IsolateName'],
                'drug_name': drug,
                **dosage_results
            }

    # Dump the processed data to the output CSV file
    # using the csvv.dump_csv() function
    headers = [
        'ref_name',
        'isolate_name',
        'drug_name',
        'concentration_cmp',
        'concentration',
        'concentration_unit',
        'concentration_unknown'
    ]
    dump_csv(output_csv, results.values(), headers=headers)
