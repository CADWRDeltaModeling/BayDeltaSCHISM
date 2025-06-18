@REM Run these commands in the BayDeltaSCHISM/ directory 
@REM to set up your documentation environment
@REM this works in windows by simply calling ./setup_doc_env_windows.bat in a terminal with conda initialized

REM Check if the "bds_doc" environment already exists
conda env list | findstr "bds_doc" > nul
if %errorlevel% equ 0 (
    echo The "bds_doc" conda environment already exists. Exiting setup. Delete this environment before running this script.
    exit /b 1
) else (
    REM Activate base environment
    conda activate base

    REM Create the "bds_doc" environment from the YAML file
    conda env create -n bds_doc -f .\schism_env.yml

    REM Activate the "bds_doc" environment
    conda activate bds_doc

    REM Configure npm registry and disable strict SSL
    npm config set registry http://registry.npmjs.org/
    npm config set strict-ssl false

    REM Install Mermaid CLI globally
    npm install -g @mermaid-js/mermaid-cli

    REM Pull the latest changes from the repository
    git pull --rebase

    REM Install version-specific uxarray and suxarray tools
    git clone -b suxarray https://github.com/kjnam/uxarray.git && pushd uxarray && pip install --no-deps . && popd && rmdir .\uxarray\ -Recurse -Force

    git clone -b v2024.09.0 https://github.com/cadwrdeltamodeling/suxarray && pushd suxarray && pip install --no-deps . && popd && rmdir .\suxarray\ -Recurse -Force

    REM Install the bdschism package with documentation dependencies
    pip install -e ./bdschism[doc]
)

REM Ensure the terminal ends with the "bds_doc" environment active
conda activate bds_doc