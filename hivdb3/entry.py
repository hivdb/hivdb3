from .cli import cli
from .commands import gen_invitro_selection
from .commands import gen_ivsel_isolates

__all__ = [
    'cli',
    'gen_invitro_selection',
    'gen_ivsel_isolates',
]


if __name__ == '__main__':
    cli()
