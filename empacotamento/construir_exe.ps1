# Gera dist\registro-demandas\ (e o .zip) com o executável e tudo de que ele precisa.
# Uso (na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File empacotamento\construir_exe.ps1 [-IncluirLista]
param([switch]$IncluirLista)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $raiz
$py = ".\.venv\Scripts\python.exe"
$nome = "registro-demandas"

& $py -m pip install -q -r requirements-dev.txt
& $py -m PyInstaller --noconfirm --clean --onedir --console --name $nome `
    --specpath build --hidden-import win32timezone buscar_demandas.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

$dest = "dist\$nome"

# Tesseract: só o executável e as DLLs (sem ferramentas de treino nem documentação)
$tess = "C:\Program Files\Tesseract-OCR"
if (-not (Test-Path "$tess\tesseract.exe")) { throw "Tesseract não encontrado em $tess" }
New-Item -ItemType Directory -Force "$dest\tesseract" | Out-Null
Copy-Item "$tess\tesseract.exe" "$dest\tesseract\"
Copy-Item "$tess\*.dll" "$dest\tesseract\"

# Idioma português, lista de estagiários, configuração e instruções
Copy-Item "tessdata" "$dest\tessdata" -Recurse -Force
New-Item -ItemType Directory -Force "$dest\config" | Out-Null
Copy-Item ".env.example" "$dest\.env.example"
Copy-Item "empacotamento\LEIA-ME.txt" "$dest\LEIA-ME.txt"

if ($IncluirLista) {
    # Pacote INTERNO: lista real e .env do órgão, SEM a chave da IA. Não publicar.
    if (Test-Path "config\estagiarios.csv") { Copy-Item "config\estagiarios.csv" "$dest\config\" }
    if (Test-Path ".env") {
        Get-Content ".env" -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*GROQ_API_KEY' } |
            Set-Content "$dest\.env" -Encoding UTF8
    }
} else {
    # Pacote PÚBLICO: só exemplos
    Copy-Item "config\estagiarios.exemplo.csv" "$dest\config\estagiarios.csv"
}

if (Test-Path "dist\$nome.zip") { Remove-Item "dist\$nome.zip" -Force }
Compress-Archive -Path $dest -DestinationPath "dist\$nome.zip" -CompressionLevel Optimal
Write-Host "Pronto: $dest  e  dist\$nome.zip"
