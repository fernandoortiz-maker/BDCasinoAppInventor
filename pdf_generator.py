"""
Función mejorada para generar PDF de auditoría con diseño profesional
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
import json
import io

def generar_pdf_profesional(datos, id_auditoria):
    """
    Genera un PDF profesional con Arial fonts, comentarios y alertas de no conformidades
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # --- CONFIGURACIÓN DE FUENTES (Arial = Helvetica en reportlab) ---
    font_title = "Helvetica-Bold"  # Arial Bold
    font_body = "Helvetica"  # Arial
    size_title = 14
    size_body = 12
    
    # --- PARSEAR DATOS ---
    datos_audit = datos['datos_auditoria']
    if isinstance(datos_audit, str):
        try:
            datos_audit = json.loads(datos_audit)
        except:
            datos_audit = {}
    
    respuestas = datos_audit.get('respuestas', {})
    comentarios = datos_audit.get('comentarios', {})
    no_conformidades = datos_audit.get('no_conformidades', {})
    
    # --- FUNCIÓN AUXILIAR PARA SALTO DE PÁGINA ---
    def check_new_page(y_pos, space_needed=100):
        if y_pos < space_needed:
            c.showPage()
            c.setFont(font_body, size_body)
            c.setFillColorRGB(0, 0, 0)
            return height - 50
        return y_pos
    
    # --- ENCABEZADO ---
    y = height - 40
    c.setFillColorRGB(0.67, 0.57, 0.36)  # Color dorado
    c.rect(50, y - 5, width - 100, 60, fill=True, stroke=False)
    
    c.setFillColorRGB(1, 1, 1)  # Blanco
    c.setFont(font_title, 18)
    c.drawCentredString(width / 2, y + 30, "REPORTE DE AUDITORÍA ISO 14001")
    
    c.setFont(font_body, size_body)
    c.drawString(60, y + 10, f"Auditor: {datos['nombre']} {datos['apellido']}")
    c.drawString(60, y - 5, f"Email: {datos['email']}")
    c.drawString(400, y + 10, f"Fecha: {datos['fecha_auditoria']}")
    c.drawString(400, y - 5, f"ID: #{id_auditoria}")
    
    y -= 80
    
    # --- ALERTAS DE NO CONFORMIDADES ---
    c.setFillColorRGB(0, 0, 0)
    if no_conformidades:
        y = check_new_page(y, 150)
        
        c.setFont(font_title, size_title)
        c.drawString(50, y, "⚠️ ALERTAS DE NO CONFORMIDADES")
        y -= 25
        
        # No Conformidades Menores
        if no_conformidades.get('total_menores', 0) > 0:
            c.setFillColorRGB(1, 0.8, 0)  # Amarillo
            c.rect(50, y - 40, width - 100, 45, fill=True, stroke=True)
            c.setFillColorRGB(0, 0, 0)
            c.setFont(font_title, size_body)
            c.drawString(60, y - 15, f"⚠️ NO CONFORMIDADES MENORES: {no_conformidades['total_menores']}")
            c.setFont(font_body, 10)
            c.drawString(60, y - 30, "Se detectaron 3 o más incumplimientos consecutivos")
            y -= 50
        
        # No Conformidades Mayores
        if no_conformidades.get('total_mayores', 0) > 0:
            c.setFillColorRGB(1, 0.6, 0)  # Naranja
            c.rect(50, y - 40, width - 100, 45, fill=True, stroke=True)
            c.setFillColorRGB(0, 0, 0)
            c.setFont(font_title, size_body)
            c.drawString(60, y - 15, f"🔶 NO CONFORMIDADES MAYORES: {no_conformidades['total_mayores']}")
            c.setFont(font_body, 10)
            c.drawString(60, y - 30, "Se acumularon 3 o más no conformidades menores")
            y -= 50
        
        # Sanción Económica
        if no_conformidades.get('sancion', False):
            c.setFillColorRGB(1, 0.2, 0.2)  # Rojo
            c.rect(50, y - 50, width - 100, 55, fill=True, stroke=True)
            c.setFillColorRGB(1, 1, 1)  # Texto blanco
            c.setFont(font_title, size_title)
            c.drawString(60, y - 20, "🚨 ACREEDOR A SANCIÓN ECONÓMICA")
            c.setFont(font_body, 11)
            c.drawString(60, y - 40, "Se detectaron 3 o más no conformidades mayores")
            c.setFillColorRGB(0, 0, 0)
            y -= 65
        
        y -= 20
    
    # --- RESULTADOS DE LA AUDITORÍA ---
    y = check_new_page(y, 100)
    c.setFont(font_title, size_title)
    c.drawString(50, y, "📋 RESULTADOS DE LA AUDITORÍA")
    y -= 30
    
    # Iterar sobre respuestas
    for i, (pregunta, respuesta) in enumerate(respuestas.items(), 1):
        y = check_new_page(y, 60)
        
        # Pregunta
        c.setFont(font_body, size_body)
        pregunta_texto = pregunta[:70] + "..." if len(pregunta) > 70 else pregunta
        c.drawString(50, y, f"{i}. {pregunta_texto}")
        y -= 18
        
        # Respuesta con color
        if respuesta == "Cumple":
            c.setFillColorRGB(0, 0.6, 0)  # Verde
            simbolo = "✅"
        elif respuesta == "No Cumple":
            c.setFillColorRGB(0.8, 0, 0)  # Rojo
            simbolo = "❌"
        elif respuesta == "Cumple Parcialmente":
            c.setFillColorRGB(0.9, 0.6, 0)  # Naranja
            simbolo = "⚠️"
        else:
            c.setFillColorRGB(0.5, 0.5, 0.5)  # Gris
            simbolo = "➖"
        
        c.setFont(font_title, size_body)
        c.drawString(70, y, f"{simbolo} {respuesta}")
        c.setFillColorRGB(0, 0, 0)
        y -= 25
    
    # --- COMENTARIOS ---
    if comentarios:
        y = check_new_page(y, 100)
        c.setFont(font_title, size_title)
        c.drawString(50, y, "💬 COMENTARIOS Y OBSERVACIONES")
        y -= 25
        
        for seccion, comentario in comentarios.items():
            y = check_new_page(y, 80)
            c.setFont(font_title, size_body)
            titulo_seccion = seccion.replace('_', ' ').replace('comentario seccion', 'Sección').title()
            c.drawString(50, y, titulo_seccion)
            y -= 15
            
            # Dibujar comentario en caja
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(50, y - 40, width - 100, 45, fill=True, stroke=True)
            c.setFillColorRGB(0, 0, 0)
            c.setFont(font_body, 10)
            
            # Dividir texto largo
            max_width = width - 120
            words = comentario.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if stringWidth(test_line, font_body, 10) <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            y_text = y - 15
            for line in lines[:3]:  # Máximo 3 líneas
                c.drawString(60, y_text, line)
                y_text -= 12
            
            y -= 50
    
    c.save()
    buffer.seek(0)
    return buffer
