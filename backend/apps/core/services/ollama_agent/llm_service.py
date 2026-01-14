import requests
import logging
from django.conf import settings
from typing import Optional

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
        # Modelo optimizado para velocidad - llama3.2:1b es más rápido
        self.ollama_model = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:1b')

    def check_connection(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=1000)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def generate_response(self, prompt: str, timeout: int = 1200, task_type: str = "general") -> str:
        """Generate response using Ollama
        
        Args:
            prompt: The prompt to send to the model
            timeout: Request timeout in seconds
            task_type: Type of task for optimized parameters:
                - "title_generation": Generate specific, detailed document titles
                - "metadata_extraction": Extract specific metadata (type, area, subject, etc.)
                - "summary_generation": Generate detailed summaries with specific facts
                - "chunk_summary": Summarize individual chunks (fast, concise) - NEW
                - "final_summary": Combine chunk summaries into final structured summary - NEW
                - "person_extraction": Extract person names and roles
                - "classification": Simple classification tasks
                - "extraction": General structured data extraction
                - "chat": Conversational Q&A about documents (short, direct answers)
                - "general": Creative/general responses
        """
        try:
            # Truncate prompt if too long - ajustado para modelos pequeños
            max_prompt_length = 15000  # Reducido para 1b model
            if len(prompt) > max_prompt_length:
                prompt = prompt[:max_prompt_length] + "\n\n[Prompt truncado por longitud]"
            
            # Adjust parameters based on specific task type
            if task_type == "title_generation":
                # Optimized for SPEED - generate titles quickly (up to 30 words)
                options = {
                    "temperature": 0.2,  # Más bajo para consistencia en modelos pequeños
                    "top_k": 10,
                    "top_p": 0.6,
                    "num_predict": 100,  # Reducido para 1b
                    "num_ctx": 2048,
                    "num_thread": 8,
                    "repeat_penalty": 1.1,  # Evitar repeticiones
                }
                max_length = 300
                logger.debug("Using title_generation configuration (1b optimized)")
                
            elif task_type == "metadata_extraction":
                # Optimized for extracting specific metadata fields
                options = {
                    "temperature": 0.1,  # Muy bajo para extracción precisa
                    "top_k": 10,
                    "top_p": 0.5,
                    "num_predict": 400,  # Reducido
                    "num_ctx": 3072,
                    "num_thread": 8,
                    "repeat_penalty": 1.1,
                }
                max_length = 4000
                logger.debug("Using metadata_extraction configuration (1b optimized)")
                
            elif task_type == "chunk_summary":
                # NEW: Optimized for summarizing individual chunks
                # Fast, concise, focused on extracting key facts
                options = {
                    "temperature": 0.15,  # Bajo para consistencia
                    "top_k": 10,
                    "top_p": 0.5,
                    "num_predict": 350,  # Respuestas cortas
                    "num_ctx": 3072,  # Suficiente para chunk + prompt
                    "num_thread": 8,
                    "repeat_penalty": 1.15,  # Evitar repeticiones
                }
                max_length = 800  # Resúmenes cortos de chunks
                logger.debug("Using chunk_summary configuration (1b optimized)")
                
            elif task_type == "final_summary":
                # NEW: Optimized for combining summaries into final structured output
                # More creative but still structured
                options = {
                    "temperature": 0.15,  # Un poco más creativo para integrar
                    "top_k": 15,
                    "top_p": 0.65,
                    "num_predict": 700,  # Aumentado para resumen completo con todas las secciones
                    "num_ctx": 8192,  # Contexto para todos los chunks resumidos
                    "num_thread": 8,
                    "repeat_penalty": 1.1,
                }
                max_length = 3000  # Resumen final estructurado completo
                logger.debug("Using final_summary configuration (1b optimized)")
                
            elif task_type == "summary_generation":
                # Fallback for direct summary (documents < 4000 chars)
                options = {
                    "temperature": 0.2,
                    "top_k": 12,
                    "top_p": 0.6,
                    "num_predict": 700,
                    "num_ctx": 4096,
                    "num_thread": 8,
                    "repeat_penalty": 1.1,
                }
                max_length = 2500
                logger.debug("Using summary_generation configuration (1b optimized)")
                
            elif task_type == "person_extraction":
                # Optimized for extracting person names and roles
                options = {
                    "temperature": 0.1,  # Muy bajo - nombres exactos
                    "top_k": 8,
                    "top_p": 0.4,
                    "num_predict": 600,
                    "num_ctx": 4096,
                    "num_thread": 8,
                    "repeat_penalty": 1.2,
                }
                max_length = 2000
                logger.debug("Using person_extraction configuration (1b optimized)")
                
            elif task_type == "classification":
                # Simple classification
                options = {
                    "temperature": 0.05,
                    "top_k": 5,
                    "top_p": 0.3,
                    "num_predict": 50,
                    "num_ctx": 2048,
                    "num_thread": 8,
                }
                max_length = 500
                logger.debug("Using classification configuration (1b optimized)")
                
            elif task_type == "extraction":
                # General extraction
                options = {
                    "temperature": 0.2,
                    "top_k": 15,
                    "top_p": 0.6,
                    "num_predict": 800,
                    "num_ctx": 4096,
                    "num_thread": 8,
                    "repeat_penalty": 1.1,
                }
                max_length = 3000
                logger.debug("Using extraction configuration (1b optimized)")
                
            elif task_type == "chat":
                # Conversational Q&A - Optimizado para velocidad y precisión
                options = {
                    "temperature": 0.01,  # Más determinístico para respuestas precisas
                    "top_k": 20,
                    "top_p": 0.3, # 0.7
                    "num_predict": 500,  # Respuestas concisas
                    "num_ctx": 8192,     # 8192 Contexto suficiente para ~12k chars
                    "num_thread": 8,
                    "repeat_penalty": 1.3,
                }
                max_length = 1500
                logger.debug("Using chat configuration (optimized for speed)")
                
            else:  # general
                options = {
                    "temperature": 0.3,
                    "top_k": 20,
                    "top_p": 0.7,
                    "num_predict": 500,
                    "num_ctx": 3072,
                    "num_thread": 8,
                }
                max_length = 2000
                logger.debug("Using general configuration (1b optimized)")
            
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": options
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                raw_response = data.get('response', '')
                logger.info(f"🤖 Ollama response length: {len(raw_response)} chars (task: {task_type})")
                logger.debug(f"🤖 Raw response preview: {raw_response[:200]}...")
                return self._clean_response(raw_response, max_length)
            else:
                logger.warning(f"Ollama responded with status {response.status_code}")
                return self._generate_fallback_response(prompt)
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout connecting to Ollama after {timeout} seconds")
            return self._generate_fallback_response(prompt)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Ollama: {e}")
            return self._generate_fallback_response(prompt)

    def _clean_response(self, text: str, max_length: int = 2000) -> str:
        """Clean response text"""
        if not text or text.strip() == '':
            logger.warning("⚠️ Empty response from Ollama")
            return "Respuesta no disponible"
        
        # Remove null bytes and clean formatting
        text = text.replace('\x00', '')
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        
        # Truncate if too long
        if len(text) > max_length:
            logger.info(f"Truncating response from {len(text)} to {max_length} chars")
            text = text[:max_length] + "..."
        
        cleaned = text.strip()
        logger.info(f"✅ Cleaned response: {len(cleaned)} chars")
        return cleaned

    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate fallback response when Ollama is not available"""
        if "ANÁLISIS COMPLETO" in prompt:
            return """**ANÁLISIS DEL DOCUMENTO LEGAL**

**Tipo de documento:** Documento Legal

**Resumen ejecutivo:** Este documento contiene información legal importante que requiere análisis detallado.

**Puntos clave:**
1. Información legal relevante identificada
2. Partes involucradas en el procedimiento
3. Aspectos jurídicos principales

*Nota: Respuesta generada en modo offline. Para análisis completo, verifique que Ollama esté funcionando.*"""
        
        return """Respuesta simulada del asistente legal:

Basándome en la información proporcionada, puedo identificar elementos relevantes del caso. Sin embargo, para obtener análisis detallados, es necesario que el servicio de IA esté disponible.

**Recomendaciones:**
1. Verifique la conectividad con el servicio de IA
2. Revise la configuración del sistema
3. Intente nuevamente en unos momentos

*Esta es una respuesta de demostración.*"""
