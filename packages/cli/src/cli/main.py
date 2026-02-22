import logging
from pathlib import Path
import click
from common.logger_setup import setup_logging
from common.model import EmbeddingModelManager
from cli.db.update_db import update_files_in_db
from cli.db.init import init_db

model = EmbeddingModelManager()


setup_logging(level="INFO")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Nidus CLI - Document MCP server CLI"""
    pass


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
    """init database"""
    file_paths = [Path(f).resolve() for f in file]
    valid_paths = [p for p in file_paths if p.exists()]
    if not valid_paths:
        logger.warning("No valid files found to update.")
        return

    update_files_in_db(valid_paths)


def main():
    cli()


if __name__ == "__main__":
    main()
