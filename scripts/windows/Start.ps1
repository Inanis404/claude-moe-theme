param([string]$Distro, [string]$LinuxUser, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Common.ps1')
try {
    $target = Get-AtelierTarget -Distro $Distro -LinuxUser $LinuxUser
    if ($CheckOnly) {
        Invoke-AtelierWsl -Distro $target.Distro -LinuxUser $target.LinuxUser -Command @('bash', "$($target.LinuxRoot)/scripts/linux/check.sh")
        exit 0
    }
    Invoke-AtelierWsl -Distro $target.Distro -LinuxUser $target.LinuxUser -Command @('python3', "$($target.LinuxRoot)/scripts/linux/install-runtime.py") | Out-Null
    $linuxHome = (Invoke-AtelierWsl -Distro $target.Distro -LinuxUser $target.LinuxUser -Command @('printenv', 'HOME') | Out-String).Trim()
    if (-not $linuxHome.StartsWith('/')) { throw 'Could not resolve Linux home.' }
    # WSL parses its option names directly; quote values, not the -d/-u/--exec flags.
    $arguments = '-d ' + (ConvertTo-AtelierArgument $target.Distro) + ' -u ' + (ConvertTo-AtelierArgument $target.LinuxUser) + ' --exec bash ' + (ConvertTo-AtelierArgument "$linuxHome/.local/share/claude-atelier/bin/run.sh")
    $process = Start-Process -FilePath (Join-Path $env:WINDIR 'System32\wsl.exe') -ArgumentList $arguments -WindowStyle Hidden -PassThru
    try {
        $null = $process.WaitForExit(28000)
        if ($process.HasExited -and $process.ExitCode -eq 14) { throw 'The previous Claude client is waiting to quit. Finish its confirmation or active task, then launch again.' }
        if ($process.HasExited -and $process.ExitCode -ne 0) { throw "Claude exited with code $($process.ExitCode). Run Start.ps1 -CheckOnly for diagnostics." }
    } finally { $process.Dispose() }
} catch {
    if ($CheckOnly) { Write-Error $_; exit 1 }
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Claude') | Out-Null
    exit 1
}
