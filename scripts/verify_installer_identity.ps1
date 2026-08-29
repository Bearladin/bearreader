param(
    [string]$InstallerPath,
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"

function Convert-Codepoints([int[]]$Codepoints) {
    return -join ($Codepoints | ForEach-Object { [char]$_ })
}

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) {
        throw $Message
    }
}

function Invoke-Installer(
    [string]$Path,
    [string[]]$Arguments,
    [string]$Description
) {
    $process = Start-Process -FilePath $Path -ArgumentList $Arguments -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "$Description failed with exit code $($process.ExitCode)"
    }
}

function Invoke-UpgradeSmoke([string]$Path, [string]$RepositoryRoot) {
    $buildRoot = Join-Path $RepositoryRoot "build"
    New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
    $smokeRoot = Join-Path $buildRoot ("i-" + $PID + "-" + (Get-Random -Maximum 10000))
    $installDir = Join-Path $smokeRoot "install"
    $arguments = @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/NOICONS",
        "/DIR=$installDir"
    )

    try {
        Invoke-Installer -Path $Path -Arguments $arguments -Description "Initial install"
        $managedSources = Join-Path $installDir "_internal\sources"
        Assert-True (Test-Path $managedSources) "Installed managed source tree is missing"

        $outsideSentinel = Join-Path $installDir "outside-managed-source.sentinel"
        Set-Content -LiteralPath $outsideSentinel -Value "preserve me" -Encoding ASCII

        Invoke-Installer -Path $Path -Arguments $arguments -Description "Upgrade install"
        Assert-True (Test-Path $outsideSentinel) "Upgrade deleted a sentinel outside managed sources"
        Assert-True (Test-Path (Join-Path $managedSources "_index.json")) "Upgrade left the source index missing"

        $uninstaller = Join-Path $installDir "unins000.exe"
        Assert-True (Test-Path $uninstaller) "Installed uninstaller is missing"
        $uninstallArguments = @(
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART"
        )
        Invoke-Installer -Path $uninstaller -Arguments $uninstallArguments -Description "Uninstall"
        Assert-True (Test-Path $outsideSentinel) "Uninstall deleted a sentinel outside managed sources"
    }
    finally {
        Remove-Item -LiteralPath $smokeRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$installer = Join-Path $repositoryRoot "installer\installer.iss"
$content = Get-Content -LiteralPath $installer -Raw -Encoding UTF8
$appName = "BearReader"
$required = @(
    ('#define MyAppName      "' + $appName + '"'),
    ('#define MyAppExeName   "' + $appName + '.exe"'),
    '#define MyAppID        "{{D44F8E47-8D94-4E50-A1F8-39D57C2B18E6}"',
    "OutputBaseFilename=BearReader-setup-{#MyAppVersion}-{#GetDateTimeString('yyyymmdd','','')}",
    "PrivilegesRequired=lowest",
    'Name: "chinesesimp"; MessagesFile: ".\languages\ChineseSimplified.isl"',
    ('Source: "..\dist\' + $appName + '\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs')
)

foreach ($value in $required) {
    Assert-True $content.Contains($value) "Installer identity is missing: $value"
}

Assert-True (-not $content.Contains("4A2E8B3D-7F1C-4E6A-9D5B-2C0F8A3E7B1D")) "Installer still contains the official LNCrawl AppId"
Assert-True (-not $content.Contains("[InstallDelete]")) "Installer uses [InstallDelete], which can leave an existing install unusable on a failed upgrade"

$translation = Join-Path $repositoryRoot "installer\languages\ChineseSimplified.isl"
$translationLicense = Join-Path $repositoryRoot "installer\languages\LICENSE-ChineseSimplified.txt"
Assert-True ((Test-Path $translation) -and (Test-Path $translationLicense)) "Installer is missing the vendored Simplified Chinese translation or its MIT license"

if ($Smoke) {
    Assert-True (-not [string]::IsNullOrWhiteSpace($InstallerPath)) "Smoke verification requires -InstallerPath"
    Assert-True (Test-Path $InstallerPath) "Installer path does not exist: $InstallerPath"
    Invoke-UpgradeSmoke (Resolve-Path $InstallerPath).Path $repositoryRoot
}

Write-Output "Verified BearReader installer identity."
