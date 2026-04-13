import os
import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
from typing import List, Dict, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)

# Chunking configuration
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


class DocumentLoader:
    @staticmethod
    def load_pdf(file_path: str) -> List[Dict[str, Any]]:
        """Load PDF file and extract text chunks."""
        chunks = []

        try:
            doc = fitz.open(file_path)

            for page_num, page in enumerate(doc):
                text = page.get_text()

                if text.strip():
                    page_chunks = DocumentLoader._chunk_text(text, page_num)
                    chunks.extend(page_chunks)

            doc.close()

        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {e}")
            raise

        return chunks

    @staticmethod
    def load_text(file_path: str) -> List[Dict[str, Any]]:
        """Load text file and extract chunks."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

            chunks = DocumentLoader._chunk_text(text, 0)
            return chunks

        except Exception as e:
            logger.error(f"Error loading text file {file_path}: {e}")
            raise

    @staticmethod
    def load_url(url: str) -> List[Dict[str, Any]]:
        """Load URL content and extract text chunks."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text(separator=' ', strip=True)

            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)

            chunks = DocumentLoader._chunk_text(text, 0)

            return chunks

        except Exception as e:
            logger.error(f"Error loading URL {url}: {e}")
            raise

    @staticmethod
    def load_image(file_path: str) -> List[Dict[str, Any]]:
        """Load image and extract text using OCR."""
        try:
            image = Image.open(file_path)

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            text = pytesseract.image_to_string(image)

            chunks = DocumentLoader._chunk_text(text, 0)

            return chunks

        except Exception as e:
            logger.error(f"Error loading image {file_path}: {e}")
            raise

    @staticmethod
    def _chunk_text(text: str, base_page: int = 0) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        chunks = []

        if len(text) <= CHUNK_SIZE:
            return [{
                "text": text,
                "page": base_page,
                "chunk_index": 0
            }]

        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + CHUNK_SIZE

            # Try to break at sentence or word boundary
            if end < len(text):
                # Look for sentence break
                sentence_break = text.rfind('. ', start, end)
                if sentence_break > start:
                    end = sentence_break + 1
                else:
                    # Look for word break
                    word_break = text.rfind(' ', start, end)
                    if word_break > start:
                        end = word_break

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "page": base_page,
                    "chunk_index": chunk_index
                })

            chunk_index += 1
            start = end - CHUNK_OVERLAP

        return chunks

    @staticmethod
    def load_document(file_path: str, source_url: Optional[str], file_type: str) -> List[Dict[str, Any]]:
        """Load a document based on type."""
        if source_url:
            return DocumentLoader.load_url(source_url)

        file_type = file_type.lower()

        if file_type == "pdf":
            return DocumentLoader.load_pdf(file_path)
        elif file_type in ["txt", "text"]:
            return DocumentLoader.load_text(file_path)
        elif file_type in ["png", "jpg", "jpeg", "image"]:
            return DocumentLoader.load_image(file_path)
        elif file_type == "link":
            if source_url:
                return DocumentLoader.load_url(source_url)
            else:
                raise ValueError("URL is required for link type")
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
