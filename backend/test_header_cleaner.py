#!/usr/bin/env python
"""
Script de prueba para el HeaderCleanerService.

Prueba la limpieza de encabezados con ejemplos reales de documentos judiciales.

Uso:
    python test_header_cleaner.py
    python test_header_cleaner.py --verbose
"""
import sys
import os

# Agregar el directorio de la app al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.documents.services.header_cleaner_service import HeaderCleanerService

# Ejemplos de texto extraído de documentos judiciales reales (proporcionados por el usuario)
SAMPLE_TEXTS = [
    # Ejemplo 1: Sentencia Laboral
    """CORTE SUPERIOR SALA LABORAL DE PUNO

DE JUSTICIA EXP. N.° 00142-2015-0-2111-JM-LA-03

DE PUNO PROCEDE: SAN ROMAN

Página 1 de 14

SENTENCIA DE SEGUNDO GRADO N.° 003-2025-ALPT:

EXPEDIENTE : 00142-2015-0-2111-JM-LA-03

DEMANDANTE : SANDRA YANETH VARGAS MIRANDA

DEMANDADA : UNIVERSIDAD ANDINA NÉSTOR CÁCERES VELÁSQUEZ

Representada por su apoderado judicial

MATERIA : REINTEGRO DE REMUNERACIONES, PAGO DE BENEFICIOS

ECONÓMICOS (PACTOS COLECTIVOS), REINTEGRO DE

BENEFICIOS SOCIALES (GRATIFICACIONES Y CTS), PAGO DE

VACACIONES NO GOZADAS Y HORAS EXTRA

VÍA PROCESAL : ORDINARIO LABORAL (Ley 26636)

PROCEDENCIA : PRIMER JUZGADO CIVIL SAN ROMÁN – JULIACA

PONENTE : JUEZ SUPERIOR ROBERTO CONDORI TICONA

RESOLUCIÓN N° 36-2025

Puno, quince de enero del año dos mil veinticinco.-

I. ASUNTO:

Corresponde a esta Superior Sala Laboral resolver el recurso de apelación

presentado por la demandada contra la sentencia de primer grado en el""",

    # Ejemplo 2: Sentencia Penal con OCR corrupto
    """/g3

/g19/g18/g7/g8/g21/g3/g13/g24/g7/g12/g6/g12/g4/g15/g3/g7/g8/g15/g3/g19/g8/g21/g108/g3

/g6/g18/g21/g23/g8/g3/g22/g24/g19/g8/g21/g12/g18/g21/g3/g7/g8/g3/g13/g24/g22/g23/g12/g6/g12/g4/g3/g7/g8/g3/g19/g24/g17/g18/g3

/g22/g131/g142/g131/g3/g19/g135/g144/g131/g142/g3/g134/g135/g3/g4/g146/g135/g142/g131/g133/g139/g145/g144/g135/g149/g3/g135/g144/g3/g131/g134/g139/g133/g139/g215/g144/g3/g22/g131/g142/g131/g3/g19/g135/g144/g131/g142/g3/g15/g139/g147 /g151/g139/g134/g131/g134/g145/g148/g131/g3/g155/g3/g3

/g4/g144/g150/g139/g133/g145/g148/g148/g151/g146/g133/g139/g215/g144/g3/g134/g135/g3/g142/g131/g3/g146/g148/g145/g152/g139/g144/g133/g139/g131/g3/g134/g135/g3/g19/g151/g144/g145 /g3

1 SENTENCIA DE VISTA Nro. 316-2022

Expediente N° : 01972-2018-76-2101-JR-PE-02.

Procede : Segundo Juzgado Penal Unipersonal de Puno.

Encausada : María Elizabeth Inquilla Yana.

Agraviada : Dionisia Silvia Calsin Vilca.

Delito: : Usurpación simple.

Asunto : Apelación de sentencia condenatoria.""",

    # Ejemplo 3: Página 2 de documento (con encabezado repetido)
    """CORTE SUPERIOR SALA LABORAL DE PUNO

DE JUSTICIA EXP. N° 02273-2018-0-2101-JR-CA-02

DE PUNO PROCEDE: PUNO

Página 2 de 18 compensación vacacional anual y de las bonificaciones especiales previstas por

los Decretos de Urgencia Nos 090-96, 073-97 y 011-99, incluyendo la

remuneración básica de S/ 50.00 soles en la base de cálculo de dichos

beneficios, conforme al mandato del Decreto de Urgencia N° 105-2001".

(énfasis añadido)

"Pretensiones accesorias:

1) Se ordene a la demandada reajustar, en adelante, su pensión mensual de

cesantía mediante el recálculo y pago de:

a) La remuneración o bonificación personal en base a la remuneración

básica de S/ 50.00 soles, en la proporción del 2% por cada año de

servicios;

b) El recálculo y pago de la bonificación diferencial incluyendo los S/

50.00 soles de remuneración básica en la base de cálculo;

c) Otorgar la compensación vacacional anual de una remuneración""",

    # Ejemplo 4: Sentencia Penal de Vista
    """C O R T E S U P E R I O R D E J U S T I C I A D E P U N O

SALA PENAL DE APELACIONES EN ADICIÓN SALA PENAL LIQUIDADORA Y

ESPECIALIZADA EN DELITOS DE CORRUPCIÓN DE FUNCIONARIOS DE PUNO

SENTENCIA DE VISTA N° 027 - 2023

Expediente Nº : 04060-2019-7-2101-JR-PE-02

Imputado : Roberto Córdova Quispe y otros

Delito : Usurpación agravada

Agraviado : Bernardino Ccuno Vilca y otros

Procedencia : Primer Juzgado Penal Unipersonal de Puno

ASUNTO : Apelación de sentencia condenatoria

CONFORMACIÓN : J.S. Luque Mamani

: J.S. Arpasi Pacho

PONENTE : J.S. Ayestas Ardiles

Resolución Nro. 21

Puno, veintitrés de marzo

del año dos mil veintitrés.

I.- VISTOS y OIDOS:

En audiencia realizada por los miembros integrantes de la Sala

Penal de Apelaciones de la Corte Superior de Justicia de Puno, provincia de

Puno, Presidida por el señor Juez Superior REYNALDO LUQUE MAMANI e""",

    # Ejemplo 5: Resolución de devolución
    """SALA LABORAL - SEDE ANEXA PUNO

EXPEDIENTE : 01637-2023-0-2101-JR-LA-01

MATERIA : INDEMNIZACIÓN POR DESPIDO ARBITRARIO Y

OTROS

RELATOR : CASTILLO SOLÓRZANO, RAÚL ANÍBAL

PROCURADOR PÚBLICO : PROCURADOR PÚBLICO DEL

MINISTERIO DE DESARROLLO AGRARIO Y

RIEGO

DEMANDADO : PROYECTO ESPECIAL BINACIONAL LAGO TITICACA

DEMANDANTE : HOLGUÍN VELÁSQUEZ, JHANNET

Resolución Nro. 10-2025

Puno, once de abril del año dos mil veinticinco.-

DADO CUENTA: No habiendo sido impugnada la sentencia de segundo

grado que antecede, dentro del plazo que las partes tenían para hacerlo;

DISPUSIERON: DEVOLVER estos autos al Juzgado de origen, para que

proceda conforme se tiene ordenado en la misma.

DISPUSIERON : que la presente resolución sea suscrita por la Secretaria

de Sala, atendiendo a lo previsto en el último párrafo del artículo 122° del

Código Procesal Civil1, de aplicación supletoria al caso.

S.S.

SALINAS MENDOZA

CONDORI TICONA

DÍAZ HAYTARA.""",
]


def print_comparison(original: str, cleaned: str, stats: dict, title: str = ""):
    """Imprime comparación lado a lado."""
    print("\n" + "="*80)
    if title:
        print(f"📄 {title}")
    print("="*80)
    
    print(f"\n🔴 ORIGINAL ({stats['original_chars']:,} caracteres, {stats['original_lines']} líneas):")
    print("-"*40)
    # Mostrar primeras 500 caracteres
    preview = original[:500]
    if len(original) > 500:
        preview += "\n... [truncado]"
    print(preview)
    
    print(f"\n🟢 LIMPIO ({stats['cleaned_chars']:,} caracteres, {stats['cleaned_lines']} líneas):")
    print("-"*40)
    preview = cleaned[:500]
    if len(cleaned) > 500:
        preview += "\n... [truncado]"
    print(preview)
    
    print(f"\n📊 ESTADÍSTICAS:")
    print(f"   • Caracteres removidos: {stats['chars_removed']:,} ({stats['chars_removed_percent']}%)")
    print(f"   • Líneas removidas: {stats['lines_removed']}")
    print(f"   • Palabras removidas: {stats['words_removed']}")


def test_individual_texts():
    """Prueba la limpieza de textos individuales."""
    print("\n" + "🧪"*30)
    print("PRUEBA DE LIMPIEZA DE TEXTOS INDIVIDUALES")
    print("🧪"*30)
    
    cleaner = HeaderCleanerService()
    
    titles = [
        "Sentencia Laboral - Primera Página",
        "Sentencia Penal con OCR Corrupto",
        "Página 2 de Documento (encabezados repetidos)",
        "Sentencia Penal de Vista",
        "Resolución de Devolución"
    ]
    
    total_original = 0
    total_cleaned = 0
    
    for i, (text, title) in enumerate(zip(SAMPLE_TEXTS, titles), 1):
        cleaned = cleaner.clean_document_text(text)
        stats = cleaner.get_cleaning_stats(text, cleaned)
        
        print_comparison(text, cleaned, stats, f"Ejemplo {i}: {title}")
        
        total_original += stats['original_chars']
        total_cleaned += stats['cleaned_chars']
    
    # Resumen total
    print("\n" + "="*80)
    print("📈 RESUMEN TOTAL")
    print("="*80)
    total_removed = total_original - total_cleaned
    percent = (total_removed / total_original * 100) if total_original > 0 else 0
    print(f"   • Total caracteres originales: {total_original:,}")
    print(f"   • Total caracteres limpios: {total_cleaned:,}")
    print(f"   • Total removidos: {total_removed:,} ({percent:.1f}%)")


def test_multi_page_document():
    """Prueba la detección de encabezados repetidos entre páginas."""
    print("\n" + "📑"*30)
    print("PRUEBA DE DETECCIÓN DE ENCABEZADOS REPETIDOS (MULTI-PÁGINA)")
    print("📑"*30)
    
    # Simular un documento de 3 páginas con encabezados repetidos
    pages = [
        (1, """CORTE SUPERIOR SALA LABORAL DE PUNO
DE JUSTICIA EXP. N° 00142-2015-0-2111-JM-LA-03
DE PUNO PROCEDE: SAN ROMAN
Página 1 de 3

I. ASUNTO:
Corresponde a esta Superior Sala Laboral resolver el recurso de apelación
presentado por la demandada contra la sentencia de primer grado.

II. ANTECEDENTES:
El demandante interpuso demanda solicitando el pago de beneficios sociales."""),
        
        (2, """CORTE SUPERIOR SALA LABORAL DE PUNO
DE JUSTICIA EXP. N° 00142-2015-0-2111-JM-LA-03
DE PUNO PROCEDE: SAN ROMAN
Página 2 de 3

III. FUNDAMENTOS:
PRIMERO.- Que, el artículo 24 de la Constitución Política del Estado
establece que el trabajador tiene derecho a una remuneración equitativa.

SEGUNDO.- Que, conforme al Decreto Legislativo 728, el trabajador tiene
derecho a percibir sus beneficios sociales."""),
        
        (3, """CORTE SUPERIOR SALA LABORAL DE PUNO
DE JUSTICIA EXP. N° 00142-2015-0-2111-JM-LA-03
DE PUNO PROCEDE: SAN ROMAN
Página 3 de 3

IV. DECISIÓN:
Por estas consideraciones, esta Sala Laboral RESUELVE:
CONFIRMAR la sentencia apelada que declara FUNDADA la demanda.

Notifíquese y devuélvase.
S.S.
CONDORI TICONA
DÍAZ HAYTARA"""),
    ]
    
    cleaner = HeaderCleanerService()
    
    print("\n📄 Páginas originales:")
    print("-"*40)
    for page_num, text in pages:
        print(f"\n--- PÁGINA {page_num} ({len(text)} chars) ---")
        print(text[:200] + "..." if len(text) > 200 else text)
    
    # Limpiar páginas
    cleaned_pages = cleaner.clean_pages_text(pages)
    
    print("\n\n🧹 Páginas limpias:")
    print("-"*40)
    for page_num, text in cleaned_pages:
        print(f"\n--- PÁGINA {page_num} ({len(text)} chars) ---")
        print(text[:200] + "..." if len(text) > 200 else text)
    
    # Estadísticas
    original_total = sum(len(t) for _, t in pages)
    cleaned_total = sum(len(t) for _, t in cleaned_pages)
    removed = original_total - cleaned_total
    percent = (removed / original_total * 100) if original_total > 0 else 0
    
    print("\n\n📊 ESTADÍSTICAS:")
    print(f"   • Caracteres originales: {original_total:,}")
    print(f"   • Caracteres limpios: {cleaned_total:,}")
    print(f"   • Removidos: {removed:,} ({percent:.1f}%)")


def test_ocr_artifacts():
    """Prueba la limpieza de artefactos OCR."""
    print("\n" + "🔧"*30)
    print("PRUEBA DE LIMPIEZA DE ARTEFACTOS OCR")
    print("🔧"*30)
    
    ocr_text = """/g3/g19/g18/g7/g8/g21/g3/g13/g24/g7/g12/g6/g12/g4/g15/g3

Este es contenido normal del documento que debe mantenerse.

/g22/g131/g142/g131/g3/g19/g135/g144/g131/g142

Más contenido importante sobre el caso penal.

1 SENTENCIA DE VISTA Nro. 316-2022

El acusado fue encontrado culpable de los cargos."""

    cleaner = HeaderCleanerService()
    cleaned = cleaner.clean_document_text(ocr_text)
    stats = cleaner.get_cleaning_stats(ocr_text, cleaned)
    
    print_comparison(ocr_text, cleaned, stats, "Texto con artefactos OCR")


if __name__ == '__main__':
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    print("\n" + "="*80)
    print("🧪 HEADER CLEANER SERVICE - TEST SUITE")
    print("="*80)
    print("Probando la limpieza de encabezados de documentos judiciales del Perú")
    
    # Ejecutar pruebas
    test_individual_texts()
    test_multi_page_document()
    test_ocr_artifacts()
    
    print("\n" + "="*80)
    print("✅ PRUEBAS COMPLETADAS")
    print("="*80)
    print("\nPara aplicar la limpieza a documentos existentes:")
    print("  python manage.py regenerate_chunks_clean --dry-run")
    print("  python manage.py regenerate_chunks_clean --force")
