import click
from typing import Dict

from ..cli import cli
from ..utils.csvv import load_csv, dump_csv
from ..utils.mutations import GenePos


def load_consensus(filename: str) -> Dict[GenePos, str]:
    lookup: Dict[GenePos, str] = {}
    for idx, row in enumerate(load_csv(filename)):
        if row['Gene'] is None:
            click.echo(
                "'Gene' cannot be empty (row: {})".format(idx + 2),
                err=True)
            raise click.Abort()
        if row['AASeq'] is None:
            click.echo(
                "'AASeq' cannot be empty (row: {})".format(idx + 2),
                err=True)
            raise click.Abort()
        gene = row['Gene']
        for pos0, aa in enumerate(row['AASeq']):
            lookup[(gene, pos0 + 1)] = aa
    return lookup


@cli.command()
@click.argument(
    'consensus_csv', type=click.Path(exists=True, dir_okay=False))
@click.argument(
    'output_csv', type=click.Path(dir_okay=False))
def generate_ref_amino_acid(consensus_csv: str, output_csv: str) -> None:
    click.echo(output_csv)
    lookup = load_consensus(consensus_csv)
    dump_csv(
        output_csv,
        [{
            'gene': gene,
            'position': pos,
            'amino_acid': aa
        } for (gene, pos), aa in lookup.items()],
        ['gene', 'position', 'amino_acid']
    )
