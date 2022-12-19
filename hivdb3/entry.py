from .cli import cli
from .commands import gen_invitro_selection
from .commands import gen_ivsel_isolates
from .commands import gen_ref_amino_acid
from .commands import gen_drugs
from .commands import gen_ivsel_drugs
from .commands import gen_mutations
from .commands import gen_isolates
from .commands import gen_gene_isolates
from .commands import db_to_sqlite

__all__ = [
    'cli',
    'gen_invitro_selection',
    'gen_ivsel_isolates',
    'gen_ref_amino_acid',
    'gen_drugs',
    'gen_ivsel_drugs',
    'gen_mutations',
    'gen_isolates',
    'gen_gene_isolates',
    'db_to_sqlite'
]


if __name__ == '__main__':
    cli()
