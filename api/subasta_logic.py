# api/subasta_logic.py
"""
Lógica de negocio para análisis de subastas
Extraído de Subasta.py y adaptado para web
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re

# Campos de datos de subasta
CAMPOS = [
    'Identificador', 'Fecha de conclusión', 'Cantidad reclamada',
    'Valor subasta', 'Tasación', 'Tramos entre pujas',
    'Importe del depósito', 'Dirección', 'Referencia catastral'
]


def limpiar_entero_por_texto(texto):
    """Limpia un número con formato español (puntos como miles, comas como decimales)"""
    texto = texto.replace('.', '').replace(',', '.').replace(' ', '').strip()
    if ',' in texto:
        texto = texto.split(',')[0]
    elif '.' in texto:
        texto = texto.split('.')[0]
    return texto


def construir_urls(urlbase):
    """Construye URLs de información y bienes"""
    p = urlparse(urlbase)
    query = parse_qs(p.query)
    
    base_url = f"{p.scheme}://{p.netloc}{p.path}"
    params = []
    
    for k in query:
        if k == 'ver':
            continue
        params.extend([f"{k}={query[k][0]}"])
    
    rest = '&'.join(params)
    url_info = f"{base_url}?ver=1&{rest}"
    url_bienes = f"{base_url}?ver=3&{rest}"
    
    return url_info, url_bienes


def extraer_datos_subasta(urlbase):
    """Extrae datos de la subasta desde la URL del BOE"""
    urls = construir_urls(urlbase)
    resultados = {campo: '' for campo in CAMPOS}
    direccion_componentes = []
    
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tabla in soup.find_all('table'):
                for fila in tabla.find_all('tr'):
                    th = fila.find('th')
                    td = fila.find('td')
                    
                    if not th or not td:
                        continue
                    
                    campo = th.text.strip().lower()
                    valor = td.text.strip()
                    
                    # Identificador
                    if 'identificador' in campo and not resultados['Identificador']:
                        resultados['Identificador'] = valor
                    
                    # Fecha de conclusión
                    elif 'conclusión' in campo and not resultados['Fecha de conclusión']:
                        resultados['Fecha de conclusión'] = valor
                    
                    # Cantidad reclamada
                    elif 'cantidad reclamada' in campo and not resultados['Cantidad reclamada']:
                        resultados['Cantidad reclamada'] = limpiar_entero_por_texto(valor)
                    
                    # Valor subasta
                    elif 'valor subasta' in campo and not resultados['Valor subasta']:
                        resultados['Valor subasta'] = limpiar_entero_por_texto(valor)
                    
                    # Tasación
                    elif 'tasación' in campo and not resultados['Tasación']:
                        resultados['Tasación'] = limpiar_entero_por_texto(valor)
                    
                    # Tramos entre pujas
                    elif 'tramos entre pujas' in campo and not resultados['Tramos entre pujas']:
                        resultados['Tramos entre pujas'] = limpiar_entero_por_texto(valor)
                    
                    # Depósito
                    elif 'depósito' in campo and not resultados['Importe del depósito']:
                        resultados['Importe del depósito'] = limpiar_entero_por_texto(valor)
                    
                    # Dirección y componentes
                    elif 'dirección' in campo or 'ubicación' in campo or 'domicilio' in campo or 'bien' in campo:
                        direccion_componentes.append(valor)
                    elif 'código postal' in campo:
                        direccion_componentes.append(f"CP {valor}")
                    elif 'localidad' in campo or 'municipio' in campo:
                        direccion_componentes.append(valor)
                    elif 'provincia' in campo:
                        direccion_componentes.append(valor)
                    
                    # Referencia catastral
                    elif ('referencia catastral' in campo or 'catastral' in campo) and not resultados['Referencia catastral']:
                        resultados['Referencia catastral'] = valor
        
        except Exception as e:
            # En caso de error, continuar sin interrumpir
            pass
    
    # Construir dirección completa
    resultados['Dirección'] = ', '.join([c for c in direccion_componentes if c])
    
    return resultados


def calcular_porcentaje_puja(puja, valor_subasta):
    """Calcula el porcentaje de la puja sobre el valor de subasta"""
    try:
        puja_float = float(puja)
        valor_subasta_float = float(valor_subasta)
        
        if valor_subasta_float == 0:
            return None, "Error: Valor de subasta no puede ser 0"
        
        porcentaje = (puja_float / valor_subasta_float) * 100
        
        # Determinar veredicto
        if porcentaje >= 70:
            veredicto = "ADJUDICADO"
            color = "success"
        elif porcentaje >= 50:
            veredicto = "POSIBLEMENTE"
            color = "warning"
        else:
            veredicto = "DEPENDE JUZGADO"
            color = "danger"
        
        return {
            'porcentaje': round(porcentaje, 2),
            'veredicto': veredicto,
            'color': color
        }, None
    
    except ValueError:
        return None, "Error: Valores inválidos"


def calcular_itp_notaria(valor_referencia, itp_porcentaje):
    """Calcula ITP y gastos de notaría/registro"""
    try:
        val_ref = float(valor_referencia)
        itp_pct = float(itp_porcentaje)
        
        itp = val_ref * (itp_pct / 100)
        notaria = val_ref * 0.03  # 3% simplificado
        
        return {
            'itp': round(itp, 2),
            'notaria': round(notaria, 2)
        }, None
    
    except ValueError:
        return None, "Error en cálculo de ITP"


def calcular_ibi_judicial(ibi_anual, ano_procedimiento, ano_actual=None):
    """Calcula IBI acumulado judicial"""
    try:
        if ano_actual is None:
            from datetime import datetime
            ano_actual = datetime.now().year
        
        ibi = float(ibi_anual)
        anos_total = ano_actual - int(ano_procedimiento) + 2  # +2 por año actual y siguiente
        
        if anos_total < 0:
            anos_total = 0
        
        total_ibi = ibi * anos_total
        
        return {
            'anos_total': anos_total,
            'total_ibi': round(total_ibi, 2)
        }, None
    
    except (ValueError, TypeError):
        return None, "Error en cálculo de IBI"


def calcular_comunidad_judicial(comunidad_anual, anos_total):
    """Calcula comunidad acumulada judicial"""
    try:
        comu = float(comunidad_anual)
        anos = int(anos_total)
        
        total_comunidad = comu * anos
        
        return round(total_comunidad, 2), None
    
    except (ValueError, TypeError):
        return None, "Error en cálculo de comunidad"


def calcular_total_inversion(puja_max, itp, notaria, ibi_total, comunidad_total, 
                            alarmas, suministros, reforma):
    """Calcula el total de inversión"""
    try:
        total = (
            float(puja_max or 0) +
            float(itp or 0) +
            float(notaria or 0) +
            float(ibi_total or 0) +
            float(comunidad_total or 0) +
            float(alarmas or 0) +
            float(suministros or 0) +
            float(reforma or 0)
        )
        
        return round(total, 2), None
    
    except (ValueError, TypeError):
        return None, "Error en cálculo de inversión total"


def calcular_margen_rentabilidad(precio_venta, total_inversion):
    """Calcula margen y rentabilidad porcentual"""
    try:
        venta = float(precio_venta)
        inversion = float(total_inversion)
        
        if inversion == 0:
            return None, "Error: Inversión no puede ser 0"
        
        margen = venta - inversion
        rentabilidad = (margen / inversion) * 100
        
        return {
            'margen': round(margen, 2),
            'rentabilidad': round(rentabilidad, 2),
            'positivo': margen > 0
        }, None
    
    except (ValueError, TypeError):
        return None, "Error en cálculo de rentabilidad"


def formatear_numero(numero):
    """Formatea un número al estilo español (1.234.567,89)"""
    try:
        num = float(numero)
        # Formato con separador de miles y 2 decimales
        formatted = f"{num:,.2f}"
        # Cambiar formato inglés a español
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    except:
        return str(numero)
