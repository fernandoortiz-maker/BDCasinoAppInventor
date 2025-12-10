"""
Generador de PDF Ejecutivo Formal para Auditorías ISO 14001
Incluye: diseño formal, gráficos de cumplimiento, secciones detalladas
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.piecharts import Pie
import json
import io

def generar_pdf_profesional(datos, id_auditoria):
    """
    Genera un PDF ejecutivo formal con gráficos y análisis detallado
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # --- CONFIGURACIÓN DE FUENTES ---
    font_title = "Helvetica-Bold"
    font_body = "Helvetica"
    
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
    buenas_practicas = no_conformidades.get('buenas_practicas', [])
    metricas = no_conformidades.get('metricas', {})
    
    # --- FUNCIÓN AUXILIAR PARA SALTO DE PÁGINA ---
    def check_new_page(y_pos, space_needed=100):
        nonlocal current_page
        if y_pos < space_needed:
            c.showPage()
            current_page += 1
            add_page_number()
            c.setFont(font_body, 10)
            c.setFillColorRGB(0, 0, 0)
            return height - 50
        return y_pos
    
    def add_page_number():
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawRightString(width - 50, 30, f"Página {current_page}")
        c.setFillColorRGB(0, 0, 0)
    
    current_page = 1
    
    # ============================================
    # PÁGINA 1: PORTADA Y ENCABEZADO FORMAL
    # ============================================
    y = height - 80
    
    # Línea superior
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(2)
    c.line(50, y + 20, width - 50, y + 20)
    
    # Título principal
    c.setFont(font_title, 20)
    c.drawCentredString(width / 2, y, "REPORTE DE AUDITORÍA")
    y -= 25
    c.setFont(font_title, 16)
    c.drawCentredString(width / 2, y, "ISO 14001:2015")
    y -= 40
    
    # Línea separadora
    c.setLineWidth(0.5)
    c.line(50, y, width - 50, y)
    y -= 40
    
    # Información del auditor
    c.setFont(font_title, 11)
    c.drawString(50, y, "INFORMACIÓN DEL AUDITOR")
    y -= 20
    c.setFont(font_body, 10)
    c.drawString(70, y, f"Nombre: {datos['nombre']} {datos['apellido']}")
    y -= 15
    c.drawString(70, y, f"Email: {datos['email']}")
    y -= 15
    c.drawString(70, y, f"Fecha de Auditoría: {datos['fecha_auditoria']}")
    y -= 15
    c.drawString(70, y, f"ID de Reporte: #{id_auditoria}")
    y -= 30
    
    # ============================================
    # RESUMEN EJECUTIVO
    # ============================================
    y = check_new_page(y, 200)
    
    c.setFont(font_title, 14)
    c.drawString(50, y, "RESUMEN EJECUTIVO")
    y -= 5
    c.setLineWidth(1)
    c.line(50, y, 200, y)
    y -= 25
    
    c.setFont(font_body, 10)
    
    if metricas:
        # Tabla de métricas
        c.setFont(font_title, 10)
        c.drawString(50, y, "Estadísticas Generales:")
        y -= 20
        
        c.setFont(font_body, 9)
        c.drawString(70, y, f"• Total de preguntas evaluadas: {metricas.get('preguntas_aplicables', 0)}")
        y -= 15
        c.drawString(70, y, f"• Cumplimiento total: {metricas.get('porcentaje_cumplimiento', 0)}%")
        y -= 15
        c.drawString(70, y, f"• No conformidades menores: {no_conformidades.get('total_menores', 0)}")
        y -= 15
        c.drawString(70, y, f"• No conformidades mayores: {no_conformidades.get('total_mayores', 0)}")
        y -= 15
        c.drawString(70, y, f"• Buenas prácticas identificadas: {no_conformidades.get('total_buenas_practicas', 0)}")
        y -= 30
    
    # Gráfico de pastel de cumplimiento
    if metricas and metricas.get('preguntas_aplicables', 0) > 0:
        y = check_new_page(y, 240)
        
        c.setFont(font_title, 10)
        c.drawString(50, y, "Distribución de Cumplimiento:")
        y -= 20
        
        # Crear gráfico de pastel
        drawing = Drawing(250, 180)
        pie = Pie()
        pie.x = 50
        pie.y = 20
        pie.width = 150
        pie.height = 150
        
        pie.data = [
            metricas.get('cumple', 0),
            metricas.get('no_cumple', 0),
            metricas.get('parcial', 0)
        ]
        pie.labels = [
            f"Cumple ({metricas.get('porcentaje_cumplimiento', 0)}%)",
            f"No Cumple ({metricas.get('porcentaje_no_cumplimiento', 0)}%)",
            f"Parcial ({metricas.get('porcentaje_parcial', 0)}%)"
        ]
        pie.slices.strokeWidth = 0.5
        pie.slices[0].fillColor = colors.Color(0, 0.6, 0)  # Verde
        pie.slices[1].fillColor = colors.Color(0.8, 0, 0)  # Rojo
        pie.slices[2].fillColor = colors.Color(0.9, 0.6, 0)  # Naranja
        
        drawing.add(pie)
        drawing.drawOn(c, 150, y - 180)
        y -= 200
    
    # ============================================
    # ALERTAS CRÍTICAS
    # ============================================
    if no_conformidades.get('sancion', False) or no_conformidades.get('total_mayores', 0) > 0:
        y = check_new_page(y, 150)
        
        c.setFont(font_title, 14)
        c.setFillColorRGB(0.8, 0, 0)
        c.drawString(50, y, "⚠ ALERTAS CRÍTICAS")
        c.setFillColorRGB(0, 0, 0)
        y -= 5
        c.setLineWidth(1)
        c.line(50, y, 200, y)
        y -= 25
        
        if no_conformidades.get('sancion', False):
            c.setFillColorRGB(0.8, 0, 0)
            c.rect(50, y - 35, width - 100, 40, fill=True, stroke=True)
            c.setFillColorRGB(1, 1, 1)
            c.setFont(font_title, 12)
            c.drawString(60, y - 15, "ACREEDOR A SANCIÓN ECONÓMICA")
            c.setFont(font_body, 9)
            c.drawString(60, y - 28, "Se detectaron 3 o más no conformidades mayores")
            c.setFillColorRGB(0, 0, 0)
            y -= 50
        
        if no_conformidades.get('total_mayores', 0) > 0:
            c.setFillColorRGB(1, 0.6, 0)
            c.rect(50, y - 35, width - 100, 40, fill=True, stroke=True)
            c.setFillColorRGB(0, 0, 0)
            c.setFont(font_title, 11)
            c.drawString(60, y - 15, f"NO CONFORMIDADES MAYORES: {no_conformidades.get('total_mayores', 0)}")
            c.setFont(font_body, 9)
            c.drawString(60, y - 28, f"{no_conformidades.get('total_menores', 0)} no conformidades menores acumuladas")
            y -= 50
    
    # ============================================
    # DETALLE DE NO CONFORMIDADES MENORES
    # ============================================
    if no_conformidades.get('menores', []):
        y = check_new_page(y, 150)
        
        c.setFont(font_title, 12)
        c.drawString(50, y, "NO CONFORMIDADES MENORES DETALLADAS")
        y -= 5
        c.setLineWidth(0.5)
        c.line(50, y, 300, y)
        y -= 20
        
        for idx, nc in enumerate(no_conformidades.get('menores', []), 1):
            y = check_new_page(y, 80)
            
            c.setFillColorRGB(1, 0.9, 0.7)
            c.rect(50, y - 55, width - 100, 60, fill=True, stroke=True)
            c.setFillColorRGB(0, 0, 0)
            
            c.setFont(font_title, 10)
            c.drawString(60, y - 12, f"NC Menor #{idx}")
            c.setFont(font_body, 9)
            c.drawString(60, y - 25, nc.get('descripcion', ''))
            c.drawString(60, y - 38, f"Ubicación: {nc.get('ubicacion', '')}")
            c.drawString(60, y - 50, f"Total afectadas: {len(nc.get('preguntas', []))} preguntas")
            
            y -= 65
    
    # ============================================
    # BUENAS PRÁCTICAS IDENTIFICADAS
    # ============================================
    if buenas_practicas:
        y = check_new_page(y, 150)
        
        c.setFont(font_title, 12)
        c.setFillColorRGB(0, 0.6, 0)
        c.drawString(50, y, "✓ BUENAS PRÁCTICAS IDENTIFICADAS")
        c.setFillColorRGB(0, 0, 0)
        y -= 5
        c.setLineWidth(0.5)
        c.line(50, y, 300, y)
        y -= 20
        
        for idx, bp in enumerate(buenas_practicas, 1):
            y = check_new_page(y, 70)
            
            c.setFillColorRGB(0.9, 1, 0.9)
            c.rect(50, y - 50, width - 100, 55, fill=True, stroke=True)
            c.setFillColorRGB(0, 0, 0)
            
            c.setFont(font_title, 10)
            c.drawString(60, y - 12, f"Buena Práctica #{idx}")
            c.setFont(font_body, 9)
            c.drawString(60, y - 25, bp.get('descripcion', ''))
            c.drawString(60, y - 38, f"Ubicación: {bp.get('ubicacion', '')}")
            
            y -= 60
    
    # ============================================
    # RESULTADOS DETALLADOS POR PREGUNTA
    # ============================================
    y = check_new_page(y, 150)
    
    c.setFont(font_title, 12)
    c.drawString(50, y, "RESULTADOS DETALLADOS DE LA AUDITORÍA")
    y -= 5
    c.setLineWidth(0.5)
    c.line(50, y, 350, y)
    y -= 25
    
    for i, (pregunta, respuesta) in enumerate(respuestas.items(), 1):
        y = check_new_page(y, 50)
        
        # Pregunta
        c.setFont(font_body, 9)
        pregunta_texto = pregunta[:80] + "..." if len(pregunta) > 80 else pregunta
        c.drawString(50, y, f"{i}. {pregunta_texto}")
        y -= 13
        
        # Respuesta con color
        if respuesta == "Cumple":
            c.setFillColorRGB(0, 0.6, 0)
            simbolo = "✓"
        elif respuesta == "No Cumple":
            c.setFillColorRGB(0.8, 0, 0)
            simbolo = "✗"
        elif respuesta == "Cumple Parcialmente":
            c.setFillColorRGB(0.9, 0.6, 0)
            simbolo = "~"
        else:
            c.setFillColorRGB(0.5, 0.5, 0.5)
            simbolo = "-"
        
        c.setFont(font_title, 9)
        c.drawString(70, y, f"{simbolo} {respuesta}")
        c.setFillColorRGB(0, 0, 0)
        y -= 20
    
    # ============================================
    # COMENTARIOS Y OBSERVACIONES
    # ============================================
    if comentarios:
        y = check_new_page(y, 100)
        
        c.setFont(font_title, 12)
        c.drawString(50, y, "COMENTARIOS Y OBSERVACIONES")
        y -= 5
        c.setLineWidth(0.5)
        c.line(50, y, 280, y)
        y -= 20
        
        for seccion, comentario in comentarios.items():
            y = check_new_page(y, 70)
            
            c.setFont(font_title, 9)
            titulo_seccion = seccion.replace('_', ' ').replace('comentario seccion', 'Sección').title()
            c.drawString(50, y, titulo_seccion)
            y -= 13
            
            # Dibujar comentario en caja
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(50, y - 40, width - 100, 45, fill=True, stroke=True)
            c.setFillColorRGB(0, 0, 0)
            c.setFont(font_body, 8)
            
            # Dividir texto largo
            max_width = width - 120
            words = comentario.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if stringWidth(test_line, font_body, 8) <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            y_text = y - 12
            for line in lines[:4]:
                c.drawString(60, y_text, line)
                y_text -= 10
            
            y -= 50
    
    # Número de página final
    add_page_number()
    
    c.save()
    buffer.seek(0)
    return buffer
