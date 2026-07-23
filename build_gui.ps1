$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$distName = "PrivateGameTranslator"

Set-Location $projectRoot

$buildArgs = @(
  "-m",
  "PyInstaller",
  "--noconfirm",
  "--clean",
  "--windowed",
  "--name",
  $distName,
  "--paths",
  "$projectRoot\src",
  "--add-data",
  "$projectRoot\runtime;runtime",
  "$projectRoot\main_gui.py"
)

& python @buildArgs
