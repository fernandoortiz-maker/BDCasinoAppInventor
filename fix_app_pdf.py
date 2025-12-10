#!/usr/bin/env python3
"""
Script mejorado para corregir la función generar_pdf en app.py
"""

def fix_pdf_function_v2():
    file_path = r'd:\proyectos uni\Nueva carpeta\BDCasinoAppInventor\app.py'
    
    print("📝 Leyendo app.py...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar el patrón completo de la función vieja
    import re
    
    # Patrón: desde @app.route hasta el cierre de send_file
    pattern = r'@app\.route\("/api/pdf_auditoria/<int:id_auditoria>", methods=\["GET"\]\)\s*\n.*?return send_file\([^)]*\)[^}]*?\)(?=\s*\n\s*\n# ===)'
    
    new_function = '''@app.route("/api/pdf_auditoria/<int:id_auditoria>", methods=["GET"])
def generar_pdf(id_auditoria):
    from pdf_generator import generar_pdf_profesional
    
    datos = obtener_datos_auditoria(id_auditoria)
    if not datos:
        return "Auditoría no encontrada", 404
    
    buffer = generar_pdf_profesional(datos, id_auditoria)
    
    return send_file(
        buffer, 
        as_attachment=False, 
        download_name=f"reporte_{id_auditoria}.pdf", 
        mimetype='application/pdf'
    )'''
    
    # Intentar reemplazo
    new_content, num_subs = re.sub(pattern, new_function, content, flags=re.DOTALL, count=1)
    
    if num_subs > 0:
        print(f"✅ Reemplazo exitoso ({num_subs} sustitución)")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"💾 Archivo guardado")
        print(f"   Tamaño anterior: {len(content)} bytes")
        print(f"   Tamaño nuevo: {len(new_content)} bytes")
        return True
    else:
        print("❌ No se pudo hacer el reemplazo con regex")
        print("   Intentando método manual...")
        return fix_manual(content, file_path)

def fix_manual(content, file_path):
    """Método manual de reemplazo"""
    lines = content.split('\n')
    
    # Encontrar líneas clave
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if '@app.route("/api/pdf_auditoria' in line:
            start_line = i
        if start_line and i > start_line and "mimetype='application/pdf'" in line:
            # Buscar el cierre del paréntesis
            if ')' in line:
                end_line = i
                break
    
    if start_line is None or end_line is None:
        print(f"❌ No se encontraron las líneas (start={start_line}, end={end_line})")
        return False
    
    print(f"✅ Función encontrada en líneas {start_line+1} a {end_line+1}")
    
    new_function_lines = [
        '@app.route("/api/pdf_auditoria/<int:id_auditoria>", methods=["GET"])',
        'def generar_pdf(id_auditoria):',
        '    from pdf_generator import generar_pdf_profesional',
        '    ',
        '    datos = obtener_datos_auditoria(id_auditoria)',
        '    if not datos:',
        '        return "Auditoría no encontrada", 404',
        '    ',
        '    buffer = generar_pdf_profesional(datos, id_auditoria)',
        '    ',
        '    return send_file(',
        '        buffer, ',
        '        as_attachment=False, ',
        '        download_name=f"reporte_{id_auditoria}.pdf", ',
        "        mimetype='application/pdf'",
        '    )',
    ]
    
    # Reconstruir
    new_lines = lines[:start_line] + new_function_lines + lines[end_line+1:]
    new_content = '\n'.join(new_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Reemplazo manual exitoso")
    print(f"   Líneas eliminadas: {end_line - start_line + 1}")
    print(f"   Líneas nuevas: {len(new_function_lines)}")
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("CORRECCIÓN DE FUNCIÓN PDF - VERSIÓN 2")
    print("="*60)
    
    try:
        if fix_pdf_function_v2():
            print("\n🎉 ¡Corrección completada!")
        else:
            print("\n❌ Falló la corrección")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
