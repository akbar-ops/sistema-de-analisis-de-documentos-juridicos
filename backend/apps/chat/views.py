from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.documents.models import Document
from apps.core.services.ollama_agent.llm_service import LLMService
from apps.documents.services.rag_service_v4 import get_rag_service
import logging

logger = logging.getLogger(__name__)

class DocumentChatView(APIView):
    """
    API endpoint for chatting about a specific document using Ollama.
    
    Provides intelligent context-aware responses by combining:
    - Document summary (concise overview)
    - Document metadata (type, area, dates, parties)
    - Chat history (conversation context)
    - User's current question
    
    This creates a focused, efficient prompt that helps Ollama understand
    the legal document context without overwhelming it with the full text.
    """
    
    def post(self, request):
        """
        Handle chat message about a document.
        
        Expected payload:
        {
            "document_id": "uuid-here",
            "message": "¿Quiénes son las partes involucradas?",
            "history": [
                {"from": "user", "text": "previous question"},
                {"from": "assistant", "text": "previous answer"}
            ]
        }
        
        Returns:
        {
            "response": "Assistant's response",
            "context_used": {
                "summary": true,
                "metadata": true,
                "history_length": 2
            }
        }
        """
        try:
            # Extract request data
            document_id = request.data.get('document_id')
            user_message = request.data.get('message', '').strip()
            chat_history = request.data.get('history', [])
            chat_mode = request.data.get('mode', 'rag')  # 'rag' o 'normal'
            
            # Validate inputs
            if not document_id:
                return Response(
                    {'error': 'document_id es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not user_message:
                return Response(
                    {'error': 'message es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get document
            try:
                document = Document.objects.get(document_id=document_id)
                logger.info(f"📄 Document found: {document_id}")
                logger.info(f"   - Has content: {bool(document.content)}")
                logger.info(f"   - Content length: {len(document.content) if document.content else 0}")
                logger.info(f"   - Has summary: {bool(document.summary)}")
                logger.info(f"   - Chat mode: {chat_mode.upper()}")
            except Document.DoesNotExist:
                logger.error(f"❌ Document not found: {document_id}")
                return Response(
                    {'error': f'Documento {document_id} no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Build intelligent context
            context_parts = []
            context_used = {
                'mode': chat_mode,
                'rag_chunks': False,
                'rag_chunks_count': 0,
                'full_text': False,
                'summary': False,
                'metadata': False,
                'history_length': 0
            }
            
            logger.info(f"{'='*60}")
            logger.info(f"🚀 INICIANDO CHAT - MODO: {chat_mode.upper()}")
            logger.info(f"{'='*60}")
            logger.info(f"📝 Pregunta del usuario: '{user_message}'")
            
            # Seleccionar modo de contexto
            if chat_mode == 'rag':
                # RAG v4.0: Menos chunks, más contexto por cada uno
                rag_service = get_rag_service(
                    top_k_anchors=3,          # Solo 3 chunks principales
                    context_window_size=2,     # ±2 chunks de contexto cada uno
                    similarity_threshold=0.40, # Threshold más estricto
                )
                chunk_stats = rag_service.check_document_has_chunks(document)
                
                if chunk_stats['has_rag_capability']:
                    # Usar nuevo método que retorna ventanas de contexto
                    rag_result = rag_service.retrieve_with_context(
                        document=document,
                        question=user_message,
                        top_k=3,
                        context_size=2,
                    )
                    
                    if rag_result.windows:
                        # Generar contexto para LLM
                        chunk_context = rag_result.get_context_for_llm(max_chars=10000)
                        context_parts.append(f"FRAGMENTOS RELEVANTES DEL DOCUMENTO:\n{chunk_context}")
                        
                        context_used['rag_chunks'] = True
                        context_used['rag_version'] = 'v4.0'
                        context_used['context_windows'] = len(rag_result.windows)
                        context_used['main_chunks'] = rag_result.main_chunks_count
                        context_used['context_chunks'] = rag_result.context_chunks_count
                        context_used['total_chunks_used'] = rag_result.total_chunks_used
                        context_used['processing_time_ms'] = round(rag_result.processing_time_ms)
                        
                        # Calcular relevancia promedio
                        if rag_result.windows:
                            avg_score = sum(w.anchor.combined_score for w in rag_result.windows) / len(rag_result.windows)
                            context_used['avg_relevance'] = round(avg_score, 3)
                        
                        # ═══════════════════════════════════════════════════════════
                        # LOGGING DETALLADO PARA EXPOSICIÓN
                        # ═══════════════════════════════════════════════════════════
                        logger.info("=" * 70)
                        logger.info("📊 RAG v4.0 - RESULTADOS DE BÚSQUEDA SEMÁNTICA")
                        logger.info("=" * 70)
                        logger.info(f"🔍 Pregunta: '{user_message}'")
                        logger.info(f"📄 Documento: {document.title[:50]}...")
                        logger.info(f"⏱️  Tiempo de búsqueda: {rag_result.processing_time_ms:.0f}ms")
                        logger.info("-" * 70)
                        
                        for i, window in enumerate(rag_result.windows, 1):
                            anchor = window.anchor
                            relevance_pct = anchor.combined_score * 100
                            semantic_pct = anchor.semantic_score * 100
                            bm25_pct = anchor.bm25_score * 100
                            
                            # Determinar nivel de relevancia
                            if relevance_pct >= 70:
                                rel_emoji = "🟢"
                                rel_label = "MUY ALTA"
                            elif relevance_pct >= 50:
                                rel_emoji = "🟡"
                                rel_label = "ALTA"
                            elif relevance_pct >= 35:
                                rel_emoji = "🟠"
                                rel_label = "MEDIA"
                            else:
                                rel_emoji = "🔴"
                                rel_label = "BAJA"
                            
                            logger.info(f"")
                            logger.info(f"📦 VENTANA {i} de {len(rag_result.windows)}")
                            logger.info(f"   ├─ Chunks: #{window.start_order} al #{window.end_order} ({len(window.all_chunks)} chunks)")
                            logger.info(f"   ├─ {rel_emoji} Relevancia: {rel_label} ({relevance_pct:.1f}%)")
                            logger.info(f"   ├─ 🧠 Similitud semántica: {semantic_pct:.1f}%")
                            logger.info(f"   ├─ 📝 Coincidencia BM25: {bm25_pct:.1f}%")
                            logger.info(f"   ├─ 🎯 Chunk principal (ancla): #{anchor.order_number}")
                            
                            # Mostrar chunks de contexto
                            if window.before:
                                before_nums = [str(c.order_number) for c in window.before]
                                logger.info(f"   ├─ ⬆️  Contexto anterior: chunks #{', #'.join(before_nums)}")
                            if window.after:
                                after_nums = [str(c.order_number) for c in window.after]
                                logger.info(f"   ├─ ⬇️  Contexto posterior: chunks #{', #'.join(after_nums)}")
                            
                            # Preview del contenido del anchor
                            preview = anchor.content[:150].replace('\n', ' ').strip()
                            logger.info(f"   └─ 📄 Preview: \"{preview}...\"")
                        
                        logger.info("-" * 70)
                        logger.info(f"📈 RESUMEN:")
                        logger.info(f"   • Ventanas de contexto: {len(rag_result.windows)}")
                        logger.info(f"   • Chunks principales: {rag_result.main_chunks_count}")
                        logger.info(f"   • Chunks de contexto: {rag_result.context_chunks_count}")
                        logger.info(f"   • Total chunks enviados al LLM: {rag_result.total_chunks_used}")
                        logger.info(f"   • Relevancia promedio: {avg_score:.1%}")
                        logger.info("=" * 70)
                    else:
                        # No se encontraron chunks - dar información de debug
                        logger.warning("=" * 70)
                        logger.warning("⚠️  RAG: NO SE ENCONTRARON CHUNKS RELEVANTES")
                        logger.warning("=" * 70)
                        logger.warning(f"🔍 Pregunta: '{user_message}'")
                        logger.warning(f"📊 Chunks disponibles en documento: {rag_result.total_chunks_searched}")
                        logger.warning(f"📏 Embedding dimension: {rag_result.embedding_dimension}d")
                        logger.warning(f"⚙️  Threshold configurado: {rag_service.similarity_threshold:.0%}")
                        logger.warning(f"")
                        logger.warning(f"💡 POSIBLES CAUSAS:")
                        logger.warning(f"   1. Threshold muy alto (>{rag_service.similarity_threshold:.0%})")
                        logger.warning(f"   2. La pregunta no tiene relación semántica con el documento")
                        logger.warning(f"   3. Los embeddings del documento necesitan regenerarse")
                        logger.warning(f"")
                        logger.warning(f"🔧 SOLUCIÓN: Bajando threshold a 0.30 y reintentando...")
                        
                        # Reintentar con threshold más bajo
                        rag_service_relaxed = get_rag_service(
                            top_k_anchors=3,
                            context_window_size=2,
                            similarity_threshold=0.30,  # Threshold más permisivo
                        )
                        rag_result_retry = rag_service_relaxed.retrieve_with_context(
                            document=document,
                            question=user_message,
                            top_k=3,
                            context_size=2,
                        )
                        
                        if rag_result_retry.windows:
                            logger.warning(f"✅ Reintento exitoso con threshold 0.30")
                            logger.warning(f"   • Chunks encontrados: {rag_result_retry.total_chunks_used}")
                            
                            # Usar el resultado del reintento
                            chunk_context = rag_result_retry.get_context_for_llm(max_chars=10000)
                            context_parts.append(f"FRAGMENTOS RELEVANTES DEL DOCUMENTO:\n{chunk_context}")
                            
                            context_used['rag_chunks'] = True
                            context_used['rag_version'] = 'v4.0'
                            context_used['context_windows'] = len(rag_result_retry.windows)
                            context_used['main_chunks'] = rag_result_retry.main_chunks_count
                            context_used['context_chunks'] = rag_result_retry.context_chunks_count
                            context_used['total_chunks_used'] = rag_result_retry.total_chunks_used
                            context_used['processing_time_ms'] = round(rag_result_retry.processing_time_ms)
                            context_used['threshold_used'] = 0.30
                            
                            if rag_result_retry.windows:
                                avg_score = sum(w.anchor.combined_score for w in rag_result_retry.windows) / len(rag_result_retry.windows)
                                context_used['avg_relevance'] = round(avg_score, 3)
                            logger.warning("=" * 70)
                        else:
                            logger.warning(f"❌ Reintento fallido incluso con threshold 0.30")
                            logger.warning(f"   • Usando fallback (primeros 6000 caracteres)")
                            logger.warning("=" * 70)
                            self._add_fallback_context(document, context_parts, context_used)
                else:
                    logger.info(f"📄 Documento sin chunks RAG, usando fallback")
                    self._add_fallback_context(document, context_parts, context_used)
            else:
                # MODO NORMAL: Usar primeros 6000 caracteres del documento
                logger.info(f"📄 MODO NORMAL - Usando primeros 6000 caracteres")
                self._add_fallback_context(document, context_parts, context_used)
            
            # 2. Document Metadata (provides structured context)
            metadata_parts = []
            
            if document.title:
                metadata_parts.append(f"Título: {document.title}")
            
            if document.doc_type:
                metadata_parts.append(f"Tipo de documento: {document.doc_type.name}")
            
            if document.legal_area:
                metadata_parts.append(f"Área legal: {document.legal_area.name}")
            
            if document.legal_subject:
                metadata_parts.append(f"Materia: {document.legal_subject}")
            
            if document.document_date:
                metadata_parts.append(f"Fecha del documento: {document.document_date}")
            
            if document.issue_place:
                metadata_parts.append(f"Lugar de emisión: {document.issue_place}")
            
            if document.jurisdictional_body:
                metadata_parts.append(f"Órgano jurisdiccional: {document.jurisdictional_body}")
            
            if document.case_number:
                metadata_parts.append(f"Número de expediente: {document.case_number}")
            
            if document.resolution_number:
                metadata_parts.append(f"Número de resolución: {document.resolution_number}")
            
            # Add persons (parties involved) - Mejorado para mejor contexto
            document_persons = document.document_persons.select_related('person').all()[:15]
            if document_persons:
                persons_by_role = {}
                for dp in document_persons:
                    role = dp.get_role_display() if hasattr(dp, 'get_role_display') else dp.role
                    if role not in persons_by_role:
                        persons_by_role[role] = []
                    persons_by_role[role].append(dp.person.name)
                
                persons_text = []
                for role, names in persons_by_role.items():
                    if len(names) == 1:
                        persons_text.append(f"{role}: {names[0]}")
                    else:
                        persons_text.append(f"{role}s: {', '.join(names)}")
                
                if persons_text:
                    metadata_parts.append("Partes involucradas:\n  - " + "\n  - ".join(persons_text))
            
            if metadata_parts:
                context_parts.append("METADATOS DEL DOCUMENTO:\n" + "\n".join(metadata_parts))
                context_used['metadata'] = True
                logger.info(f"📋 Using metadata ({len(metadata_parts)} fields)")
            
            # 3. Recent Chat History (last 6 messages for context continuity)
            if chat_history:
                # Take last 6 messages (3 exchanges)
                recent_history = chat_history[-6:]
                context_used['history_length'] = len(recent_history)
                
                history_text = "CONVERSACIÓN ANTERIOR:\n"
                for msg in recent_history:
                    role = "Usuario" if msg.get('from') == 'user' else "Asistente"
                    history_text += f"{role}: {msg.get('text', '')}\n"
                
                context_parts.append(history_text)
                logger.info(f"💬 Using chat history ({len(recent_history)} messages)")
            
            # Build the complete prompt
            prompt = self._build_chat_prompt(
                context="\n\n".join(context_parts),
                user_question=user_message,
                document=document
            )
            
            logger.info(f"{'='*60}")
            logger.info(f"🤖 ENVIANDO A OLLAMA")
            logger.info(f"{'='*60}")
            logger.info(f"📏 Tamaño del prompt: {len(prompt)} caracteres")
            logger.info(f"📊 Contexto usado: {context_used}")
            
            # Generate response using Ollama
            llm_service = LLMService()
            
            # Check Ollama connection
            if not llm_service.check_connection():
                return Response(
                    {
                        'error': 'Ollama no está disponible. Por favor verifica que el servicio esté ejecutándose.',
                        'response': 'Lo siento, el servicio de IA no está disponible en este momento. Por favor intenta más tarde.'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Generate response (using chat task type for short, direct answers)
            ai_response = llm_service.generate_response(
                prompt=prompt,
                task_type="chat",  # Optimized for conversational Q&A
                timeout=120  # 2 minutes timeout for full text processing
            )
            
            logger.info(f"{'='*60}")
            logger.info(f"✅ RESPUESTA RECIBIDA")
            logger.info(f"{'='*60}")
            logger.info(f"📏 Tamaño respuesta: {len(ai_response)} caracteres")
            logger.info(f"📄 Preview respuesta: {ai_response[:150]}...")
            
            return Response({
                'response': ai_response,
                'context_used': context_used,
                'document_id': str(document_id)
            })
            
        except Exception as e:
            logger.error(f"❌ Error in DocumentChatView: {str(e)}", exc_info=True)
            
            # Proporcionar mensaje de error más específico
            error_message = str(e)
            if "Connection" in error_message or "connect" in error_message.lower():
                user_message = "No se pudo conectar con el servicio de IA. Verifica que Ollama esté corriendo."
            elif "timeout" in error_message.lower():
                user_message = "La solicitud tardó demasiado. Intenta con una pregunta más específica."
            elif "model" in error_message.lower():
                user_message = "El modelo de IA no está disponible. Verifica la configuración de Ollama."
            else:
                user_message = f"Error al procesar la pregunta: {error_message}"
            
            return Response(
                {
                    'error': 'Error procesando la solicitud',
                    'detail': str(e),
                    'response': user_message
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _build_chat_prompt(self, context: str, user_question: str, document) -> str:
        """
        Construye un prompt genérico para responder preguntas sobre documentos legales.
        
        Versión 4.0 SIMPLIFICADA:
        ========================
        NO detectamos tipos de pregunta. El RAG ya encontró los fragmentos
        más relevantes usando similitud semántica. El LLM solo necesita
        leer esos fragmentos y responder la pregunta.
        
        La similitud semántica es AGNÓSTICA al tipo de pregunta:
        - Si preguntan por "antecedentes", el RAG encontró chunks sobre antecedentes
        - Si preguntan por "fallo", el RAG encontró chunks sobre la decisión
        - El embedding del modelo entiende sinónimos y conceptos relacionados
        
        Args:
            context: Fragmentos relevantes del documento (ya filtrados por RAG)
            user_question: Pregunta del usuario
            document: Documento fuente
            
        Returns:
            Prompt formateado para el LLM
        """
        prompt = f"""Eres un asistente legal experto especializado en analizar documentos judiciales peruanos.

CONTEXTO: A continuación se presentan los fragmentos MÁS RELEVANTES del documento "{document.title}", 
seleccionados automáticamente por su similitud semántica con la pregunta del usuario.

═══════════════════════════════════════════════════════════════════════════════
📄 FRAGMENTOS DEL DOCUMENTO:
═══════════════════════════════════════════════════════════════════════════════
{context}

═══════════════════════════════════════════════════════════════════════════════
❓ PREGUNTA DEL USUARIO: {user_question}
═══════════════════════════════════════════════════════════════════════════════

INSTRUCCIONES:
1. Responde ÚNICAMENTE con información que aparezca en los fragmentos anteriores
2. Si la información solicitada no está en los fragmentos, indícalo claramente
3. Sé específico y cita la información exacta del documento
4. Usa un lenguaje claro y profesional

📝 RESPUESTA:"""
        
        return prompt
    
    def _add_fallback_context(self, document, context_parts: list, context_used: dict) -> None:
        """
        Agrega contexto usando el método legacy (primeros N caracteres del documento).
        Se usa cuando el documento no tiene chunks con embeddings.
        
        Args:
            document: Documento a procesar
            context_parts: Lista donde agregar el contexto
            context_used: Diccionario para trackear qué contexto se usó
        """
        if document.content:
            # Para modelos pequeños, menos es más
            # El encabezado del documento tiene: juez, partes, expediente, etc.
            max_context = 6000
            doc_text = document.content[:max_context]
            
            if len(document.content) > max_context:
                doc_text += f"\n\n[Documento tiene {len(document.content)} caracteres totales. Considera re-procesar el documento para habilitar búsqueda RAG inteligente]"
            
            context_parts.append(f"DOCUMENTO:\n{doc_text}")
            context_used['full_text'] = True
            logger.info(f"📄 Fallback: Using document text ({len(doc_text)} chars)")
        elif document.summary:
            # Fallback: usar resumen
            context_parts.append(f"RESUMEN DEL DOCUMENTO:\n{document.summary}")
            context_used['summary'] = True
            logger.info(f"📄 Fallback: Using summary ({len(document.summary)} chars)")

