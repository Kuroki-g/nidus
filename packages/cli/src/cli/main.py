import asyncio
import logging
from pathlib import Path
import click
from common.logger_setup import setup_logging

setup_logging(level="INFO")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Nidus CLI - Document MCP server CLI"""
    pass


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
    targets = [str(Path(p).resolve()) for p in dir]

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
def update(file):
    """add or update existing document in database

    nidus update -f update-target.txt -f add-target.txt
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
def delete(file):
    """delete existing document information in database

    nidus delete -f delete-target.txt -f delete-target-dir/
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
    "keyword",
    required=True,
    type=click.STRING,
)
def search(keyword):
    """Search database by keyword"""
    if not keyword or len(keyword) == 0:
        logger.warning("keyword is required.")
        return

    from cli.db.search_db import display_results_simple, search_docs_in_db

    results = search_docs_in_db(keyword)
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


# endregion cli


@cli.group()
def db():
    """db commands."""
    pass


@db.command()
def show_meta():
    """show metadata for database file"""
    from cli.meta.db_info import display_meta_simple, get_meta

    meta = get_meta()
    display_meta_simple(meta)


# region debug
@cli.group()
def debug():
    """debug commands for check NidusMCP"""
    pass


@debug.command()
@click.option(
    "--url",
    default="http://localhost:8000/mcp",
    help="Server URL",
)
def list_tools(url):
    """debug commands for check NidusMCP"""
    from cli.debug.list_tools import list_all_tools

    asyncio.run(list_all_tools(url))


@debug.command()
@click.argument(
    "keyword",
    required=True,
    type=click.STRING,
)
@click.option(
    "--url",
    default="http://localhost:8000/mcp",
    help="Server URL",
)
def search_mcp(keyword, url):
    """debug commands for check NidusMCP"""
    from cli.debug.search_db_mcp import run_search

    try:
        asyncio.run(run_search(keyword, url))
    except KeyboardInterrupt:
        print("\nAborted by user.")


@debug.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
def read_pdf(path):
    """debug commands for search document from Nidus MCP"""
    from cli.processor.pdf_processor import chunk_pdf

    pdf_path = Path(path).resolve()
    if pdf_path.exists():
        logger.info(f"Imported {pdf_path}")
    else:
        logger.critical(f"PDF ({pdf_path}) was not found.")

    chunks = chunk_pdf(pdf_path)
    for chunk in chunks:
        print(chunk)


# endregion


def main():
    cli()


if __name__ == "__main__":
    main()
