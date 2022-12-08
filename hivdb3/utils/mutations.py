import re
from copy import deepcopy
from typing import List, Tuple, Set, Dict, Optional
from itertools import chain


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


def load_mutations(
    *delta_mutations: str,
    default_gene: str,
    baseline_mutmap: Dict[GenePos, Set[str]] = {},
    refmap: Dict[GenePos, str] = {}
) -> Dict[GenePos, Set[str]]:
    """
    List of mutations -> dict lookup

    @param: delta_mutations list of mutations from baseline strain
    @param: default_gene default gene if gene is not come with a delta mutation
    @param: baseline_mutmap dict of mutations from refseq of baseline strain
    @param: refmap dict of reference (consensus B) amino acids
    """
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
            # remove back mutations
            mutmap.pop(genepos, None)
        else:
            mutmap[genepos] = aas
    return mutmap


def dump_mutations(mutmap: Dict[GenePos, Set[str]]) -> Dict[str, str]:
    mutlist: Dict[str, List[str]] = {}
    for (gene, pos), aas in sorted(
        mutmap.items(),
        key=lambda m: (GENE_ORDER.index(m[0][0]), m[0][1])
    ):
        if 'ins' in aas or 'del' in aas:
            aatext = '/'.join(sorted(aas))
        else:
            aatext = ''.join(sorted(aas))
        if gene not in mutlist:
            mutlist[gene] = []
        mutlist[gene].append('{}{}'.format(pos, aatext))
    return {
        f'{gene} Mutations': '+'.join(muts)
        for gene, muts in mutlist.items()
    }
