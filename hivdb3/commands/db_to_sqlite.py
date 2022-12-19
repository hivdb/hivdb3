import itertools
import click
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Connection
from sqlite_utils import Database
from sqlite_utils.db import Table
from typing import List, Dict, Tuple, Set, Optional, Any, Iterator

from ..cli import cli


@cli.command()
@click.version_option()
@click.argument("connection")
@click.argument("path", type=click.Path(exists=False), required=True)
@click.option("--all", help="Detect and copy all tables", is_flag=True)
@click.option("--table", help="Specific tables to copy", multiple=True)
@click.option(
    "--skip",
    help="When using --all skip these tables",
    multiple=True
)
@click.option(
    "--redact",
    help="(table, column) pairs to redact with ***",
    nargs=2,
    type=str,
    multiple=True,
)
@click.option("--sql", help="Optional SQL query to run")
@click.option("--output", help="Table in which to save --sql query results")
@click.option("--pk", help="Optional column to use as a primary key")
@click.option("-p", "--progress", help="Show progress bar", is_flag=True)
def db_to_sqlite(
    connection: str,
    path: str,
    all: bool,
    table: List[str],
    skip: List[str],
    redact: List[Tuple[str, str]],
    sql: str,
    output: str,
    pk: str,
    progress: bool
) -> None:
    """
    Load data from any database into SQLite.

    PATH is a path to the SQLite file to create, e.c. /tmp/my_database.db

    CONNECTION is a SQLAlchemy connection string, for example:

        postgresql://localhost/my_database
        postgresql://username:passwd@localhost/my_database

        mysql://root@localhost/my_database
        mysql://username:passwd@localhost/my_database

    More: https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls
    """
    if not all and not table and not sql:
        raise click.ClickException("--all OR --table OR --sql required")
    if skip and not all:
        raise click.ClickException("--skip can only be used with --all")
    redact_columns: Dict[str, Set[str]] = {}
    for table_name, column_name in redact:
        redact_columns.setdefault(table_name, set()).add(column_name)
    db = Database(path)
    db_conn: Connection = create_engine(connection).connect()
    inspector = inspect(db_conn)
    # Figure out which tables we are copying, if any
    tables = table
    if all:
        tables = inspector.get_table_names()
    if tables:
        for i, tbl in enumerate(tables):
            if progress:
                click.echo(
                    "{}/{}: {}".format(i + 1, len(tables), tbl), err=True
                )

            tblobj = db[tbl]
            if not isinstance(tblobj, Table):
                raise click.ClickException(
                    "Output table must be a table, not a view"
                )

            if tbl in skip:
                if progress:
                    click.echo("  ... skipping", err=True)
                continue
            pks = inspector.get_pk_constraint(tbl)["constrained_columns"]
            if len(pks) == 1:
                pks = pks[0]
            count: Optional[int] = None
            if progress:
                count = db_conn.execute(
                    "select count(*) from {}".format(tbl)
                ).fetchone()[0]  # type: ignore
            results = db_conn.execute(
                "select * from {}".format(tbl))  # type: ignore
            redact_these = redact_columns.get(tbl) or set()
            rows: Iterator[Dict[str, Any]] = (
                redacted_dict(r, redact_these) for r in results)
            # Make sure generator is not empty
            try:
                first: Dict[str, Any] = next(rows)
            except StopIteration:
                pass
            else:
                rows = itertools.chain([first], rows)
                if progress:
                    with click.progressbar(rows, length=count) as bar:
                        tblobj.insert_all(bar, pk=pks, replace=True)
                else:
                    tblobj.insert_all(rows, pk=pks, replace=True)
            for index in inspector.get_indexes(tbl):
                tblobj.create_index(
                    index['column_names'],
                    index_name=index['name'],
                    unique=index['unique']
                )
    if sql:
        if not output:
            raise click.ClickException("--sql must be accompanied by --output")
        tblobj = db[output]
        if not isinstance(tblobj, Table):
            raise click.ClickException(
                "Output table must be a table, not a view"
            )
        results = db_conn.execute(sql)  # type: ignore
        rows = (dict(r) for r in results)
        tblobj.insert_all(rows, pk=pk)


def redacted_dict(
    row: Dict[str, Any],
    redact: Set[str]
) -> Dict[str, Any]:
    d = dict(row)
    for key in redact:
        if key in d:
            d[key] = "***"
    return d
