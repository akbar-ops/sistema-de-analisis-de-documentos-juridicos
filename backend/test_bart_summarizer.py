"""
Script de prueba para comparar resúmenes de BART vs Ollama

Uso:
    python test_bart_summarizer.py

Este script:
1. Carga un documento de ejemplo de la BD
2. Genera resumen con BART
3. Genera resumen con Ollama (si está disponible)
4. Compara ambos resúmenes
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.models import Document
from apps.documents.services.document_summarizer import DocumentSummarizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_separator():
    print("\n" + "=" * 80 + "\n")


def test_bart_summarizer():
    """Prueba el summarizer con BART."""
    
    print_separator()
    print("🧪 TEST DE BART LARGE CNN SUMMARIZER")
    print_separator()
    
    # Obtener un documento de ejemplo
    document = Document.objects.filter(content__isnull=False).last()
    
    if not document:
        print("❌ No hay documentos en la base de datos para probar")
        return
    
    print(f"📄 Documento seleccionado:")
    print(f"   ID: {document.document_id}")
    print(f"   Tipo: {document.doc_type.name if document.doc_type else 'N/A'}")
    print(f"   Área: {document.legal_area.name if document.legal_area else 'N/A'}")
    print(f"   Contenido: {len(document.content)} caracteres")
    
    # Preparar datos
    doc_type = document.doc_type.name if document.doc_type else "Documento Legal"
    legal_area = document.legal_area.name if document.legal_area else "General"
    legal_subject = document.legal_subject
    
    print_separator()
    print("🤖 GENERANDO RESUMEN CON BART...")
    print_separator()
    
    # Forzar uso de BART
    from apps.documents.services import document_summarizer
    original_flag = document_summarizer.USE_BART
    document_summarizer.USE_BART = True
    
    try:
        summarizer = DocumentSummarizer()
        
        bart_summary = summarizer.generate_summary(
            document.content,
            doc_type,
            legal_area,
            legal_subject
        )
        
        print("✅ Resumen generado con BART:\n")
        print(bart_summary['summary_text'])
        
        print_separator()
        print("📊 COMPONENTES DEL RESUMEN:")
        print_separator()
        
        print("1️⃣ Executive Summary:")
        print(bart_summary['executive_summary'][:300] + "..." if len(bart_summary['executive_summary']) > 300 else bart_summary['executive_summary'])
        print()
        
        print("2️⃣ Fechas Importantes:")
        if bart_summary['important_dates']:
            print(bart_summary['important_dates'][:200] + "..." if len(bart_summary['important_dates']) > 200 else bart_summary['important_dates'])
        else:
            print("No se encontraron fechas")
        print()
        
        print("3️⃣ Decisión/Fallo:")
        if bart_summary['decision']:
            print(bart_summary['decision'][:200] + "..." if len(bart_summary['decision']) > 200 else bart_summary['decision'])
        else:
            print("No se encontró decisión")
        print()
        
        print("4️⃣ Keywords:")
        print(bart_summary['keywords'])
        
    except Exception as e:
        print(f"❌ Error al generar resumen con BART: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restaurar flag original
        document_summarizer.USE_BART = original_flag
    
    print_separator()
    print("🔄 COMPARACIÓN CON OLLAMA (si está disponible)...")
    print_separator()
    
    # Probar con Ollama
    document_summarizer.USE_BART = False
    
    try:
        summarizer_ollama = DocumentSummarizer()
        
        ollama_summary = summarizer_ollama.generate_summary(
            document.content,
            doc_type,
            legal_area,
            legal_subject
        )
        
        print("✅ Resumen generado con Ollama:\n")
        print(ollama_summary['summary_text'])
        
    except Exception as e:
        print(f"⚠️ No se pudo generar resumen con Ollama: {e}")
    finally:
        # Restaurar flag original
        document_summarizer.USE_BART = original_flag
    
    print_separator()
    print("✨ PRUEBA COMPLETADA")
    print_separator()


def test_bart_only():
    """Prueba solo BART con un texto de ejemplo."""
    
    print_separator()
    print("🧪 TEST RÁPIDO DE BART")
    print_separator()
    
    texto_ejemplo = """
    SENTENCIA
    
    CORTE SUPERIOR DE JUSTICIA DE LIMA
    PRIMERA SALA PENAL PARA PROCESOS CON REOS LIBRES
    
    EXPEDIENTE: 12345-2023
    JUEZ PONENTE: Dr. Juan Pérez García
    FECHA: 15 de marzo de 2024
    
    VISTOS: Los autos seguidos contra Juan Carlos Rodríguez Mamani por el delito contra el 
    patrimonio en la modalidad de robo agravado en agravio de María Teresa Flores López.
    
    HECHOS: El día 10 de enero de 2024, siendo aproximadamente las 23:00 horas, en circunstancias 
    que la agraviada María Teresa Flores López transitaba por la Av. Principal 123, distrito de 
    San Juan de Lurigancho, fue interceptada por el acusado Juan Carlos Rodríguez Mamani, quien 
    portando un arma blanca tipo cuchillo de aproximadamente 20 cm, bajo amenaza le sustrajo su 
    cartera conteniendo la suma de S/ 500.00 soles, un celular marca Samsung modelo A54 valorizado 
    en S/ 1,200.00 soles, y documentos personales.
    
    CONSIDERANDOS:
    PRIMERO: Que, el artículo 188 del Código Penal establece el tipo base de robo, mientras que 
    el artículo 189 inciso 4 agrava la conducta cuando se realiza durante la noche o en lugar 
    desolado, siendo que en el presente caso se configuran ambas circunstancias.
    
    SEGUNDO: Que, está acreditado con el acta de intervención policial de fecha 10/01/2024 que 
    el acusado fue intervenido en flagrancia delictiva a 200 metros del lugar de los hechos, 
    encontrándosele en su poder los bienes sustraídos.
    
    TERCERO: Que, la declaración de la agraviada es coherente y persistente, corroborada con 
    el reconocimiento en rueda de personas realizado el 12/01/2024.
    
    SE RESUELVE:
    
    1. CONDENAR a Juan Carlos Rodríguez Mamani como autor del delito contra el patrimonio en la 
    modalidad de ROBO AGRAVADO en agravio de María Teresa Flores López, a OCHO AÑOS DE PENA 
    PRIVATIVA DE LIBERTAD EFECTIVA.
    
    2. FIJAR la reparación civil en la suma de TRES MIL SOLES (S/ 3,000.00) a favor de la agraviada.
    
    3. DISPONER la inscripción de la presente sentencia en el Registro Central de Condenas.
    
    Regístrese, comuníquese y archívese.
    """
    
    from apps.core.services.bart_summarizer import BARTSummarizer
    
    try:
        print("🔄 Inicializando BART (esto puede tomar un momento la primera vez)...")
        bart = BARTSummarizer()
        
        print("✅ BART cargado correctamente\n")
        
        print("📝 Generando resumen abstractivo...")
        summary_abstractive = bart.generate_abstractive_summary(texto_ejemplo)
        print(f"\nRESUMEN ABSTRACTIVO:\n{summary_abstractive}\n")
        
        print("=" * 80)
        
        print("📝 Generando resumen extractivo...")
        summary_extractive = bart.generate_extractive_summary(texto_ejemplo)
        print(f"\nRESUMEN EXTRACTIVO:\n{summary_extractive}\n")
        
        print("=" * 80)
        
        print("📝 Generando bullet points...")
        summary_bullets = bart.generate_bullet_points(texto_ejemplo)
        print(f"\nBULLET POINTS:\n{summary_bullets}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print_separator()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test BART Summarizer')
    parser.add_argument(
        '--quick', 
        action='store_true', 
        help='Ejecutar prueba rápida con texto de ejemplo'
    )
    
    args = parser.parse_args()
    
    if args.quick:
        test_bart_only()
    else:
        test_bart_summarizer()
