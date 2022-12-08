import os
import re
import click

from ..cli import cli
from ..utils.csvv import load_csv, dump_csv
from ..utils.mutations import load_mutations

GENES = ['PR', 'RT', 'IN', 'CA']


@cli.command()
@click.argument(
    'input_worksheet',
    type=click.Path(exists=True, file_okay=True))
@click.argument(
    'output_csv',
    type=click.Path(dir_okay=False))
def generate_mutations(input_worksheet: str, output_csv: str) -> None:
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    click.echo(output_csv)

    isolates = load_csv(input_worksheet)
    records = []
    for row in isolates:
        for gene in GENES:
            colname = f'{gene} Mutations'
            muts = row.get(colname)
            if not muts:
                continue
            mutlist = re.split(r'\s*\+\s*', muts)
            mutlookup = load_mutations(*mutlist, default_gene=gene)
            for (_, pos), aas in mutlookup.items():
                for aa in aas:
                    records.append({
                        'isolate_name': row['IsolateName'],
                        'gene': gene,
                        'position': pos,
                        'amino_acid': aa
                    })
    dump_csv(
        output_csv,
        records,
        ['isolate_name', 'gene', 'position', 'amino_acid']
    )
