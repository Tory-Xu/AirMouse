param(
    [string]$Version = "2.0.0",
    [switch]$NoClean,
    [string]$PfxPath = "",
    [string]$PfxPassword = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($Version -notmatch '^\d+\.\d+\.\d+(\.\d+)?$') {
    throw "版本号必须为 2.0.0 或 2.0.0.0 形式。"
}

if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") {
    throw "Windows 安装包必须在 Windows 环境构建。"
}

$Venv = Join-Path $Root ".venv-build"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        & $PyLauncher.Source -3.11 -m venv $Venv
    } else {
        & python -m venv $Venv
    }
}

$PythonVersion = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($PythonVersion.Trim() -ne "3.11") {
    throw "Windows 安装包要求 Python 3.11，当前虚拟环境为 Python $PythonVersion。请删除 .venv-build 后重试。"
}

& $VenvPython -m pip install --disable-pip-version-check --upgrade pip
& $VenvPython -m pip install --disable-pip-version-check -r requirements-build.txt

if (-not $NoClean) {
    Remove-Item build, dist, release -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item build, dist, release -ItemType Directory -Force | Out-Null

$IconPath = Join-Path $Root "build\AirMouse.ico"
& $VenvPython -c "from PIL import Image; image=Image.open(r'static/touchpad.png').convert('RGBA'); image.save(r'build/AirMouse.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"

$VersionParts = @($Version.Split('.') | ForEach-Object { [int]$_ })
while ($VersionParts.Count -lt 4) {
    $VersionParts += 0
}
$FileVersion = ($VersionParts[0..3] -join ', ')
$VersionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($FileVersion),
    prodvers=($FileVersion),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'080404B0',
        [StringStruct(u'CompanyName', u'Tory-Xu'),
         StringStruct(u'FileDescription', u'AirMouse Remote'),
         StringStruct(u'FileVersion', u'$Version'),
         StringStruct(u'InternalName', u'AirMouse'),
         StringStruct(u'OriginalFilename', u'AirMouse.exe'),
         StringStruct(u'ProductName', u'AirMouse'),
         StringStruct(u'ProductVersion', u'$Version')]
      )
    ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)
"@
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $Root "build\version_info.txt"), $VersionInfo, $Utf8NoBom)

& $VenvPython -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller packaging\AirMouse.spec

function Find-SignTool {
    $Command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($Command) {
        return $Command.Source
    }
    return $null
}

function Sign-File([string]$Path) {
    if (-not $PfxPath) {
        return
    }
    $SignTool = Find-SignTool
    if (-not $SignTool) {
        throw "已指定签名证书，但未找到 signtool.exe。"
    }
    & $SignTool sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f $PfxPath /p $PfxPassword $Path
}

Sign-File (Join-Path $Root "dist\AirMouse\AirMouse.exe")

$IsccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
)
$IsccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($IsccCommand) {
    $Iscc = $IsccCommand.Source
} else {
    $Iscc = $IsccCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $Iscc) {
    throw "未找到 Inno Setup 6，请先安装：https://jrsoftware.org/isinfo.php"
}

$SourceDir = Join-Path $Root "dist\AirMouse"
$OutputDir = Join-Path $Root "release"
& $Iscc "/DMyAppVersion=$Version" "/DSourceDir=$SourceDir" "/DOutputDir=$OutputDir" "/DIconFile=$IconPath" "packaging\installer.iss"

$Installer = Join-Path $OutputDir "AirMouse-Setup-$Version-x64.exe"
Sign-File $Installer
$Hash = (Get-FileHash $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText("$Installer.sha256", "$Hash  $(Split-Path $Installer -Leaf)`n", $Utf8NoBom)

Write-Host "构建完成：$Installer"
Write-Host "SHA-256：$Hash"
