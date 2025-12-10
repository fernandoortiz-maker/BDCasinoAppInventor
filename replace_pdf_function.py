#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para reemplazar la función generar_pdf en app.py
"""

def replace_pdf_function():
    file_path = r'd:\proyectos uni\Nueva carpeta\BDCasinoAppInventor\app.py'
    
    # Leer el archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Encontrar las líneas de inicio y fin
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if '@app.route("/api/pdf_auditoria' in line and 'id_auditoria' in line:
            start_idx = i
        if start_idx is not None and i > start_idx:
            # Buscar el final de la función (siguiente decorador o sección)
            if line.strip().startswith('#') and '=====' in line and 'SECCIÓN 4' in line:
                # Retroceder para encontrar el cierre de la función anterior
                for j in range(i-1, start_idx, -1):
                    if lines[j].strip() == ')':
                        end_idx = j
                        break
                break
    
    if start_idx is None or end_idx is None:
        print(f"❌ No se pudo encontrar la función. start={start_idx}, end={end_idx}")
        return False
    
    print(f"✅ Función encontrada en líneas {start_idx+1} hasta {end_idx+1}")
    print(f"   Total de líneas a reemplazar: {end_idx - start_idx + 1}")
    
    # Nueva función
    new_function_lines = [
        '@app.route("/api/pdf_auditoria/<int:id_auditoria>", methods=["GET"])\n',
        'def generar_pdf(id_auditoria):\n',
        '    from pdf_generator import generar_pdf_profesional\n',
        '    \n',
        '    datos = obtener_datos_auditoria(id_auditoria)\n',
        '    if not datos:\n',
        '        return "Auditoría no encontrada", 404\n',
        '    \n',
        '    buffer = generar_pdf_profesional(datos, id_auditoria)\n',
        '    \n',
        '    return send_file(\n',
        '        buffer, \n',
        '        as_attachment=False, \n',
        '        download_name=f"reporte_{id_auditoria}.pdf", \n',
        '        mimetype=\'application/pdf\'\n',
        '    )\n',
        '\n',
    ]
    
    # Reemplazar
    new_lines = lines[:start_idx] + new_function_lines + lines[end_idx+1:]
    
    # Escribir el archivo
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"✅ Archivo app.py actualizado exitosamente!")
    print(f"   Líneas anteriores: {len(lines)}")
    print(f"   Líneas actuales: {len(new_lines)}")
    print(f"   Diferencia: {len(new_lines) - len(lines)} líneas")
    
    return True

if __name__ == "__main__":
    try:
        success = replace_pdf_function()
        if success:
            print("\n🎉 ¡Reemplazo completado con éxito!")
        else:
            print("\n❌ El reemplazo falló")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
