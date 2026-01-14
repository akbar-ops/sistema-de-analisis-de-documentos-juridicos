import os
import PyPDF2
import pandas as pd
from tqdm import tqdm
from transformers import MBartForConditionalGeneration, MBart50TokenizerFast
import torch

# ============================================================
# CONFIGURACIÓN
# ============================================================
MODEL_NAME = "facebook/mbart-large-50"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Cargar modelo y tokenizer
print(f"\n[Cargando modelo {MODEL_NAME} en {DEVICE}]")
tokenizer = MBart50TokenizerFast.from_pretrained(MODEL_NAME)
model = MBartForConditionalGeneration.from_pretrained(MODEL_NAME).to(DEVICE)

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def extraer_texto_pdf(path_pdf: str) -> str:
    """Extrae el texto completo de un archivo PDF."""
    texto = ""
    with open(path_pdf, "rb") as f:
        lector = PyPDF2.PdfReader(f)
        for pagina in lector.pages:
            texto += pagina.extract_text() or ""
    return texto.strip()


def resumir_texto(texto: str, idioma_origen="es_XX", max_tokens=200) -> str:
    """Genera un resumen del texto usando MBART-50."""
    if not texto.strip():
        return ""

    # Limitar tamaño si el texto es muy largo (por fragmentos)
    fragmentos = []
    palabras = texto.split()
    chunk_size = 900  # ~900 tokens aprox
    for i in range(0, len(palabras), chunk_size):
        parte = " ".join(palabras[i:i + chunk_size])
        fragmentos.append(parte)

    tokenizer.src_lang = idioma_origen
    res_final = []

    for parte in fragmentos:
        inputs = tokenizer(
            parte,
            max_length=1024,
            truncation=True,
            return_tensors="pt"
        ).to(DEVICE)

        resumen_ids = model.generate(
            **inputs,
            max_length=max_tokens,
            min_length=60,
            num_beams=5,
            length_penalty=2.0,
            early_stopping=True
        )

        resumen = tokenizer.decode(resumen_ids[0], skip_special_tokens=True)
        res_final.append(resumen.strip())

    # Combinar los mini-resúmenes
    resumen_total = " ".join(res_final)
    return resumen_total


# ============================================================
# PROCESAR CARPETA DE PDFs
# ============================================================

def procesar_carpeta_pdf(carpeta_input: str, salida_csv: str = "resumenes.csv"):
    """Lee todos los PDF de una carpeta, genera un resumen y guarda los resultados en un CSV."""
    resultados = []

    pdfs = [f for f in os.listdir(carpeta_input) if f.lower().endswith(".pdf")]
    if not pdfs:
        print("⚠️ No se encontraron archivos PDF en la carpeta.")
        return

    for nombre in tqdm(pdfs, desc="Resumiendo documentos"):
        ruta = os.path.join(carpeta_input, nombre)
        try:
            texto = extraer_texto_pdf(ruta)
            resumen = resumir_texto(texto)
            resultados.append({"archivo": nombre, "resumen": resumen})
        except Exception as e:
            print(f"❌ Error procesando {nombre}: {e}")

    # Guardar resultados
    df = pd.DataFrame(resultados)
    df.to_csv(salida_csv, index=False)
    print(f"\n✅ Resúmenes guardados en {salida_csv}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    carpeta = "./media/test_documents"  # 📂 Carpeta donde están tus documentos
    os.makedirs(carpeta, exist_ok=True)

    procesar_carpeta_pdf(carpeta)



