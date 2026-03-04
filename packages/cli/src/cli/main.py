import logging
from pathlib import Path

import click
from common.logger_setup import setup_logging

setup_logging(level="WARNING")
logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Show INFO logs")
@click.option("--debug", is_flag=True, help="Show DEBUG logs")
def cli(verbose, debug):
    """Nidus - Japanese local document search engine"""
    if debug:
        setup_logging(level="DEBUG")
    elif verbose:
        setup_logging(level="INFO")


@cli.command(name="help")
@click.argument("command", required=False)
@click.pass_context
def help_command(ctx, command):
    """Show help for a command. (e.g. nidus help add)"""
    if command is None:
        click.echo(ctx.parent.get_help())
        return
    cmd = ctx.parent.command.commands.get(command)
    if cmd is None:
        raise click.UsageError(f"No such command: {command!r}")
    with click.Context(cmd, parent=ctx.parent, info_name=command) as sub_ctx:
        click.echo(cmd.get_help(sub_ctx))


# region cli
@cli.command()
@click.option(
    "--dir",
    help="document directory path(s) to be store",
    multiple=True,
    required=False,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
def init(dir):
    """init database and download model if not exist"""
    from cli.db.init import init_db, init_model

    init_model()

    dir = [] if dir is None else dir
    targets = [Path(p).resolve() for p in dir]

    init_db(targets)


@cli.command()
@click.option(
    "--file",
    "-f",
    help="file(s) or dir to be added or updated",
    multiple=True,
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
)
def add(file):
    """add or update existing document in database

    nidus add -f update-target.txt -f add-target.txt
    """
    file_paths = [Path(f).resolve() for f in file]
    valid_paths = [p for p in file_paths if p.exists()]
    if not valid_paths:
        logger.warning("No valid files found to update.")
        return

    from cli.db.update_db import update_files_in_db

    update_files_in_db(valid_paths)


@cli.command()
@click.option(
    "--file",
    "-f",
    help="file(s) or dir to be deleted",
    multiple=True,
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
)
def drop(file):
    """delete existing document information in database

    nidus drop -f delete-target.txt -f delete-target-dir/
    """
    file_paths = [Path(f).resolve() for f in file]
    valid_paths = [p for p in file_paths if p.exists()]
    if not valid_paths:
        logger.warning("No valid files found to be deleted.")
        return

    from cli.db.delete_db_record import delete_files_in_db

    delete_files_in_db(valid_paths)


@cli.command()
@click.argument(
    "dirs",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option("--no-recursive", is_flag=True, help="Do not watch subdirectories")
def watch(dirs, no_recursive):
    """Watch directories and auto-index on file changes.

    nidus watch ./docs ./notes
    """
    dir_paths = [Path(d).resolve() for d in dirs]

    from cli.watch import watch_directories

    click.echo(f"Watching {len(dir_paths)} directory(ies). Press Ctrl+C to stop.")
    for d in dir_paths:
        click.echo(f"  {d}")
    watch_directories(dir_paths, recursive=not no_recursive)


@cli.command()
@click.argument(
    "keyword",
    required=True,
    type=click.STRING,
)
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
def search(keyword, output_json):
    """Search database by keyword"""
    if not keyword or len(keyword) == 0:
        logger.warning("keyword is required.")
        return

    from cli.db.search_db import (
        display_results_json,
        display_results_simple,
        search_docs_in_db,
    )

    results = search_docs_in_db(keyword)
    if output_json:
        display_results_json(results)
    else:
        display_results_simple(results)


@cli.command()
@click.argument(
    "keyword",
    required=False,
    type=click.STRING,
)
def list(keyword):
    """List document filtered by keyword."""
    from cli.db.search_db import display_list_results_simple, list_docs_in_db

    results = list_docs_in_db(keyword)
    display_list_results_simple(results)


@cli.command()
@click.option("--dry-run", is_flag=True, help="Show files to be reindexed without processing")
def reindex(dry_run):
    """Re-index all registered documents from scratch.

    Useful after changing the embedding model or DB schema.
    All existing records are cleared and rebuilt.
    """
    from cli.db.reindex_db import reindex_all_in_db

    reindex_all_in_db(dry_run=dry_run)


@cli.command()
def status():
    """show metadata for database file"""
    from cli.meta.db_info import display_meta_simple, get_meta

    meta = get_meta()
    display_meta_simple(meta)


# endregion cli


# region debug
@cli.group()
def debug():
    """debug commands"""
    pass


@debug.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
def parse(path):
    """parse a document file and print chunks"""
    from cli.processor.file_processor import get_chunks

    file_path = Path(path).resolve()
    chunks = get_chunks(file_path)
    if chunks is None:
        logger.error(f"Failed to parse: {file_path}")
        return
    for chunk in chunks:
        print(chunk)


# endregion


def main():
    cli()


if __name__ == "__main__":
    main()
