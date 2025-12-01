$inputFile = "templates/auditor-historial.html"
$outputFile = "templates/auditor-historial_new.html"

# Leer todo el archivo
$lines = Get-Content $inputFile

# Flag para saber si estamos reemplazando
$inReplacement = $false
$outputLines = @()

foreach ($line in $lines) {
    # Detectar inicio del enlace a reemplazar
    if ($line -match '<a href="/api/pdf_auditoria') {
        # Reemplazar con button onclick
        $newLine = $line -replace '<a href="/api/pdf_auditoria/\{\{ auditoria.id_auditoria \}\}" class="btn-view-pdf">', '<button onclick="window.open(''/api/pdf_auditoria/{{ auditoria.id_auditoria}}'', ''_blank'')" class="btn-view-pdf">'
        $outputLines += $newLine
        $inReplacement = $true
    }
    # Detectar cierre del enlace
    elseif ($inReplacement -and $line -match '</a>') {
        $newLine = $line -replace '</a>', '</button>'
        $outputLines += $newLine
        $inReplacement = $false
    }
    else {
        $outputLines += $line
    }
}

# Escribir archivo
$outputLines | Set-Content $outputFile -Encoding UTF8
Write-Host "Archivo creado: $outputFile"
