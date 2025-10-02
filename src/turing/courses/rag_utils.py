# courses/rag_utils.py
import os
import re
import json
from typing import List, Dict, Any, Tuple
from django.conf import settings
from openai import OpenAI
import PyPDF2
import numpy as np
from .models import KnowledgeBaseFile
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class RAGProcessor:
    """Handles PDF text extraction, chunking, and retrieval-augmented generation."""
    
    def __init__(self):
        self.chunk_size = 1000  # Maximum characters per chunk
        self.chunk_overlap = 200  # Characters to overlap between chunks
        self.max_chunks_for_context = 3  # Maximum chunks to include in context
        
    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text content from a PDF file."""
        if not PyPDF2:
            raise ImportError("PyPDF2 is required for PDF processing")
            
        try:
            # Read the file content directly from the Django file field
            pdf_file.seek(0)  # Make sure we're at the beginning of the file
            reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                text += page_text + "\n"
            
            return text.strip()
        except Exception as e:
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
            # Extract text from PDF
            extracted_text = self.extract_text_from_pdf(knowledge_file.file)
            
            cleaned_text = self.clean_text(extracted_text)
            
            # Create chunks
            chunks = self.chunk_text(cleaned_text)
            
            if not chunks:
                return {
                    'success': False,
                    'error': 'No text could be extracted from the PDF'
                }
            
            # Get embeddings
            embeddings = self.get_embeddings_openai(chunks)
            
            # Update the knowledge file
            knowledge_file.extracted_text = cleaned_text
            knowledge_file.text_chunks = chunks
            knowledge_file.embeddings = embeddings
            knowledge_file.processed = True
            knowledge_file.processing_error = ""
            knowledge_file.save()
            
            return {
                'success': True,
                'chunks_count': len(chunks),
                'text_length': len(cleaned_text)
            }
            
        except Exception as e:
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
        
        if limit is None:
            limit = self.max_chunks_for_context
            
        try:
            # Get all processed files for the course
            knowledge_files = KnowledgeBaseFile.objects.filter(
                course_id=course_id,
                processed=True,
                text_chunks__len__gt=0
            )
            
            if not knowledge_files.exists():
                return []
            
            # Get query embedding
            query_embedding = self.get_embeddings_openai([query])[0]
            
            relevant_chunks = []
            
            for kf in knowledge_files:
                chunks = kf.text_chunks
                embeddings = kf.embeddings
                
                if not chunks or not embeddings or len(chunks) != len(embeddings):
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
            
            return relevant_chunks[:limit]
            
        except Exception as e:
            return []
    
    def create_rag_context(self, query: str, course_id: int) -> str:
        """Create context from relevant knowledge base chunks."""
        relevant_chunks = self.find_relevant_chunks(query, course_id)
        
        if not relevant_chunks:
            return ""
        
        context_parts = []
        for i, (chunk, similarity) in enumerate(relevant_chunks, 1):
            context_parts.append(f"[Fuente {i}]: {chunk}")
        
        context = "\n\n".join(context_parts)
        
        final_context = f"""Información relevante de la base de conocimiento del curso:

{context}

---

Pregunta del estudiante: {query}

Por favor, responde la pregunta utilizando la información de la base de conocimiento cuando sea relevante. Si la información de la base de conocimiento no es suficiente para responder completamente, puedes complementar con conocimiento general, pero menciona claramente qué parte viene de los materiales del curso."""

        return final_context


# Global instance
rag_processor = RAGProcessor()