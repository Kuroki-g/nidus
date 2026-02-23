from pathlib import Path
from typing import Union, Iterable, Generator


def flatten_path_to_file(
    paths: Union[str, Path, Iterable[Union[str, Path]]],
) -> Generator[Path, None, None]:
    """Flatten path to file list."""
    if isinstance(paths, (str, Path)):
        paths = [paths]

    for p in paths:
        path_obj = Path(p).resolve()

        if not path_obj.exists():
            continue

        if path_obj.is_file():
            yield path_obj
        elif path_obj.is_dir():
            yield from flatten_path_to_file(path_obj.iterdir())
