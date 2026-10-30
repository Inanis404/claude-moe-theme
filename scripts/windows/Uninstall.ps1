param([string]$Distro, [string]$LinuxUser)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Common.ps1')
$target = Get-AtelierTarget -Distro $Distro -LinuxUser $LinuxUser
Invoke-AtelierWsl -Distro $target.Distro -LinuxUser $target.LinuxUser -Command @('python3', "$($target.LinuxRoot)/scripts/linux/uninstall-user.py")
$shell = New-Object -ComObject WScript.Shell
$expected = ConvertTo-AtelierArgument (Join-Path $PSScriptRoot 'Start.ps1')
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Startup'))) {
    $shortcutPath = Join-Path $folder 'Claude.lnk'
    if (Test-Path -LiteralPath $shortcutPath) {
        $shortcut = $shell.CreateShortcut($shortcutPath)
        if ($shortcut.Arguments.EndsWith($expected)) { Remove-Item -LiteralPath $shortcutPath }
    }
}
Write-Output 'Project shortcuts removed. Account data, themes, input dictionaries, installed packages and runtime copies were preserved.'
