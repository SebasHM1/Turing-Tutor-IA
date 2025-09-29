# courses/rag_utils.py
import os
import re
import json
from typing import List, Dict, Any, Tuple
from django.conf import settings
from openai import OpenAI

try:
    import PyPDF2
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError as e:
    print(f"Warning: Missing dependencies for RAG functionality: {e}")
    PyPDF2 = None
    np = None
    cosine_similarity = None
    TfidfVectorizer = None


class RAGProcessor:
    """Handles PDF text extraction, chunking, and retrieval-augmented generation."""
    
    def __init__(self):
        self.chunk_size = 1000  # Maximum characters per chunk
        self.chunk_overlap = 200  # Characters to overlap between chunks
        self.max_chunks_for_context = 3  # Maximum chunks to include in context
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from a PDF file."""
        if not PyPDF2:
            print("DEBUG RAG: ERROR - PyPDF2 no está disponible")
            raise ImportError("PyPDF2 is required for PDF processing")
            
        try:
            print(f"DEBUG RAG: Intentando abrir PDF: {pdf_path}")
            print(f"DEBUG RAG: ¿Archivo existe? {os.path.exists(pdf_path)}")
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                print(f"DEBUG RAG: PDF abierto, número de páginas: {len(reader.pages)}")
                
                text = ""
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    text += page_text + "\n"
                    if i < 3:  # Solo mostrar las primeras 3 páginas para debug
                        print(f"DEBUG RAG: Página {i+1}, texto extraído: {len(page_text)} caracteres")
                        if page_text:
                            print(f"DEBUG RAG: Primeros 100 chars de página {i+1}: {page_text[:100]}")
                
                print(f"DEBUG RAG: Extracción completada, total: {len(text)} caracteres")
                return text.strip()
        except Exception as e:
            print(f"DEBUG RAG: Error en extract_text_from_pdf: {str(e)}")
            print(f"DEBUG RAG: Tipo de error: {type(e).__name__}")
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', ' ', text)
        return text.strip()
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks for better retrieval."""
        if not text:
            return []
            
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # Find the end of this chunk
            end = start + self.chunk_size
            
            # If we're not at the end of the text, try to break at a sentence
            if end < text_length:
                # Look for sentence endings within the last 200 characters
                look_back = min(200, self.chunk_size // 5)
                sentence_end = text.rfind('.', end - look_back, end)
                if sentence_end != -1:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            
            # Move to next chunk with overlap
            start = max(start + 1, end - self.chunk_overlap)
            
        return chunks
    
    def get_embeddings_openai(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings using OpenAI's embedding model."""
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            embeddings = []
            
            # Process texts in batches to avoid rate limits
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            return embeddings
        except Exception as e:
            print(f"Error getting OpenAI embeddings: {e}")
            # Fallback to TF-IDF if OpenAI fails
            return self.get_embeddings_tfidf(texts)
    
    def get_embeddings_tfidf(self, texts: List[str]) -> List[List[float]]:
        """Fallback embedding method using TF-IDF."""
        if not TfidfVectorizer:
            raise ImportError("scikit-learn is required for TF-IDF embeddings")
            
        vectorizer = TfidfVectorizer(max_features=384, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(texts)
        return tfidf_matrix.toarray().tolist()
    
    def process_pdf_file(self, knowledge_file) -> Dict[str, Any]:
        """Process a KnowledgeBaseFile: extract text, chunk it, and create embeddings."""
        try:
            print(f"DEBUG RAG: Iniciando procesamiento del archivo ID: {knowledge_file.id}")
            print(f"DEBUG RAG: Archivo: {knowledge_file.file.name}")
            
            # Extract text from PDF
            pdf_path = knowledge_file.file.path
            print(f"DEBUG RAG: Ruta del PDF: {pdf_path}")
            
            extracted_text = self.extract_text_from_pdf(pdf_path)
            print(f"DEBUG RAG: Texto extraído, longitud: {len(extracted_text)} caracteres")
            
            cleaned_text = self.clean_text(extracted_text)
            print(f"DEBUG RAG: Texto limpiado, longitud: {len(cleaned_text)} caracteres")
            
            # Create chunks
            chunks = self.chunk_text(cleaned_text)
            print(f"DEBUG RAG: Chunks creados: {len(chunks)}")
            
            if not chunks:
                print("DEBUG RAG: ERROR - No se pudieron crear chunks")
                return {
                    'success': False,
                    'error': 'No text could be extracted from the PDF'
                }
            
            # Get embeddings
            print("DEBUG RAG: Generando embeddings...")
            embeddings = self.get_embeddings_openai(chunks)
            print(f"DEBUG RAG: Embeddings generados: {len(embeddings)}")
            
            # Update the knowledge file
            knowledge_file.extracted_text = cleaned_text
            knowledge_file.text_chunks = chunks
            knowledge_file.embeddings = embeddings
            knowledge_file.processed = True
            knowledge_file.processing_error = ""
            knowledge_file.save()
            
            print(f"DEBUG RAG: Archivo procesado exitosamente - {len(chunks)} chunks, {len(embeddings)} embeddings")
            
            return {
                'success': True,
                'chunks_count': len(chunks),
                'text_length': len(cleaned_text)
            }
            
        except Exception as e:
            print(f"DEBUG RAG: ERROR en procesamiento: {str(e)}")
            print(f"DEBUG RAG: Tipo de error: {type(e).__name__}")
            import traceback
            print(f"DEBUG RAG: Traceback completo: {traceback.format_exc()}")
            
            # Save error information
            knowledge_file.processing_error = str(e)
            knowledge_file.processed = False
            knowledge_file.save()
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_relevant_chunks(self, query: str, course_id: int, limit: int = None) -> List[Tuple[str, float]]:
        """Find the most relevant text chunks for a given query."""
        from .models import KnowledgeBaseFile
        
        if limit is None:
            limit = self.max_chunks_for_context
            
        try:
            print(f"DEBUG RAG: Buscando chunks para curso {course_id} con query: '{query}'")
            
            # Get all processed files for the course
            knowledge_files = KnowledgeBaseFile.objects.filter(
                course_id=course_id,
                processed=True,
                text_chunks__len__gt=0
            )
            
            print(f"DEBUG RAG: Archivos procesados encontrados: {knowledge_files.count()}")
            
            if not knowledge_files.exists():
                print("DEBUG RAG: No hay archivos procesados para este curso")
                return []
            
            # Get query embedding
            print("DEBUG RAG: Generando embedding para la query...")
            query_embedding = self.get_embeddings_openai([query])[0]
            print(f"DEBUG RAG: Embedding generado, dimensiones: {len(query_embedding)}")
            
            relevant_chunks = []
            
            for kf in knowledge_files:
                chunks = kf.text_chunks
                embeddings = kf.embeddings
                
                print(f"DEBUG RAG: Procesando archivo '{kf.name}' con {len(chunks)} chunks")
                
                if not chunks or not embeddings or len(chunks) != len(embeddings):
                    print(f"DEBUG RAG: Saltando archivo '{kf.name}' - datos inconsistentes")
                    continue
                
                # Calculate similarities
                similarities = []
                for i, emb in enumerate(embeddings):
                    if np and cosine_similarity:
                        sim = cosine_similarity([query_embedding], [emb])[0][0]
                    else:
                        # Fallback: simple dot product similarity
                        sim = sum(a * b for a, b in zip(query_embedding, emb))
                    similarities.append(sim)
                
                # Add chunks with their similarities
                for chunk, similarity in zip(chunks, similarities):
                    relevant_chunks.append((chunk, similarity))
            
            # Sort by similarity and return top chunks
            relevant_chunks.sort(key=lambda x: x[1], reverse=True)
            print(f"DEBUG RAG: Total chunks encontrados: {len(relevant_chunks)}")
            if relevant_chunks:
                print(f"DEBUG RAG: Mejor similitud: {relevant_chunks[0][1]:.4f}")
                print(f"DEBUG RAG: Peor similitud en top {limit}: {relevant_chunks[min(limit-1, len(relevant_chunks)-1)][1]:.4f}")
            
            return relevant_chunks[:limit]
            
        except Exception as e:
            print(f"DEBUG RAG: Error finding relevant chunks: {e}")
            return []
    
    def create_rag_context(self, query: str, course_id: int) -> str:
        """Create context from relevant knowledge base chunks."""
        print(f"DEBUG RAG: create_rag_context llamado para curso {course_id}")
        relevant_chunks = self.find_relevant_chunks(query, course_id)
        
        if not relevant_chunks:
            print("DEBUG RAG: No se encontraron chunks relevantes")
            return ""
        
        context_parts = []
        for i, (chunk, similarity) in enumerate(relevant_chunks, 1):
            print(f"DEBUG RAG: Chunk {i} - Similitud: {similarity:.4f}, Longitud: {len(chunk)} chars")
            context_parts.append(f"[Fuente {i}]: {chunk}")
        
        context = "\n\n".join(context_parts)
        
        final_context = f"""Información relevante de la base de conocimiento del curso:

{context}

---

Pregunta del estudiante: {query}

Por favor, responde la pregunta utilizando la información de la base de conocimiento cuando sea relevante. Si la información de la base de conocimiento no es suficiente para responder completamente, puedes complementar con conocimiento general, pero menciona claramente qué parte viene de los materiales del curso."""

        print(f"DEBUG RAG: Contexto final generado, longitud total: {len(final_context)} caracteres")
        return final_context


# Global instance
rag_processor = RAGProcessor()