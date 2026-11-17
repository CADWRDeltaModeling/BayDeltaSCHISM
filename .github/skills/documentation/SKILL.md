---
name: documentation
description: "Use when setting up, building, updating, or troubleshooting BayDeltaSCHISM Sphinx documentation: schism_env.yml plus docs overlay, make html, automatic bdschism API generation, failed autodoc imports, Mermaid and Click pages, and GitHub Pages actions."
---

# BayDeltaSCHISM documentation

Read [documentation.rst](../../../docsrc/documentation.rst) for contributor commands and
publishing instructions. Run setup commands from the repository root in a
Conda-initialized terminal. Let the user create or change environments unless execution
is requested.

## Environment

- `schism_env.yml` is the runtime base. It is the large, task-oriented SCHISM environment
  and is deliberately not reduced for documentation.
- `environment-doc.yml` adds Sphinx `>=8.2,<9`, its extensions, and the build tools needed
  to install `bdschism`. It is an overlay, not a standalone environment.
- Create `bds_doc` from `schism_env.yml`, update it with the overlay without `--prune`,
  then install the checkout with `python -m pip install --no-deps --no-build-isolation -e ./bdschism`.
- `build_doc_env.bat` and `build_doc_env.sh` are convenience wrappers over those steps,
  not alternative dependency definitions.
- An existing environment is not disposable. Update a compatible environment, or ask
  before replacing it. Do not modify `schism` or another existing environment merely to
  make the docs build.
- Keep the `doc` extra in `bdschism/pyproject.toml` and `environment-doc.yml` consistent.
  CI uses `environment-doc.yml`.

## Build

From `docsrc`, run `make html` (`.\make.bat html` in Windows PowerShell). For a fresh build,
run `make clean` and then `make html`.

`sphinx.ext.apidoc` generates the `bdschism` API RST under ignored `docsrc/_api/` during
every build. The package is `bdschism/bdschism` inside the `bdschism` project directory.
`docsrc/bdschism.rst` only links to the generated page. Do not edit or commit generated
RST/HTML, and do not run a separate `sphinx-apidoc` command.

HTML goes to ignored `docs/html`. Inspect `index.html`, the API pages and the command
pages rather than treating a green build as proof of completeness.

## Failures and warnings

- Missing API or CLI content: examine import warnings in the docs environment. Fix
  dependency inputs or report a source-level failure; do not add mock imports or suppress
  warnings merely to produce a green build.
- The existing `autodoc_mock_imports` in `docsrc/conf.py` are retained. Do not silently
  expand them. `suxarray` is not available from conda and is installed separately in the
  full environment.
- Existing docstring and cross-reference warnings remain; warning-free builds are not
  currently required.
- Rendering Mermaid diagrams in HTML does not require installing Mermaid CLI. Do not change
  global npm registry or TLS settings as part of setup.

## CI and deployment

The docs workflow uses the same runtime YAML, overlay and editable checkout, then
`make html`. It caches the Conda environment (keyed on both YAML files and the calendar
week) so the large SCHISM solve is skipped on most runs; bump `CACHE_NUMBER` in the
workflow to force a rebuild. GitHub Pages receives `docs/html` through upload/deploy actions, not a branch.
Settings -> Pages must use GitHub Actions, and the `github-pages` environment must allow the
publishing branch or tag. Pull-request checks and branch protection are outside this change.
