# txt_parser_complete.py
import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Data Models (Same as PDF/PPTX/DOCX)
class ImageChunk(BaseModel):
    path: str
    caption: Optional[str] = None
    bbox: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentChunk(BaseModel):
    doc_id: str
    unit: str
    index: int
    text_chunks: List[str]
    images: List[ImageChunk]
    embeddings: Optional[Dict[str, List[float]]] = None

class TXTParser:
    """
    Complete TXT parser that extracts text in same format as other parsers
    """
    
    def __init__(self):
        # TXT files don't have images, so no image directory needed
        pass

    def split_into_paragraphs(self, text: str, min_paragraph_length: int = 50) -> List[str]:
        """Split text into meaningful paragraphs"""
        paragraphs = []
        
        # Split by double newlines (common paragraph separator)
        raw_paragraphs = text.split('\n\n')
        
        for paragraph in raw_paragraphs:
            # Clean up the paragraph
            paragraph = paragraph.strip()
            paragraph = ' '.join(paragraph.split())  # Normalize whitespace
            
            # Skip empty or very short paragraphs
            if paragraph and len(paragraph) >= min_paragraph_length:
                paragraphs.append(paragraph)
        
        return paragraphs

    def split_into_fixed_chunks(self, text: str, chunk_size: int = 500) -> List[str]:
        """Split text into fixed-size chunks"""
        chunks = []
        
        # Clean and normalize text
        text = ' '.join(text.split())
        
        # Split into chunks
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())
        
        return chunks

    def detect_sections(self, text: str) -> List[str]:
        """Detect natural sections in text"""
        sections = []
        current_section = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check if this line might be a section header
            is_header = (
                len(line) < 100 and  # Short line
                not line.endswith('.') and  # Doesn't end with period
                len(line.split()) < 10 and  # Few words
                any(c.isupper() for c in line)  # Has uppercase letters
            )
            
            if is_header and current_section:
                # Save current section and start new one
                section_text = ' '.join(current_section).strip()
                if section_text:
                    sections.append(section_text)
                current_section = [line]
            else:
                if line:  # Add non-empty lines
                    current_section.append(line)
        
        # Add the last section
        if current_section:
            section_text = ' '.join(current_section).strip()
            if section_text:
                sections.append(section_text)
        
        return sections

    def parse_txt(self, file_path: str, doc_id: Optional[str] = None, 
                 chunk_strategy: str = "paragraphs") -> List[DocumentChunk]:
        """Parse TXT file and return document chunks"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"TXT file not found: {file_path}")
        
        if doc_id is None:
            doc_id = os.path.splitext(os.path.basename(file_path))[0]
        
        document_chunks = []
        
        try:
            # Read TXT file with proper encoding handling
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            logger.info(f"Parsing TXT: {file_path} ({len(text)} characters)")
            
            # Remove empty lines and normalize
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            clean_text = '\n'.join(lines)
            
            if not clean_text:
                logger.warning("TXT file is empty or contains no readable text")
                return []
            
            # Choose chunking strategy
            if chunk_strategy == "paragraphs":
                text_chunks = self.split_into_paragraphs(clean_text)
            elif chunk_strategy == "sections":
                text_chunks = self.detect_sections(clean_text)
            elif chunk_strategy == "fixed":
                text_chunks = self.split_into_fixed_chunks(clean_text)
            else:
                # Default: use paragraphs
                text_chunks = self.split_into_paragraphs(clean_text)
            
            # If no chunks were created with the chosen strategy, use fixed chunks as fallback
            if not text_chunks:
                text_chunks = self.split_into_fixed_chunks(clean_text, chunk_size=300)
            
            # Create chunks (TXT files have no images, so images list is always empty)
            if len(text_chunks) <= 5:
                # For small number of chunks, put all in one section
                chunk = DocumentChunk(
                    doc_id=doc_id,
                    unit="document",
                    index=0,
                    text_chunks=text_chunks,
                    images=[]  # No images in TXT files
                )
                document_chunks.append(chunk)
            else:
                # For larger documents, split into multiple sections
                chunks_per_section = max(3, len(text_chunks) // 5)  # Aim for 5 sections max
                
                for section_index, i in enumerate(range(0, len(text_chunks), chunks_per_section)):
                    section_chunks = text_chunks[i:i + chunks_per_section]
                    
                    chunk = DocumentChunk(
                        doc_id=doc_id,
                        unit="section",
                        index=section_index,
                        text_chunks=section_chunks,
                        images=[]  # No images in TXT files
                    )
                    document_chunks.append(chunk)
            
            logger.info(f"TXT parsing complete: {len(document_chunks)} sections, {len(text_chunks)} text chunks")
            
            return document_chunks
            
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    text = f.read()
                
                logger.info(f"Parsed with latin-1 encoding: {file_path}")
                
                # Continue with processing...
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                clean_text = '\n'.join(lines)
                
                text_chunks = self.split_into_paragraphs(clean_text)
                
                chunk = DocumentChunk(
                    doc_id=doc_id,
                    unit="document",
                    index=0,
                    text_chunks=text_chunks,
                    images=[]
                )
                document_chunks.append(chunk)
                
                return document_chunks
                
            except Exception as e:
                logger.error(f"Error parsing TXT with alternative encoding: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Error parsing TXT {file_path}: {e}")
            raise

    def save_txt_extraction(self, chunks: List[DocumentChunk], output_dir: str, txt_file: str):
        """Save TXT extraction results to JSON (same format as other parsers)"""
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(txt_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create data structure (same format as PDF/PPTX/DOCX)
        txt_data = {
            "metadata": {
                "source_file": txt_file,
                "file_type": "txt",
                "extraction_time": timestamp,
                "total_sections": len(chunks),
                "total_text_chunks": sum(len(chunk.text_chunks) for chunk in chunks),
                "total_images": 0  # TXT files never have images
            },
            "sections": []  # Same structure as other parsers
        }
        
        for chunk in chunks:
            section_data = {
                "section_number": chunk.index,
                "unit_type": chunk.unit,
                "text_chunks_count": len(chunk.text_chunks),
                "images_count": 0,  # Always 0 for TXT
                "text_chunks": chunk.text_chunks,
                "images": []  # Always empty for TXT
            }
            txt_data["sections"].append(section_data)
        
        # Save complete data
        output_filename = f"{base_name}_txt_extraction_{timestamp}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(txt_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ TXT extraction saved: {output_path}")
        
        # Save text-only version (same as complete for TXT, but consistent with other parsers)
        text_filename = f"{base_name}_txt_text_{timestamp}.json"
        text_path = os.path.join(output_dir, text_filename)
        
        text_data = {
            "metadata": txt_data["metadata"],
            "text_content": []
        }
        
        for section in txt_data["sections"]:
            for i, text in enumerate(section["text_chunks"]):
                text_data["text_content"].append({
                    "section_number": section["section_number"],
                    "chunk_id": i,
                    "text": text,
                    "word_count": len(text.split()),
                    "char_count": len(text)
                })
        
        with open(text_path, 'w', encoding='utf-8') as f:
            json.dump(text_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ TXT text-only saved: {text_path}")
        
        return output_path

def main():
    """Main function to test the TXT parser"""
    txt_file = "sample.txt"  # Change to your TXT file
    
    # Create parser
    parser = TXTParser()
    
    # Parse TXT with different strategies
    print("=== Testing Paragraph Chunking ===")
    chunks_paragraphs = parser.parse_txt(txt_file, chunk_strategy="paragraphs")
    output_path_para = parser.save_txt_extraction(chunks_paragraphs, "./txt_results", txt_file)
    
    print("\n=== Testing Section Detection ===")
    chunks_sections = parser.parse_txt(txt_file, chunk_strategy="sections")
    output_path_sections = parser.save_txt_extraction(chunks_sections, "./txt_results", txt_file)
    
    print("\n=== Testing Fixed Chunking ===")
    chunks_fixed = parser.parse_txt(txt_file, chunk_strategy="fixed")
    output_path_fixed = parser.save_txt_extraction(chunks_fixed, "./txt_results", txt_file)
    
    # Print summary
    total_text_para = sum(len(chunk.text_chunks) for chunk in chunks_paragraphs)
    total_text_sections = sum(len(chunk.text_chunks) for chunk in chunks_sections)
    total_text_fixed = sum(len(chunk.text_chunks) for chunk in chunks_fixed)
    
    print(f"\n📊 TXT EXTRACTION SUMMARY:")
    print(f"   TXT: {txt_file}")
    print(f"   Paragraph strategy: {len(chunks_paragraphs)} sections, {total_text_para} chunks")
    print(f"   Section strategy: {len(chunks_sections)} sections, {total_text_sections} chunks")
    print(f"   Fixed strategy: {len(chunks_fixed)} sections, {total_text_fixed} chunks")
    print(f"   Results saved in: ./txt_results/")

if __name__ == "__main__":
    main()