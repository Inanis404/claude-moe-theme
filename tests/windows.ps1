$ErrorActionPreference = 'Stop'
$project = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $project 'scripts\windows') -Filter '*.ps1') {
    $tokens=$null; $errors=$null
    $null=[System.Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
    if ($errors.Count -gt 0) { throw "PowerShell parse error in $($file.Name): $errors" }
}
. (Join-Path $project 'scripts\windows\Common.ps1')
if ((ConvertTo-AtelierArgument 'a b') -cne '"a b"') { throw 'Space quoting failed' }
if ((ConvertTo-AtelierArgument 'a"b') -cne '"a\"b"') { throw 'Quote escaping failed' }
if ((ConvertTo-AtelierArgument 'folder\') -cne 'folder\') { throw 'Unquoted path escaping failed' }
if ((ConvertTo-AtelierArgument 'folder name\') -cne '"folder name\\"') { throw 'Trailing slash escaping failed' }
# Override only this test's function; do not start WSL or read real user settings.
$script:AtelierProjectRoot = Join-Path $project '.local\synthetic-plan'
function Invoke-AtelierWsl {
    param([string]$Distro,[string]$LinuxUser,[string[]]$Command)
    if ($Command[0] -eq 'printenv') { return 'Ubuntu-Test' }
    if ($Command[0] -eq 'id') { return 'sample' }
    if ($Command[0] -eq 'wslpath') { return '/tmp/atelier-project with spaces' }
    throw 'Unexpected test command'
}
$target=Get-AtelierTarget
if ($target.Distro -ne 'Ubuntu-Test' -or $target.LinuxUser -ne 'sample' -or $target.LinuxRoot -ne '/tmp/atelier-project with spaces') { throw 'Target autodetection failed' }
try { $null=Get-AtelierTarget -Distro Ubuntu -LinuxUser root; throw 'Root rejection failed' } catch { if ($_.Exception.Message -eq 'Root rejection failed') { throw } }
Write-Output 'PASS: PowerShell parsing, native argument quoting, target detection and root rejection.'
