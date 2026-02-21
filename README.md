# nidus-mcp

NidusMCP: store doc information and connect as MCP server

## Arch

![Arch](docs/architecture.drawio.png)


## Database candidate

lancedb

- https://lancedb.github.io/lancedb/python/python/
  - https://github.com/lancedb/lancedb

qdrant

- https://github.com/qdrant/qdrant

DuckDB + vss

- https://duckdb.org/docs/stable/core_extensions/vss

```yml
service:
    nidus-mcp:
        image: "docker image to do"
        volumns:
            - docs
        env:
            - PORT=2122
```
