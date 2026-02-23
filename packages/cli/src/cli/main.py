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


@cli.command()
@click.option(
    "--doc_dir",
    help="document directory path(s)",
    multiple=True,
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
def init(doc_dir):
    """init database"""
    targets = [str(Path(p).resolve()) for p in doc_dir]
    if len(targets) == 0:
        logger.warning("Document list is empty.")
        return

    from cli.db.init import init_db

    init_db(targets)


@cli.command()
@click.option(
    "--file",
    "-f",
    help="update file(s)",
    multiple=True,
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
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


def main():
    cli()


if __name__ == "__main__":
    main()
