"""
Script para verificar la instalación de BART y sus dependencias
"""
import sys


def check_imports():
    """Verifica que todas las librerías estén instaladas."""
    print("🔍 Verificando dependencias...\n")
    
    errors = []
    
    # PyTorch
    try:
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
        
        if torch.cuda.is_available():
            print(f"   🎮 CUDA disponible: {torch.version.cuda}")
            print(f"   🎮 GPU: {torch.cuda.get_device_name(0)}")
        else:
            print(f"   💻 Usando CPU (no se detectó GPU CUDA)")
    except ImportError:
        errors.append("PyTorch no está instalado")
        print("❌ PyTorch no encontrado")
    
    # Transformers
    try:
        import transformers
        print(f"✅ Transformers: {transformers.__version__}")
    except ImportError:
        errors.append("Transformers no está instalado")
        print("❌ Transformers no encontrado")
    
    # Sentencepiece
    try:
        import sentencepiece
        print(f"✅ Sentencepiece instalado")
    except ImportError:
        errors.append("Sentencepiece no está instalado")
        print("❌ Sentencepiece no encontrado")
    
    return errors


def check_model():
    """Intenta cargar el modelo BART."""
    print("\n🤖 Verificando modelo BART...\n")
    
    try:
        from transformers import BartForConditionalGeneration, BartTokenizer
        import os
        
        print("🔄 Cargando tokenizer...")
        tokenizer = BartTokenizer.from_pretrained('facebook/bart-large-cnn')
        print("✅ Tokenizer cargado")
        
        print("🔄 Cargando modelo (esto puede tomar un momento)...")
        model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
        print("✅ Modelo cargado exitosamente")
        
        cache_dir = os.path.expanduser('~/.cache/huggingface/hub/')
        print(f"📁 Ubicación del cache: {cache_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al cargar el modelo: {e}")
        return False


def test_summarization():
    """Prueba de resumen simple."""
    print("\n🧪 Prueba de resumen rápido...\n")
    
    try:
        from apps.core.services.bart_summarizer import BARTSummarizer
        
        texto = """
        La Corte Superior de Justicia de Lima condenó a Juan Pérez por el delito 
        de robo agravado. El acusado utilizó un arma blanca para amenazar a la 
        víctima en horas de la noche, sustrayéndole bienes valorados en 3,000 soles. 
        La pena impuesta fue de 8 años de prisión efectiva y una reparación civil 
        de 5,000 soles. El fallo se fundamentó en las pruebas presentadas y el 
        testimonio de la víctima.
        """
        
        bart = BARTSummarizer()
        resumen = bart.generate_bullet_points(texto)
        
        print("📄 Texto original:")
        print(texto.strip())
        print("\n📝 Resumen generado por BART:")
        print(resumen)
        print("\n✅ ¡Prueba exitosa!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("="*60)
    print("🔧 VERIFICACIÓN DE INSTALACIÓN DE BART")
    print("="*60)
    print()
    
    # Verificar imports
    errors = check_imports()
    
    if errors:
        print("\n❌ ERRORES ENCONTRADOS:")
        for error in errors:
            print(f"   - {error}")
        print("\nPara instalar:")
        print("   pip install transformers torch sentencepiece")
        print("O ejecuta:")
        print("   bash install_bart.sh")
        sys.exit(1)
    
    # Verificar modelo
    model_ok = check_model()
    
    if not model_ok:
        print("\n⚠️  El modelo no se pudo cargar.")
        print("   Esto es normal si es la primera vez.")
        print("   Ejecuta: python test_bart_summarizer.py --quick")
        print("   para descargar el modelo automáticamente.")
        return
    
    # Prueba de resumen
    test_ok = test_summarization()
    
    print("\n" + "="*60)
    if test_ok:
        print("✅ TODO ESTÁ LISTO PARA USAR BART")
        print("="*60)
        print("\nPróximos pasos:")
        print("1. Edita: apps/documents/services/document_summarizer.py")
        print("2. Cambia la línea 17 a: USE_BART = True")
        print("3. Reinicia tu servidor Django")
        print("\nPara más información: cat BART_IMPLEMENTATION.md")
    else:
        print("⚠️  VERIFICACIÓN INCOMPLETA")
        print("="*60)
        print("\nRevisa los errores arriba y consulta BART_IMPLEMENTATION.md")
    print()


if __name__ == "__main__":
    main()
