# Fairy-Stockfish Installation Script for Windows
# Run this in PowerShell as Administrator

Write-Host "=== Fairy-Stockfish Installation for Windows ===" -ForegroundColor Green

# Create installation directory
$installDir = "C:\fairy-stockfish"
if (!(Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force
    Write-Host "Created directory: $installDir"
}

# Get latest release info
Write-Host "Fetching latest Fairy-Stockfish release..." -ForegroundColor Yellow
try {
    $releaseInfo = Invoke-RestMethod -Uri "https://api.github.com/repos/fairy-stockfish/Fairy-Stockfish/releases/latest"
    $version = $releaseInfo.tag_name
    Write-Host "Latest version: $version" -ForegroundColor Cyan
    
    # Find Windows binary
    $windowsAsset = $releaseInfo.assets | Where-Object { $_.name -like "*windows*" -or $_.name -like "*x86_64*" -and $_.name -like "*.exe*" } | Select-Object -First 1
    
    if ($windowsAsset) {
        $downloadUrl = $windowsAsset.browser_download_url
        $filename = $windowsAsset.name
        $filePath = Join-Path $installDir $filename
        
        Write-Host "Downloading: $filename" -ForegroundColor Yellow
        Invoke-WebRequest -Uri $downloadUrl -OutFile $filePath -UseBasicParsing
        
        # Extract if it's a zip file
        if ($filename -like "*.zip") {
            Write-Host "Extracting archive..." -ForegroundColor Yellow
            Expand-Archive -Path $filePath -DestinationPath $installDir -Force
            
            # Find the executable
            $exeFiles = Get-ChildItem -Path $installDir -Filter "*.exe" -Recurse
            if ($exeFiles) {
                $exePath = $exeFiles[0].FullName
                $finalPath = Join-Path $installDir "fairy-stockfish.exe"
                Copy-Item $exePath $finalPath -Force
                Write-Host "Fairy-Stockfish installed to: $finalPath" -ForegroundColor Green
            }
        } else {
            # Direct executable
            $finalPath = Join-Path $installDir "fairy-stockfish.exe"
            Move-Item $filePath $finalPath -Force
            Write-Host "Fairy-Stockfish installed to: $finalPath" -ForegroundColor Green
        }
        
        # Add to PATH
        $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        if ($currentPath -notlike "*$installDir*") {
            [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$installDir", "User")
            Write-Host "Added to user PATH. Please restart PowerShell to use." -ForegroundColor Green
        }
        
        # Test installation
        Write-Host "Testing installation..." -ForegroundColor Yellow
        try {
            & "$finalPath" --version
            Write-Host "Fairy-Stockfish installed successfully!" -ForegroundColor Green
        } catch {
            Write-Host "Installation test failed. You may need to run: $finalPath" -ForegroundColor Red
        }
        
    } else {
        Write-Host "Windows binary not found in release assets" -ForegroundColor Red
        Write-Host "Please download manually from: https://github.com/fairy-stockfish/Fairy-Stockfish/releases" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Failed to fetch release information: $_" -ForegroundColor Red
    Write-Host "Please download manually from GitHub releases" -ForegroundColor Yellow
}

Write-Host "`n=== Installation Complete ===" -ForegroundColor Green
Write-Host "Fairy-Stockfish location: $installDir\fairy-stockfish.exe" -ForegroundColor Cyan
Write-Host "If not in PATH, use full path in your code." -ForegroundColor Yellow
