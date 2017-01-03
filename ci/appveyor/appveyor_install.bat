git submodule update --init --recursive
:: Batch script will not exit if a command returns an error, so we manually do
:: it for commands that may fail.
if %errorlevel% neq 0 exit /b %errorlevel%

::
:: Python configuration
::

if %arch% == 32 (
  set python_path=C:\Python%python%
) else (
  set python_path=C:\Python%python%-x64
)

set PATH=%python_path%;%python_path%\Scripts;%PATH%
python --version

appveyor DownloadFile https://bootstrap.pypa.io/get-pip.py
python get-pip.py
pip install -r python\test_requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%

::
:: Vim configuration
::

if %arch% == 32 (
  set vc_mod=x86
) else (
  set vc_mod=x86_amd64
)

git clone https://github.com/vim/vim %APPVEYOR_BUILD_FOLDER%\vim
pushd %APPVEYOR_BUILD_FOLDER%\vim\src
set SDK_INCLUDE_DIR=C:\Program Files (x86)\Microsoft SDKs\Windows\v7.1A\Include
"%VS120COMNTOOLS%\..\..\VC\vcvarsall.bat" %vc_mod%
"%VS120COMNTOOLS%\..\..\VC\bin\nmake.exe" /f Make_mvc.mak FEATURES=HUGE DYNAMIC_PYTHON3=yes PYTHON3=%python_path%
popd
set PATH=%APPVEYOR_BUILD_FOLDER%\vim\src;%PATH%
vim --version
