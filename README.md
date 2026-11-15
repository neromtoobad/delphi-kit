# delphi-kit is now Agon for Python

This package was renamed and moved. Everything it did, plus recording what your agent believed before each
trade, is now **Agon for Python**:

```bash
pip install agon-delphi
```

```python
from agon import Delphi
```

- Code and docs: https://github.com/neromtoobad/agon/tree/main/python
- Site: https://agon.nerom.site
- PyPI: https://pypi.org/project/agon-delphi/

The command is now `agon` (was `delphi`), the MCP server is `agon-mcp` (was `delphi-mcp`), and environment
variables start with `AGON_` (were `DELPHI_`).

`pip install delphi-kit` 0.3.0 still works: it installs agon-delphi, and `import delphi_kit` re-exports it with a
deprecation warning. This repository is archived.
