$file = "templates/auditor-historial.html"
$content = Get-Content $file -Raw -Encoding UTF8
$newContent = $content -replace '<a href="/api/pdf_auditoria/\{\{ auditoria.id_auditoria \}\}" class="btn-view-pdf">', '<button onclick="window.open(''/api/pdf_auditoria/{{ auditoria.id_auditoria}}'', ''_blank'')" class="btn-view-pdf">'
$newContent = $newContent -replace '</a>', '</button>'
Set-Content $file $newContent -NoNewline -Encoding UTF8
Write-Host "Link actualizado correctamente"
