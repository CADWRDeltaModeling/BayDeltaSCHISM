#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
    -h|--help)
        printf '%s\n' \
            'Usage: bash build_doc_env.sh' \
            'Create bds_doc from schism_env.yml plus environment-doc.yml,' \
            'then install the bdschism checkout editable. Requires Conda on PATH.' \
            'An existing environment is not deleted or replaced.'
        exit 0
        ;;
    "")
        ;;
    *)
        printf '%s\n' 'Usage: bash build_doc_env.sh' >&2
        exit 2
        ;;
esac

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
conda_hook="$(conda shell.bash hook)"
eval "$conda_hook"
conda env create -n bds_doc -f schism_env.yml
conda env update -n bds_doc -f environment-doc.yml
conda activate bds_doc
python -m pip install --no-deps --no-build-isolation -e ./bdschism
printf '%s\n' \
    'Documentation environment ready.' \
    'Next: conda activate bds_doc' \
    'Then: cd docsrc' \
    '      make html'
