@echo off
setlocal
if "%~1"=="--help" goto help
if "%~1"=="-h" goto help
if not "%~1"=="" (
    echo Usage: build_doc_env.bat
    exit /b 2
)

pushd "%~dp0"
call conda env create -n bds_doc -f schism_env.yml
set RESULT=%errorlevel%
if not "%RESULT%"=="0" goto end
call conda env update -n bds_doc -f environment-doc.yml
set RESULT=%errorlevel%
if not "%RESULT%"=="0" goto end
call conda activate bds_doc
set RESULT=%errorlevel%
if not "%RESULT%"=="0" goto end
python -m pip install --no-deps --no-build-isolation -e .\bdschism
set RESULT=%errorlevel%
if not "%RESULT%"=="0" goto end
echo Documentation environment ready.
echo Next: conda activate bds_doc
echo Then: cd docsrc
echo       make html

:end
popd
exit /b %RESULT%

:help
echo Usage: build_doc_env.bat
echo Create bds_doc from schism_env.yml plus environment-doc.yml,
echo then install the bdschism checkout editable. Run in a Conda-initialized terminal.
echo An existing environment is not deleted or replaced.
exit /b 0
