import os
import click
from typing import List, Iterable, Dict, Set, Tuple

from ..cli import cli
from ..utils.csvv import load_csv, dump_csv, CSVReaderRow, CSVWriterRow
from ..utils.mutations import load_mutations, dump_mutations, GenePos

from .gen_invitro_selection import gen_isolate_names


def update_isolates(
    isolates: Dict[str, CSVWriterRow],
    isolate_name: str,
    mutmap: Dict[GenePos, Set[str]]
) -> None:
    if isolate_name not in isolates:
        isolates[isolate_name] = {
            'IsolateName': isolate_name,
            '_mutmap': mutmap,
            **dump_mutations(mutmap)
        }
    else:
        old_mutmap: Dict[GenePos, Set[str]] = isolates[isolate_name]['_mutmap']
        old_mutmap.update(mutmap)
        isolates[isolate_name].update(
            dump_mutations(old_mutmap)
        )


def load_baseline(baseline_csv: str) -> Tuple[
    Dict[str, Dict[GenePos, Set[str]]],
    Dict[str, str]
]:
    lookup: Dict[str, Dict[GenePos, Set[str]]] = {}
    renames: Dict[str, str] = {}
    rows = load_csv(baseline_csv)
    for idx, row in enumerate(rows):
        if row['IsolateName'] is None:
            click.echo("({}) 'IsolateName' is empty at row {}"
                       .format(baseline_csv, idx + 2), err=True)
            raise click.Abort()
        if row['CanonName']:
            renames[row['IsolateName']] = row['CanonName']
            continue
        iso_name = row['IsolateName']
        if iso_name not in lookup:
            lookup[iso_name] = {}
        for gene in ('CA', 'PR', 'RT', 'IN'):
            genemuts = row[f'{gene} Mutations']
            if genemuts is None:
                click.echo("({}) '{} Mutations' is empty at row {}"
                           .format(baseline_csv, gene, idx + 2),
                           err=True)
                raise click.Abort()
            lookup[iso_name].update(
                load_mutations(genemuts, default_gene=gene)
            )
    return lookup, renames


def ivsel_to_isolates(
    filenames: List[str],
    refseq_mutmaps: Dict[str, Dict[GenePos, Set[str]]],
    renames: Dict[str, str]
) -> Iterable[CSVWriterRow]:
    isolates: Dict[str, CSVWriterRow] = {}

    for filename in filenames:
        rows: List[CSVReaderRow] = load_csv(filename)
        for idx, row in enumerate(gen_isolate_names(rows)):
            if row['IsolateName'] is None:
                raise RuntimeError(
                    "'IsolateName' is empty, "
                    "check function 'gen_isolate_names'"
                )

            if row['BaselineRefSeq'] is None:
                click.echo("({}) 'BaselineRefSeq' is empty at row {}"
                           .format(filename, idx + 2), err=True)
                raise click.Abort()

            if row['Strain'] is None:
                click.echo("({}) 'Strain' is empty at row {}"
                           .format(filename, idx + 2), err=True)
                raise click.Abort()

            if row['Gene'] is None:
                click.echo("({}) 'Gene' is empty at row {}"
                           .format(filename, idx + 2), err=True)
                raise click.Abort()

            if row['Baseline mutations'] is None:
                click.echo("({}) 'Baseline mutations' is empty at row {}"
                           .format(filename, idx + 2), err=True)
                raise click.Abort()

            if row['Delta mutations'] is None:
                click.echo("({}) 'Delta mutations' is empty at row {}"
                           .format(filename, idx + 2), err=True)
                raise click.Abort()

            refseq_name = row['BaselineRefSeq']
            baseline_name = row['Strain']

            if refseq_name in renames:
                refseq_name = renames[refseq_name]

            if baseline_name in renames:
                baseline_name = renames[baseline_name]

            refseq_mutmap = refseq_mutmaps.get(refseq_name, {})
            baseline_mutmap = load_mutations(
                row['Baseline mutations'],
                default_gene=row['Gene'],
                baseline_mutmap=refseq_mutmap,
                refmap={}  # TODO: use Consensus B
            )

            if baseline_name not in refseq_mutmaps:
                update_isolates(
                    isolates, baseline_name, baseline_mutmap)

            delta_mutmap = load_mutations(
                row['Delta mutations'],
                default_gene=row['Gene'],
                baseline_mutmap=baseline_mutmap,
                refmap={}  # TODO: use Consensus B
            )
            update_isolates(
                isolates, row['IsolateName'], delta_mutmap)
    return isolates.values()


@cli.command()
@click.argument(
    'worksheet_dir',
    type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.argument(
    'output_csv',
    type=click.Path(dir_okay=False))
@click.option(
    '--baseline-csv',
    type=click.Path(exists=True, dir_okay=False),
    required=True)
def generate_ivsel_isolates(
    worksheet_dir: str,
    output_csv: str,
    baseline_csv: str
) -> None:
    click.echo(output_csv)
    refseqs, renames = load_baseline(baseline_csv)
    filenames = [
        os.path.join(worksheet_dir, fn)
        for fn in os.listdir(worksheet_dir)
        if fn.endswith('-ivsel.csv')
    ]
    dump_csv(
        output_csv,
        ivsel_to_isolates(filenames, refseqs, renames),
        headers=[
            'IsolateName',
            'CA Mutations',
            'PR Mutations',
            'RT Mutations',
            'IN Mutations'
        ]
    )
