"""
BART Large CNN Summarizer Service

Servicio para generar resúmenes usando modelos BART de Hugging Face.
Soporta tanto BART (inglés) como mBART (multilingüe, mejor para español).
"""
import logging
from typing import Optional
from transformers import (
    BartForConditionalGeneration, 
    BartTokenizer,
    MBartForConditionalGeneration,
    MBart50TokenizerFast
)
import torch

logger = logging.getLogger(__name__)


class BARTSummarizer:
    """
    Generador de resúmenes usando BART o mBART.
    
    BART (Bidirectional and Auto-Regressive Transformers) es un modelo de Facebook AI
    que combina las ventajas de BERT y GPT para tareas de generación de texto.
    
    Modelos soportados:
    - facebook/bart-large-cnn: Optimizado para inglés (~1.6GB)
    - facebook/mbart-large-50: Multilingüe, mejor para español (~2.2GB)
    """
    
    def __init__(self, model_name: str = "facebook/mbart-large-50"):
        """
        Inicializa el modelo BART.
        
        Args:
            model_name: Nombre del modelo en Hugging Face Hub
                       Por defecto usa 'facebook/mbart-large-50' (multilingüe, mejor para español)
                       Optimizado para velocidad con greedy decoding
        """
        self.model_name = model_name
        self.is_mbart = "mbart" in model_name.lower()
        self.model = None
        self.tokenizer = None
        self.device = self._select_best_device()
        self.gpu_memory_gb = self._get_gpu_memory()
        self._load_model()
    
    def _select_best_device(self):
        """Selecciona el mejor dispositivo disponible."""
        # Para GPUs pequeñas (<4GB), es mejor usar CPU directamente
        # mBART-50 requiere ~3GB+ VRAM, dejando poco espacio para procesamiento
        if torch.cuda.is_available():
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            if gpu_memory < 4.5:
                logger.info(f"GPU detected ({gpu_memory:.1f}GB) but using CPU for stability with mBART-50")
                return "cpu"
            return "cuda"
        else:
            return "cpu"
    
    def _get_gpu_memory(self):
        """Obtiene la memoria total de la GPU en GB."""
        if self.device == "cuda":
            try:
                return torch.cuda.get_device_properties(0).total_memory / (1024**3)
            except:
                return 0
        return 0
    
    def _get_optimal_generation_params(self, desired_quality: str = "high"):
        """
        Determina parámetros óptimos según la memoria disponible.
        
        Args:
            desired_quality: "high", "medium", "low"
            
        Returns:
            dict con parámetros optimizados
        """
        # Configuraciones según memoria disponible
        if self.device == "cpu":
            # CPU: configuración conservadora
            return {
                "num_beams": 4,
                "batch_size": 1
            }
        elif self.gpu_memory_gb < 4:
            # GPU pequeña (< 4GB): configuración ligera
            logger.warning(f"Low GPU memory ({self.gpu_memory_gb:.1f}GB), using conservative settings")
            return {
                "num_beams": 4,  # Reducido de 8
                "batch_size": 1
            }
        elif self.gpu_memory_gb < 8:
            # GPU media (4-8GB): configuración balanceada
            return {
                "num_beams": 6,
                "batch_size": 1
            }
        else:
            # GPU grande (>8GB): máxima calidad
            return {
                "num_beams": 8,
                "batch_size": 1
            }
    
    def _load_model(self):
        """Carga el modelo y tokenizer de BART o mBART."""
        try:
            logger.info(f"Loading model: {self.model_name}")
            logger.info(f"Using device: {self.device}")
            if self.device == "cuda":
                logger.info(f"GPU memory: {self.gpu_memory_gb:.2f} GB")
            
            if self.is_mbart:
                logger.info("Loading mBART (multilingual) - better for Spanish")
                self.tokenizer = MBart50TokenizerFast.from_pretrained(
                    self.model_name,
                    src_lang="es_XX",  # Español como idioma fuente
                    tgt_lang="es_XX"   # Español como idioma objetivo
                )
                self.model = MBartForConditionalGeneration.from_pretrained(self.model_name)
            else:
                logger.info("Loading BART (English-focused)")
                self.tokenizer = BartTokenizer.from_pretrained(self.model_name)
                self.model = BartForConditionalGeneration.from_pretrained(self.model_name)
            
            self.model = self.model.to(self.device)
            self.model.eval()  # Modo evaluación (no entrenamiento)
            
            # Optimizaciones para velocidad
            if self.device == "cpu":
                # Optimización para CPU
                try:
                    import torch
                    torch.set_num_threads(4)  # Limitar threads para evitar overhead
                except:
                    pass
            
            # Limpiar cache de GPU si es necesario
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            raise
    
    def generate_summary(
        self, 
        text: str, 
        max_length: int = 500,
        min_length: int = 150,
        num_beams: int = 4,
        length_penalty: float = 2.0,
        early_stopping: bool = True
    ) -> str:
        """
        Genera un resumen del texto usando BART.
        
        Args:
            text: Texto a resumir
            max_length: Longitud máxima del resumen en tokens
            min_length: Longitud mínima del resumen en tokens
            num_beams: Número de beams para beam search (mayor = más calidad, más lento)
            length_penalty: Penalización por longitud (>1 favorece resúmenes más largos)
            early_stopping: Si True, detiene cuando todos los beams terminan
            
        Returns:
            Texto del resumen generado
        """
        try:
            if not text or len(text.strip()) < 100:
                logger.warning("Text too short for summarization")
                return "El texto es demasiado corto para generar un resumen significativo."
            
            # Balance óptimo para mBART: suficiente contexto sin ser lento
            max_chars = 5500  # ~1375 tokens (buen balance)
            if len(text) > max_chars:
                logger.debug(f"Truncating text from {len(text)} to {max_chars} chars")
                # Tomar 70% del inicio + 30% final para mejor contexto
                first_part = text[:int(max_chars * 0.70)]
                last_part = text[-int(max_chars * 0.30):]
                text = first_part + "\n...\n" + last_part
            
            # Tokenizar
            inputs = self.tokenizer(
                text,
                max_length=1024,
                return_tensors="pt",
                truncation=True
            )
            inputs = inputs.to(self.device)
            
            # Generar resumen
            logger.debug(f"Generating summary with max_length={max_length}, num_beams={num_beams}")
            
            # Limpiar cache antes de generar
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            with torch.no_grad():
                if self.is_mbart:
                    # mBART requiere forced_bos_token_id para especificar idioma de salida
                    summary_ids = self.model.generate(
                        inputs["input_ids"],
                        max_length=max_length,
                        min_length=min_length,
                        num_beams=num_beams,
                        length_penalty=length_penalty,
                        early_stopping=early_stopping,
                        no_repeat_ngram_size=3,
                        forced_bos_token_id=self.tokenizer.lang_code_to_id["es_XX"]  # Forzar español
                    )
                else:
                    # BART normal
                    summary_ids = self.model.generate(
                        inputs["input_ids"],
                        max_length=max_length,
                        min_length=min_length,
                        num_beams=num_beams,
                        length_penalty=length_penalty,
                        early_stopping=early_stopping,
                        no_repeat_ngram_size=3
                    )
            
            # Limpiar cache después de generar
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            # Decodificar
            summary = self.tokenizer.decode(
                summary_ids[0],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )
            
            logger.info(f"Generated summary of {len(summary)} characters")
            
            return summary.strip()
            
        except torch.cuda.OutOfMemoryError as e:
            logger.error(f"CUDA out of memory: {e}")
            logger.warning("Retrying with CPU...")
            
            # Mover modelo a CPU y reintentar
            try:
                self.model = self.model.to("cpu")
                self.device = "cpu"
                
                # Limpiar GPU
                torch.cuda.empty_cache()
                
                # Reintentar con CPU y parámetros más conservadores
                inputs = self.tokenizer(
                    text,
                    max_length=1024,
                    return_tensors="pt",
                    truncation=True
                )
                # inputs ya están en CPU por defecto
                
                with torch.no_grad():
                    if self.is_mbart:
                        summary_ids = self.model.generate(
                            inputs["input_ids"],
                            max_length=max_length,
                            min_length=min_length,
                            num_beams=min(num_beams, 4),
                            length_penalty=length_penalty,
                            early_stopping=True,
                            no_repeat_ngram_size=3,
                            forced_bos_token_id=self.tokenizer.lang_code_to_id["es_XX"]
                        )
                    else:
                        summary_ids = self.model.generate(
                            inputs["input_ids"],
                            max_length=max_length,
                            min_length=min_length,
                            num_beams=min(num_beams, 4),
                            length_penalty=length_penalty,
                            early_stopping=True,
                            no_repeat_ngram_size=3
                        )
                
                summary = self.tokenizer.decode(
                    summary_ids[0],
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True
                )
                
                logger.info(f"Successfully generated summary with CPU fallback")
                return summary.strip()
                
            except Exception as cpu_error:
                logger.error(f"CPU fallback also failed: {cpu_error}", exc_info=True)
                return f"Error al generar resumen (GPU y CPU): {str(cpu_error)}"
            
        except Exception as e:
            logger.error(f"Error generating BART summary: {e}", exc_info=True)
            return f"Error al generar resumen con BART: {str(e)}"
    
    def generate_dense_summary_for_embeddings(self, text: str) -> str:
        """
        Genera un resumen denso y detallado optimizado para embeddings.
        
        Configuración BALANCEADA para ESPAÑOL (velocidad + calidad):
        - mBART-50 multilingüe (español nativo)
        - num_beams=2 (balance perfecto: 2-3x más rápido que 4, mucho mejor que 1)
        - Longitud optimizada (512 tokens) para embeddings de calidad
        - ~30-40 segundos por documento en CPU
        """
        logger.info("Using num_beams=2 for balanced speed/quality with mBART-50")
        
        return self.generate_summary(
            text,
            max_length=1024,       # Balance: suficiente para embeddings densos
            min_length=200,       # Mínimo más alto para mejor calidad
            num_beams=8,          # BALANCE PERFECTO: rápido pero buena calidad
            length_penalty=2.5,   # Aumentado para resúmenes más completos
            early_stopping=False
        )
    
    def generate_abstractive_summary(self, text: str) -> str:
        """
        Genera un resumen abstractivo (más creativo, reformula ideas).
        
        Configuración optimizada para resúmenes abstractivos que capturan
        la esencia del documento con nuevas palabras.
        """
        return self.generate_summary(
            text,
            max_length=400,
            min_length=100,
            num_beams=6,  # Más beams para mejor calidad
            length_penalty=1.5,  # Menos penalización = más conciso
            early_stopping=True
        )
    
    def generate_extractive_summary(self, text: str) -> str:
        """
        Genera un resumen más extractivo (más fiel al texto original).
        
        Configuración que favorece mantener frases del documento original.
        """
        return self.generate_summary(
            text,
            max_length=600,
            min_length=200,
            num_beams=4,
            length_penalty=2.5,  # Mayor penalización = más largo y fiel
            early_stopping=True
        )
    
    def generate_bullet_points(self, text: str) -> str:
        """
        Genera un resumen corto tipo bullet points.
        
        Ideal para resúmenes ejecutivos rápidos.
        """
        return self.generate_summary(
            text,
            max_length=250,
            min_length=80,
            num_beams=4,
            length_penalty=1.0,
            early_stopping=True
        )
    
    def check_model_loaded(self) -> bool:
        """Verifica si el modelo está cargado correctamente."""
        return self.model is not None and self.tokenizer is not None
