# Gera o programa com janelas (sem terminal) e o .zip para publicar.
# Uso (na raiz do projeto):
#   powershell -ExecutionPolicy Bypass -File empacotamento\construir_exe.ps1 [-IncluirLista]
# Resultado: dist\Registro-de-Demandas.zip  (contém a pasta "Registro de Demandas" com o .exe)
param([switch]$IncluirLista)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $raiz
$py = Join-Path $raiz ".venv\Scripts\python.exe"
$nome = "Registro de Demandas"
$tess = "C:\Program Files\Tesseract-OCR"
if (-not (Test-Path "$tess\tesseract.exe")) { throw "Tesseract não encontrado em $tess" }

& $py -m pip install -q -r requirements-dev.txt

# Tesseract: só o executável e as DLLs (sem ferramentas de treino nem documentação)
$stage = Join-Path $raiz "build\tesseract_embutido"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null
Copy-Item "$tess\tesseract.exe" $stage
Copy-Item "$tess\*.dll" $stage

# Programa com janelas (--windowed: não abre terminal). Os recursos ficam DENTRO do programa.
& $py -m PyInstaller --noconfirm --clean --onedir --windowed --name $nome --specpath build `
    --hidden-import win32timezone `
    --add-data "$raiz\tessdata;tessdata" `
    --add-data "$raiz\config\estagiarios.exemplo.csv;config" `
    registro_demandas.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

$dest = Join-Path $raiz "dist\$nome"
# O Tesseract é copiado DEPOIS (não via --add-data, que duplicaria as DLLs na raiz do programa)
Copy-Item $stage "$dest\_internal\tesseract" -Recurse
Copy-Item "empacotamento\LEIA-ME.txt" "$dest\LEIA-ME.txt"

if ($IncluirLista) {
    # Pacote INTERNO: leva a lista real e a configuração do órgão (SEM a chave da IA).
    # Na primeira execução o programa copia esses arquivos para a pasta de dados do usuário. NÃO publicar.
    $ini = "$dest\configuracao-inicial"
    New-Item -ItemType Directory -Force $ini | Out-Null
    if (Test-Path "config\estagiarios.csv") { Copy-Item "config\estagiarios.csv" "$ini\" }
    if (Test-Path ".env") {
        Get-Content ".env" -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*GROQ_API_KEY' } |
            Set-Content "$ini\.env" -Encoding UTF8
    }
}

$zip = Join-Path $raiz "dist\Registro-de-Demandas.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $dest -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Pronto: $zip"
