import logging
import time

from init_scripts.processor.file_processor import (
    data_generator,
    data_generator_multiprocessing,
)

logging.disable(logging.WARNING)


def run_benchmark(path_list, func: callable):
    print(f"--- Benchmark Start (Target: {path_list}) ---")

    start_time = time.perf_counter()

    total_chunks = 0
    for batch in func(path_list):
        total_chunks += len(batch)

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    print("-" * 30)
    print(f"Total Chunks: {total_chunks}")
    print(f"Execution Time: {elapsed:.4f} seconds")
    if total_chunks > 0:
        print(f"Average Time per Chunk: {elapsed / total_chunks:.6f} seconds")
    print("-" * 30)


if __name__ == "__main__":
    target_dir = ["samples/docs/secrets"]
    run_benchmark(target_dir, data_generator)
    run_benchmark(target_dir, data_generator_multiprocessing)
