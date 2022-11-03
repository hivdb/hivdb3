from .cli import cli
from .commands import gen_invitro_selection
from .commands import gen_ivsel_isolates
from .commands import gen_ref_amino_acid

__all__ = [
    'cli',
    'gen_invitro_selection',
    'gen_ivsel_isolates',
    'gen_ref_amino_acid'
]


if __name__ == '__main__':
    cli()
