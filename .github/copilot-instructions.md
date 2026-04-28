# dms_datastore — Workspace Instructions

Follow organization standards and hierarchy and local rules from AGENTS.md.

## Build and Test

The `schism` conda environment is assumed to exist. It is a large superset of dms_datastore.

Always activate it before running any tests or install commands.

```bash
# Install (development mode)
cd bdschism
conda activate schism
pip install --no-deps -e .

# Single file
conda activate schism && pytest tests
```

pytest is configured in `pyproject.toml` (`[tool.pytest.ini_options]`): strict markers, JUnit XML output, ignores `setup.py` and `build/`.
