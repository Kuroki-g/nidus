from collections.abc import Generator, Iterable
from pathlib import Path


def flatten_path_to_file(
    paths: str | Path | Iterable[str | Path],
    exclude_patterns: str | Path | Iterable[str | Path] = (),
) -> Generator[Path]:
    """Flatten path to file list."""
    if isinstance(paths, (str, Path)):
        paths = [paths]

    if isinstance(exclude_patterns, (str, Path)):
        exclude_patterns = [exclude_patterns]

    exclude_strs = [str(p) for p in exclude_patterns]
    for p in paths:
        path_obj = Path(p).resolve()

        if not path_obj.exists():
            continue

        # Check exclude pattern
        if any(path_obj.match(pattern) for pattern in exclude_strs):
            continue

        if path_obj.is_file():
            yield path_obj
        elif path_obj.is_dir():
            yield from flatten_path_to_file(
                path_obj.iterdir(), exclude_patterns=exclude_strs
            )
