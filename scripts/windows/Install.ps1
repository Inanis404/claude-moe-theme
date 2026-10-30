param([string]$Distro, [string]$LinuxUser, [switch]$SkipSystemPackages, [switch]$Startup, [switch]$Plan)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Common.ps1')
$target = Get-AtelierTarget -Distro $Distro -LinuxUser $LinuxUser
if ($Plan) {
    Write-Output "Distribution: $($target.Distro); regular user: $($target.LinuxUser)"
    Write-Output 'Steps: verified official packages; Chinese fonts and Pinyin; local runtime copy; Linux URL routing; Windows desktop shortcut.'
    Write-Output 'This plan does not install, launch, quit or reboot anything.'
    exit 0
}
if (-not $SkipSystemPackages) {
    Invoke-AtelierWsl -Distro $target.Distro -LinuxUser root -Command @('bash', "$($target.LinuxRoot)/scripts/linux/install-system.sh", $target.LinuxUser)
}
Invoke-AtelierWsl -Distro $target.Distro -LinuxUser $target.LinuxUser -Command @('python3', "$($target.LinuxRoot)/scripts/linux/install-user.py")
Save-AtelierTarget $target
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = $shell.CreateShortcut((Join-Path $desktop 'Claude.lnk'))
$shortcut.TargetPath = if ($PSVersionTable.PSEdition -eq 'Core') { Join-Path $PSHOME 'pwsh.exe' } else { Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe' }
$shortcut.Arguments = '-NoProfile -WindowStyle Hidden -File ' + (ConvertTo-AtelierArgument (Join-Path $PSScriptRoot 'Start.ps1'))
$shortcut.WorkingDirectory = $script:AtelierProjectRoot
$shortcut.Description = 'Claude with startup animation'
$shortcut.IconLocation = (Join-Path $script:AtelierProjectRoot 'assets\claude.ico') + ',0'
$shortcut.Save()
if ($Startup) { Copy-Item -LiteralPath (Join-Path $desktop 'Claude.lnk') -Destination (Join-Path ([Environment]::GetFolderPath('Startup')) 'Claude.lnk') -Force }
Write-Output 'Installed. Keep this project folder in place. Run Start.ps1 -CheckOnly, then use the desktop shortcut.'
Write-Output 'If kvm membership is not active yet, close WSL applications and start a fresh WSL session as described in the README.'
