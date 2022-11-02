import re
import click
from copy import deepcopy
from typing import List, Iterable, Tuple, Set, Dict, Optional
from itertools import chain

from ..cli import cli
from ..utils.csvv import load_csv, dump_csv, CSVReaderRow, CSVWriterRow


GenePos = Tuple[str, int]

MUTATION_PATTERN = re.compile(r"""
    (?:(?P<gene>\w+):)?                      # the gene
    [AC-IK-NP-TV-Y]?                         # the ref AA (ignored)
    (?P<pos>\d+)                             # the position
    (?P<aas>
      (?:[AC-IK-NP-TV-Y*]|ins|del)
      (?:/?(?:[AC-IK-NP-TV-Y*]|ins|del))*
    )                                        # the mut AAs
""", re.VERBOSE)

GENE_ORDER = ['CA', 'PR', 'RT', 'IN']


def gen_isolate_names(rows: List[CSVReaderRow]) -> Iterable[CSVReaderRow]:
    optional_key_columns = [
        ('Cell line', ''),
        ('Strain', ''),
        ('Regimen', ''),
        ('Experiment', 'exp:'),
        ('Passage', 'p'),
        ('Cumulative culture time', ''),
        ('Concentration', 'dose:'),
    ]
    essential_key_columns: List[str] = []
    keys: Dict[Tuple[str, ...], int] = {}
    for idx, row in enumerate(rows):
        key = tuple(
            prefix + (row[col] or '')
            for col, prefix in optional_key_columns
        )
        if key in keys:
            click.echo(
                'The experiment key of row {} is conflict'
                'to row {}, both are {!r}'
                .format(idx + 2, keys[key] + 2, key),
                err=True
            )
            raise click.Abort()
        keys[key] = idx
    for idx, (col, _) in reversed(list(enumerate(optional_key_columns))):
        partial_keys: Dict[Tuple[str, ...], int] = {}
        if col == 'Experiment':
            # alway keep Experiment column
            essential_key_columns.append(col)
            continue
        for key in keys:
            partial_key = key[:idx] + key[idx + 1:]
            if partial_key in partial_keys:
                essential_key_columns.append(col)
                break
            partial_keys[partial_key] = keys[key]
        else:
            keys = partial_keys
    essential_key_columns.reverse()
    for key, idx in keys.items():
        row = rows[idx]
        if row['RefName'] is None:
            click.echo(
                "'RefName' is empty at row {}".format(idx + 2), err=True)
            raise click.Abort()
        prefix = 'ivsel:' + row['RefName'] + '|'
        yield {
            'isolate_name': prefix + '|'.join(key),
            **rows[idx]
        }


def make_mutation_map(
    *delta_mutations: str,
    default_gene: str,
    baseline_mutmap: Dict[GenePos, Set[str]] = {},
    refmap: Dict[GenePos, str] = {}
) -> Dict[GenePos, Set[str]]:
    mutmap: Dict[GenePos, Set[str]] = deepcopy(baseline_mutmap)
    for m in chain(*[
        MUTATION_PATTERN.finditer(delta)
        for delta in delta_mutations
    ]):
        named: Dict[str, Optional[str]] = m.groupdict()
        if named['pos'] is None or named['aas'] is None:
            raise RuntimeError('pos or aas is None, check MUTATION_PATTERN')
        genepos: GenePos = (
            named['gene'] or default_gene,
            int(named['pos'])
        )
        aas: Set[str] = set(named['aas']
                            .replace('/', '')
                            .replace('ins', '')
                            .replace('del', ''))
        if 'ins' in named['aas']:
            aas.add('ins')
        if 'del' in named['aas']:
            aas.add('del')

        if aas == {refmap.get(genepos)}:
            mutmap.pop(genepos)
        else:
            mutmap[genepos] = aas
    return mutmap


def mutation_map_as_text(mutmap: Dict[GenePos, Set[str]]) -> str:
    mutlist: List[str] = []
    prevgene: Optional[str] = None
    for (gene, pos), aas in sorted(
        mutmap.items(),
        key=lambda m: (GENE_ORDER.index(m[0][0]), m[0][1])
    ):
        if 'ins' in aas or 'del' in aas:
            aatext = '/'.join(sorted(aas))
        else:
            aatext = ''.join(sorted(aas))
        if gene == prevgene:
            mutlist.append('{}{}'.format(pos, aatext))
        else:
            mutlist.append('{}:{}{}'.format(gene, pos, aatext))
            prevgene = gene
    return '+'.join(mutlist)


def norm_strain(
    strain: str,
    mutmap: Dict[GenePos, Set[str]] = {}
) -> str:
    strain = strain.rsplit(' (', 1)[0]
    muttext: str = mutation_map_as_text(mutmap)
    if muttext:
        return '{} ({})'.format(strain, muttext)
    else:
        return strain


def get_value_cmp(value: str) -> Optional[str]:
    if value.startswith('~') or re.search(r'\d+-\d+', value):
        return '~'
    elif value.startswith('>'):
        return '>'
    elif value.startswith('<'):
        return '<'
    elif not is_unknown(value):
        return '='
    return None


def get_positive_num(value: str) -> Optional[str]:
    posnum: List[str] = re.findall(r'\d+(?:\.\d+)?', value)
    if posnum:
        return '{:g}'.format(
            sum(float(n) for n in posnum) / len(posnum)
        )
    else:
        return None


def get_time_unit(value: str) -> Optional[str]:
    if value.endswith('d') or value.endswith('day'):
        return 'day'
    elif value.endswith('w') or value.endswith('week'):
        return 'week'
    elif value.endswith('m') or \
            value.endswith('mo') or \
            value.endswith('month'):
        return 'month'
    elif value.endswith('ord') or value.endswith('seq'):
        return 'ordinal'
    else:
        return None


def is_unknown(value: str) -> bool:
    return value.lower() == 'unknown'


def worksheet_to_table(rows: List[CSVReaderRow]) -> Iterable[CSVWriterRow]:
    for idx, row in enumerate(gen_isolate_names(rows)):
        if row['Strain'] is None:
            click.echo("'Strain' is empty at row {}"
                       .format(idx + 2), err=True)
            raise click.Abort()

        if row['Baseline mutations'] is None:
            click.echo("'Baseline mutations' is empty at row {}"
                       .format(idx + 2), err=True)
            raise click.Abort()

        if row['Gene'] is None:
            click.echo("'Gene' is empty at row {}"
                       .format(idx + 2), err=True)
            raise click.Abort()

        if row['Passage'] is None:
            click.echo("'Passage' is empty at row {}"
                       .format(idx + 2), err=True)
            raise click.Abort()

        if row['Cumulative culture time'] is None:
            click.echo("'Cumulative culture time' is empty at row {}"
                       .format(idx + 2), err=True)
            raise click.Abort()

        # TODO: this one should be used when creating mutations table
        # baseline_mutmap: Dict[GenePos, Set[str]] = make_mutation_map(
        #     row['Baseline mutations'],
        #     default_gene=row['Gene'],
        #     baseline_mutmap={},  # TODO: respect column BaselineRefSeq
        #     refmap={}  # TODO: use Consensus B
        # )

        yield {
            'ref_name': row['RefName'],
            'isolate_name': row['isolate_name'],
            'baseline_isolate_name': row['Strain'],
            'cell_line': row['Cell line'],
            'experiment': row['Experiment'],
            'passage_cmp': get_value_cmp(row['Passage']),
            'passage': get_positive_num(row['Passage']),
            'passage_unknown': is_unknown(row['Passage']),
            'cumulative_culture_time_cmp':
            get_value_cmp(row['Cumulative culture time']),

            'cumulative_culture_time':
            get_positive_num(row['Cumulative culture time']),

            'cumulative_culture_time_unit':
            get_time_unit(row['Cumulative culture time']),

            'cumulative_culture_time_unknown':
            is_unknown(row['Cumulative culture time']),

            'section': row['Source']
        }


@cli.command()
@click.argument(
    'input_worksheet',
    type=click.Path(exists=True, dir_okay=False))
@click.argument(
    'output_csv',
    type=click.Path(dir_okay=False))
def generate_invitro_selection(input_worksheet: str, output_csv: str) -> None:
    click.echo(output_csv)
    rows = load_csv(input_worksheet)
    dump_csv(
        output_csv,
        worksheet_to_table(rows),
        headers=[
            'ref_name',
            'isolate_name',
            'baseline_isolate_name',
            'cell_line',
            'experiment',
            'passage_cmp',
            'passage',
            'passage_unknown',
            'cumulative_culture_time_cmp',
            'cumulative_culture_time',
            'cumulative_culture_time_unit',
            'cumulative_culture_time_unknown',
            'section'
        ]
    )
