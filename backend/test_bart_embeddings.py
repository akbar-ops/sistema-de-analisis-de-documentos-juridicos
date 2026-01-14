"""
Prueba rápida de mBART optimizado para embeddings (español)
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.services.bart_summarizer import BARTSummarizer

# Texto de ejemplo
texto = """
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

La agraviada inmediatamente dio aviso a la policía, quienes en un operativo lograron 
intervenir al acusado a 200 metros del lugar de los hechos, encontrándosele en su poder 
todos los bienes sustraídos. El acusado presentaba signos de ebriedad al momento de la 
intervención.

CONSIDERANDOS:

PRIMERO: Que, el artículo 188 del Código Penal establece el tipo base de robo, mientras que 
el artículo 189 inciso 4 agrava la conducta cuando se realiza durante la noche o en lugar 
desolado, siendo que en el presente caso se configuran ambas circunstancias agravantes.

SEGUNDO: Que, está acreditado con el acta de intervención policial de fecha 10/01/2024 que 
el acusado fue intervenido en flagrancia delictiva a 200 metros del lugar de los hechos, 
encontrándosele en su poder los bienes sustraídos, lo cual constituye prueba directa de su 
participación en el ilícito.

TERCERO: Que, la declaración de la agraviada es coherente, persistente y corroborada con 
el reconocimiento en rueda de personas realizado el 12/01/2024, donde identificó 
plenamente al acusado como la persona que le sustrajo sus pertenencias bajo amenaza.

CUARTO: Que, el examen de alcoholemia practicado al acusado arrojó 1.8 gramos de alcohol 
por litro de sangre, lo que evidencia estado de ebriedad, sin embargo, esto no exime de 
responsabilidad penal conforme al artículo 20 inciso 1 del Código Penal.

QUINTO: Que, el acusado cuenta con antecedentes penales por el delito de hurto agravado 
cometido en el año 2021, lo que evidencia su reincidencia delictiva.

SE RESUELVE:

1. CONDENAR a Juan Carlos Rodríguez Mamani, identificado con DNI 12345678, como autor 
del delito contra el patrimonio en la modalidad de ROBO AGRAVADO en agravio de María 
Teresa Flores López, a OCHO AÑOS DE PENA PRIVATIVA DE LIBERTAD EFECTIVA.

2. FIJAR la reparación civil en la suma de TRES MIL SOLES (S/ 3,000.00) que deberá 
abonar el sentenciado a favor de la agraviada María Teresa Flores López.

3. DISPONER la inscripción de la presente sentencia en el Registro Central de Condenas.

4. ORDENAR que consentida o ejecutoriada que sea la presente resolución, se remitan los 
boletines de condena correspondientes.

Regístrese, comuníquese y archívese.
"""

print("="*80)
print("PRUEBA DE mBART MULTILINGÜE PARA EMBEDDINGS (ESPAÑOL)")
print("="*80)
print("\n🔄 Inicializando mBART (modelo multilingüe optimizado para español)...")

bart = BARTSummarizer()  # Por defecto usa facebook/mbart-large-50

print("✅ mBART cargado\n")
print("📝 Generando resumen DENSO para embeddings...")
print("   Modelo: facebook/mbart-large-50 (multilingüe)")
print("   Configuración adaptativa según GPU")
print("   (Esto puede tomar 30-60 segundos para máxima calidad)\n")

resumen = bart.generate_dense_summary_for_embeddings(texto)

print("="*80)
print("RESUMEN GENERADO EN ESPAÑOL (sin formato, optimizado para embeddings)")
print("="*80)
print(resumen)
print("\n" + "="*80)
print(f"Longitud del resumen: {len(resumen)} caracteres")
print(f"Longitud del original: {len(texto)} caracteres")
print(f"Ratio de compresión: {len(resumen)/len(texto)*100:.1f}%")
print("="*80)
print("\n💡 Este resumen está optimizado para:")
print("   - Generar embeddings de alta calidad")
print("   - Búsqueda por similitud semántica")
print("   - Capturar toda la información relevante")
print("   - Idioma español (modelo multilingüe)")
print("="*80)
