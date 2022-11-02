from .cli import cli
from .commands import gen_invitro_selection

__all__ = [
    'cli',
    'gen_invitro_selection'
]


if __name__ == '__main__':
    cli()
