# nidus-mcp

NidusMCP is an open-source MCP server that search documents information locally.
It provides locally-restricted document search.

## Quick start

### Install globally with uv and serve

Installation:

```bash
uv tool install git+https://github.com/Kuroki-g/nidus-mcp.git
```

Init database:

```bash
nidus init --dir={YOUR_DOC_DIR}
```

Run Nidus Server:

```bash
nidus-mcp
```

You tell AI agent CLI by editing your `settings.json`.

```json
{
  "mcpServers": {
    "nidus": {
      "httpUrl": "http://localhost:8000/mcp",
    }
  }
}
```

## CLI tools

For database status check, Nidus CLI is available.
For detail, call `nidus --help`.

## MCP tools

For automatically update by AI agent, Nidus CLI is also available as MCP tools.
For detail, call `list_tools` via MCP.

## [TODO] Use docker compose

I have a plan but not implemented.

```yaml
services:
    // here your service
    // ...
    nidus:
        image: nidus:latest
        environment:
            # default: 8000
            PORT: 8000
            # DB_PATH default ./db/.lancedb
            DB_PATH: "${PWD}:./.lancedb"
        ports:
            - "8000:8000"
        volumes:
            # document directory mount
            - nidus:/docs
volumes:
    nidus_data:
```

## Notice

All data is saved to `$HOME/.cache/nidus/` directory.
For clean up, remove this directory.

## License

- License: [Apache License 2.0](https://github.com/Kuroki-g/nidus-mcp/blob/main/LICENSE)
