# # docx_parser_complete.py
# import os
# import tempfile
# import json
# import logging
# from typing import List, Optional, Dict, Any
# from datetime import datetime
# from docx import Document
# from docx.document import Document as DocxDocument
# from docx.oxml.table import CT_Tbl
# from docx.oxml.text.paragraph import CT_P
# from docx.table import Table, _Cell
# from docx.text.paragraph import Paragraph
# import zipfile
# from PIL import Image
# import io
# from pydantic import BaseModel

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(message)s')
# logger = logging.getLogger(__name__)

# # Data Models (Same as PDF/PPTX)
# class ImageChunk(BaseModel):
#     path: str
#     caption: Optional[str] = None
#     bbox: Optional[List[float]] = None
#     metadata: Optional[Dict[str, Any]] = None
#     image_type: Optional[str] = None

# class DocumentChunk(BaseModel):
#     doc_id: str
#     unit: str
#     index: int
#     text_chunks: List[str]
#     images: List[ImageChunk]
#     embeddings: Optional[Dict[str, List[float]]] = None

# class DOCXParser:
#     """
#     Complete DOCX parser that extracts text and ALL images
#     """
    
#     def __init__(self, output_image_dir: Optional[str] = None, user_id: str = "default", session_id: str = "default_session"):
#         self.output_image_dir = output_image_dir or tempfile.gettempdir()
#         self.user_id = user_id
#         self.session_id = session_id
#         os.makedirs(self.output_image_dir, exist_ok=True)
        
#         # DOCX-specific settings
#         self.min_paragraph_length = 10  # Minimum characters for a text chunk

#     def extract_text_from_paragraph(self, paragraph) -> Optional[str]:
#         """Extract text from a paragraph"""
#         try:
#             text = paragraph.text.strip()
#             if text and len(text) >= self.min_paragraph_length:
#                 return text
#         except Exception as e:
#             logger.debug(f"Error extracting text from paragraph: {e}")
#         return None

#     def extract_text_from_table(self, table) -> List[str]:
#         """Extract text from tables"""
#         table_texts = []
#         try:
#             for row in table.rows:
#                 row_text = []
#                 for cell in row.cells:
#                     cell_text = cell.text.strip()
#                     if cell_text:
#                         row_text.append(cell_text)
#                 if row_text:
#                     table_texts.append(" | ".join(row_text))
#         except Exception as e:
#             logger.debug(f"Error extracting text from table: {e}")
#         return table_texts

#     def extract_images_from_docx(self, docx_path: str, chunk_index: int) -> List[ImageChunk]:
#         """Extract ALL images from DOCX file"""
#         images = []
#         try:
#             # Open DOCX as zip to access embedded images
#             with zipfile.ZipFile(docx_path, 'r') as docx_zip:
#                 # Look for images in the media directory
#                 media_files = [f for f in docx_zip.namelist() if f.startswith('word/media/')]
                
#                 for img_index, media_path in enumerate(media_files):
#                     try:
#                         # Extract image data
#                         image_data = docx_zip.read(media_path)
                        
#                         # Determine file extension - ALL FORMATS
#                         ext = self._get_image_extension(image_data)
#                         if not ext:
#                             # Default to png if cannot determine
#                             ext = 'png'
                            
#                         # Generate filename
#                         filename = f"docx_chunk_{chunk_index:03d}_img_{img_index:03d}.{ext}"
#                         image_path = os.path.join(self.output_image_dir, filename)
                        
#                         # Save image
#                         with open(image_path, 'wb') as f:
#                             f.write(image_data)
                        
#                         # Get image dimensions
#                         width, height = self._get_image_dimensions(image_data)
#                         area = width * height
                        
#                         images.append(ImageChunk(
#                             path=image_path,
#                             metadata={
#                                 'width': width,
#                                 'height': height,
#                                 'area': area,  # Important for filtering
#                                 'file_size': len(image_data),
#                                 'source_path': media_path,
#                                 'chunk_index': chunk_index,
#                                 'image_index': img_index,
#                                 'extension': ext
#                             },
#                             image_type="extracted"
#                         ))
                        
#                         logger.info(f"Extracted image: {width}x{height} pixels - {filename}")
                        
#                     except Exception as e:
#                         logger.warning(f"Error extracting image {media_path}: {e}")
#                         continue
                        
#         except Exception as e:
#             logger.error(f"Error extracting images from DOCX: {e}")
            
#         return images

#     def _get_image_extension(self, image_data: bytes) -> Optional[str]:
#         """Determine image extension from binary data - ALL FORMATS"""
#         try:
#             # Check common image signatures
#             if image_data.startswith(b'\xff\xd8\xff'):  # JPEG
#                 return 'jpg'
#             elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
#                 return 'png'
#             elif image_data.startswith(b'GIF8'):  # GIF
#                 return 'gif'
#             elif image_data.startswith(b'BM'):  # BMP
#                 return 'bmp'
#             elif image_data.startswith(b'\x00\x00\x01\x00'):  # ICO
#                 return 'ico'
#             elif image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP':  # WEBP
#                 return 'webp'
#             elif image_data.startswith(b'%PDF'):  # PDF (embedded)
#                 return 'pdf'
#             elif image_data.startswith(b'\x00\x00\x00\x0c'):  # JP2
#                 return 'jp2'
#         except Exception as e:
#             logger.debug(f"Error determining image extension: {e}")
#         return None

#     def _get_image_dimensions(self, image_data: bytes) -> tuple:
#         """Get image dimensions from binary data"""
#         try:
#             image = Image.open(io.BytesIO(image_data))
#             return image.size
#         except Exception as e:
#             logger.debug(f"Error getting image dimensions: {e}")
#             return 0, 0

#     def iter_block_items(self, parent):
#         """
#         Iterate through all blocks (paragraphs and tables) in a DOCX document
#         """
#         try:
#             if isinstance(parent, DocxDocument):
#                 parent_elm = parent.element.body
#             else:
#                 parent_elm = parent
            
#             for child in parent_elm.iterchildren():
#                 if isinstance(child, CT_P):
#                     yield Paragraph(child, parent)
#                 elif isinstance(child, CT_Tbl):
#                     yield Table(child, parent)
#         except Exception as e:
#             logger.error(f"Error iterating DOCX blocks: {e}")

#     def parse_docx(self, file_path: str, doc_id: Optional[str] = None) -> List[DocumentChunk]:
#         """Parse DOCX file and return document chunks - EXTRACT ALL IMAGES"""
#         if not os.path.exists(file_path):
#             raise FileNotFoundError(f"DOCX file not found: {file_path}")
        
#         if doc_id is None:
#             doc_id = os.path.splitext(os.path.basename(file_path))[0]
        
#         document_chunks = []
        
#         try:
#             # Load DOCX document
#             doc = Document(file_path)
#             logger.info(f"Parsing DOCX: {file_path}")
#             logger.info(f"Mode: EXTRACT ALL IMAGES")
            
#             # Extract ALL images first
#             all_images = self.extract_images_from_docx(file_path, 0)
#             logger.info(f"Total images found: {len(all_images)}")
            
#             text_chunks = []
#             current_section = 0
            
#             # Iterate through all content blocks
#             for block in self.iter_block_items(doc):
#                 if isinstance(block, Paragraph):
#                     text = self.extract_text_from_paragraph(block)
#                     if text:
#                         text_chunks.append(text)
                        
#                         # Start new section for headings
#                         if self._is_heading(block):
#                             if text_chunks:  # Save current section if it has content
#                                 chunk = DocumentChunk(
#                                     doc_id=doc_id,
#                                     unit="section",
#                                     index=current_section,
#                                     text_chunks=text_chunks.copy(),
#                                     images=all_images if current_section == 0 else []  # Add images to first section
#                                 )
#                                 document_chunks.append(chunk)
#                                 current_section += 1
#                                 text_chunks.clear()
                
#                 elif isinstance(block, Table):
#                     table_texts = self.extract_text_from_table(block)
#                     text_chunks.extend(table_texts)
            
#             # Add final section
#             if text_chunks:
#                 chunk = DocumentChunk(
#                     doc_id=doc_id,
#                     unit="section",
#                     index=current_section,
#                     text_chunks=text_chunks,
#                     images=all_images if current_section == 0 else []  # Add images to first section if not already added
#                 )
#                 document_chunks.append(chunk)
            
#             # If no sections were created (no headings), create one chunk with all content
#             if not document_chunks and (text_chunks or all_images):
#                 chunk = DocumentChunk(
#                     doc_id=doc_id,
#                     unit="section",
#                     index=0,
#                     text_chunks=text_chunks,
#                     images=all_images  # ALL images
#                 )
#                 document_chunks.append(chunk)
            
#             logger.info(f"DOCX parsing complete: {len(document_chunks)} sections, {len(all_images)} total images")
            
#             return document_chunks
            
#         except Exception as e:
#             logger.error(f"Error parsing DOCX {file_path}: {e}")
#             raise

#     def _is_heading(self, paragraph) -> bool:
#         """Check if paragraph is a heading"""
#         try:
#             return paragraph.style.name.startswith('Heading')
#         except:
#             return False

#     def save_docx_extraction(self, chunks: List[DocumentChunk], output_dir: str, docx_file: str):
#         """Save DOCX extraction results to JSON (same format as PDF/PPTX)"""
#         os.makedirs(output_dir, exist_ok=True)
        
#         base_name = os.path.splitext(os.path.basename(docx_file))[0]
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
#         # Create data structure (same format as PDF/PPTX)
#         docx_data = {
#             "metadata": {
#                 "source_file": docx_file,
#                 "file_type": "docx",
#                 "extraction_time": timestamp,
#                 "total_sections": len(chunks),
#                 "total_text_chunks": sum(len(chunk.text_chunks) for chunk in chunks),
#                 "total_images": sum(len(chunk.images) for chunk in chunks)
#             },
#             "sections": []  # Same structure as "pages" in PDF, "slides" in PPTX
#         }
        
#         for chunk in chunks:
#             section_data = {
#                 "section_number": chunk.index,
#                 "unit_type": chunk.unit,
#                 "text_chunks_count": len(chunk.text_chunks),
#                 "images_count": len(chunk.images),
#                 "text_chunks": chunk.text_chunks,
#                 "images": [
#                     {
#                         "path": img.path,
#                         "caption": img.caption,
#                         "bbox": img.bbox,
#                         "metadata": img.metadata
#                     }
#                     for img in chunk.images
#                 ]
#             }
#             docx_data["sections"].append(section_data)
        
#         # Save complete data
#         output_filename = f"{base_name}_docx_extraction_{timestamp}.json"
#         output_path = os.path.join(output_dir, output_filename)
        
#         with open(output_path, 'w', encoding='utf-8') as f:
#             json.dump(docx_data, f, indent=2, ensure_ascii=False)
        
#         print(f"✓ DOCX extraction saved: {output_path}")
        
#         # Save text-only version
#         text_filename = f"{base_name}_docx_text_{timestamp}.json"
#         text_path = os.path.join(output_dir, text_filename)
        
#         text_data = {
#             "metadata": docx_data["metadata"],
#             "text_content": []
#         }
        
#         for section in docx_data["sections"]:
#             for i, text in enumerate(section["text_chunks"]):
#                 text_data["text_content"].append({
#                     "section_number": section["section_number"],
#                     "chunk_id": i,
#                     "text": text
#                 })
        
#         with open(text_path, 'w', encoding='utf-8') as f:
#             json.dump(text_data, f, indent=2, ensure_ascii=False)
        
#         print(f"✓ DOCX text-only saved: {text_path}")
        
#         return output_path

# def main():
#     """Main function to test the DOCX parser"""
#     docx_file = "sample.docx"  # Change to your DOCX file
    
#     # Create parser
#     parser = DOCXParser(output_image_dir="./docx_images_complete")
    
#     # Parse DOCX - EXTRACT ALL IMAGES
#     chunks = parser.parse_docx(docx_file)
    
#     # Save results
#     output_path = parser.save_docx_extraction(chunks, "./docx_results", docx_file)
    
#     # Print summary
#     total_text = sum(len(chunk.text_chunks) for chunk in chunks)
#     total_images = sum(len(chunk.images) for chunk in chunks)
    
#     print(f"\n📊 DOCX EXTRACTION SUMMARY:")
#     print(f"   DOCX: {docx_file}")
#     print(f"   Sections: {len(chunks)}")
#     print(f"   Text chunks: {total_text}")
#     print(f"   Images: {total_images}")
#     print(f"   Results saved in: ./docx_results/")

# if __name__ == "__main__":
#     main()



# docx_parser_complete.py
import os
import tempfile
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
import zipfile
from PIL import Image
import io
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Data Models (Same as PDF/PPTX)
class ImageChunk(BaseModel):
    path: str
    caption: Optional[str] = None
    bbox: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    image_type: Optional[str] = None

class DocumentChunk(BaseModel):
    doc_id: str
    unit: str
    index: int
    text_chunks: List[str]
    images: List[ImageChunk]
    embeddings: Optional[Dict[str, List[float]]] = None

class DOCXParser:
    """
    Complete DOCX parser that extracts text and ACTUAL images only
    """
    
    def __init__(self, output_image_dir: Optional[str] = None, user_id: str = "default", session_id: str = "default_session"):
        self.output_image_dir = output_image_dir or tempfile.gettempdir()
        self.user_id = user_id
        self.session_id = session_id
        os.makedirs(self.output_image_dir, exist_ok=True)
        
        # DOCX-specific settings
        self.min_paragraph_length = 10  # Minimum characters for a text chunk

    def extract_text_from_paragraph(self, paragraph) -> Optional[str]:
        """Extract text from a paragraph"""
        try:
            text = paragraph.text.strip()
            if text and len(text) >= self.min_paragraph_length:
                return text
        except Exception as e:
            logger.debug(f"Error extracting text from paragraph: {e}")
        return None

    def extract_text_from_table(self, table) -> List[str]:
        """Extract text from tables"""
        table_texts = []
        try:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text:
                        row_text.append(cell_text)
                if row_text:
                    table_texts.append(" | ".join(row_text))
        except Exception as e:
            logger.debug(f"Error extracting text from table: {e}")
        return table_texts

    def _is_valid_image(self, image_data: bytes) -> bool:
        """Check if the data is actually a valid image"""
        try:
            # Try to open with PIL to verify it's a real image
            image = Image.open(io.BytesIO(image_data))
            image.verify()  # Verify it's a valid image file
            return True
        except Exception as e:
            logger.debug(f"Invalid image data: {e}")
            return False

    def _get_image_extension(self, image_data: bytes) -> Optional[str]:
        """Determine image extension from binary data - ONLY REAL IMAGES"""
        try:
            # Check common image signatures
            if image_data.startswith(b'\xff\xd8\xff'):  # JPEG
                return 'jpg'
            elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                return 'png'
            elif image_data.startswith(b'GIF8'):  # GIF
                return 'gif'
            elif image_data.startswith(b'BM'):  # BMP
                return 'bmp'
            elif image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP':  # WEBP
                return 'webp'
            elif image_data.startswith(b'%PDF'):  # PDF (embedded) - skip these
                return None
            elif image_data.startswith(b'PK'):  # ZIP file - skip these
                return None
            elif image_data.startswith(b'<?xml'):  # XML file - skip these
                return None
            elif image_data.startswith(b'\x00\x00\x00\x0c'):  # JP2
                return 'jp2'
            elif image_data.startswith(b'\x00\x00\x00\x18'):  # TIFF
                return 'tiff'
        except Exception as e:
            logger.debug(f"Error determining image extension: {e}")
        return None

    def _get_image_dimensions(self, image_data: bytes) -> tuple:
        """Get image dimensions from binary data"""
        try:
            image = Image.open(io.BytesIO(image_data))
            return image.size
        except Exception as e:
            logger.debug(f"Error getting image dimensions: {e}")
            return 0, 0

    def extract_images_from_docx(self, docx_path: str, chunk_index: int) -> List[ImageChunk]:
        """Extract ONLY VALID images from DOCX file"""
        images = []
        try:
            # Open DOCX as zip to access embedded images
            with zipfile.ZipFile(docx_path, 'r') as docx_zip:
                # Look for images in the media directory
                media_files = [f for f in docx_zip.namelist() if f.startswith('word/media/')]
                
                logger.info(f"Found {len(media_files)} files in media directory")
                
                for img_index, media_path in enumerate(media_files):
                    try:
                        # Extract file data
                        file_data = docx_zip.read(media_path)
                        
                        # Skip very small files (likely not images)
                        if len(file_data) < 1000:
                            logger.debug(f"Skipping small file: {media_path} ({len(file_data)} bytes)")
                            continue
                        
                        # Determine file extension - ONLY REAL IMAGES
                        ext = self._get_image_extension(file_data)
                        if not ext:
                            logger.debug(f"Skipping non-image file: {media_path}")
                            continue
                        
                        # Verify it's actually a valid image
                        if not self._is_valid_image(file_data):
                            logger.debug(f"Skipping invalid image: {media_path}")
                            continue
                            
                        # Generate filename
                        filename = f"docx_chunk_{chunk_index:03d}_img_{img_index:03d}.{ext}"
                        image_path = os.path.join(self.output_image_dir, filename)
                        
                        # Save image
                        with open(image_path, 'wb') as f:
                            f.write(file_data)
                        
                        # Get image dimensions
                        width, height = self._get_image_dimensions(file_data)
                        area = width * height
                        
                        images.append(ImageChunk(
                            path=image_path,
                            metadata={
                                'width': width,
                                'height': height,
                                'area': area,  # Important for filtering
                                'file_size': len(file_data),
                                'source_path': media_path,
                                'chunk_index': chunk_index,
                                'image_index': img_index,
                                'extension': ext
                            },
                            image_type="extracted"
                        ))
                        
                        logger.info(f"✅ Extracted VALID image: {width}x{height} pixels - {filename}")
                        
                    except Exception as e:
                        logger.warning(f"Error extracting image {media_path}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error extracting images from DOCX: {e}")
            
        logger.info(f"Total valid images extracted: {len(images)}")
        return images

    def iter_block_items(self, parent):
        """
        Iterate through all blocks (paragraphs and tables) in a DOCX document
        """
        try:
            if isinstance(parent, DocxDocument):
                parent_elm = parent.element.body
            else:
                parent_elm = parent
            
            for child in parent_elm.iterchildren():
                if isinstance(child, CT_P):
                    yield Paragraph(child, parent)
                elif isinstance(child, CT_Tbl):
                    yield Table(child, parent)
        except Exception as e:
            logger.error(f"Error iterating DOCX blocks: {e}")

    def parse_docx(self, file_path: str, doc_id: Optional[str] = None) -> List[DocumentChunk]:
        """Parse DOCX file and return document chunks - EXTRACT ONLY VALID IMAGES"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"DOCX file not found: {file_path}")
        
        if doc_id is None:
            doc_id = os.path.splitext(os.path.basename(file_path))[0]
        
        document_chunks = []
        
        try:
            # Load DOCX document
            doc = Document(file_path)
            logger.info(f"Parsing DOCX: {file_path}")
            logger.info(f"Mode: EXTRACT ONLY VALID IMAGES")
            
            # Extract ONLY VALID images
            all_images = self.extract_images_from_docx(file_path, 0)
            logger.info(f"Total valid images found: {len(all_images)}")
            
            text_chunks = []
            current_section = 0
            
            # Iterate through all content blocks
            for block in self.iter_block_items(doc):
                if isinstance(block, Paragraph):
                    text = self.extract_text_from_paragraph(block)
                    if text:
                        text_chunks.append(text)
                        
                        # Start new section for headings
                        if self._is_heading(block):
                            if text_chunks:  # Save current section if it has content
                                chunk = DocumentChunk(
                                    doc_id=doc_id,
                                    unit="section",
                                    index=current_section,
                                    text_chunks=text_chunks.copy(),
                                    images=all_images if current_section == 0 else []  # Add images to first section
                                )
                                document_chunks.append(chunk)
                                current_section += 1
                                text_chunks.clear()
                
                elif isinstance(block, Table):
                    table_texts = self.extract_text_from_table(block)
                    text_chunks.extend(table_texts)
            
            # Add final section
            if text_chunks:
                chunk = DocumentChunk(
                    doc_id=doc_id,
                    unit="section",
                    index=current_section,
                    text_chunks=text_chunks,
                    images=all_images if current_section == 0 else []  # Add images to first section if not already added
                )
                document_chunks.append(chunk)
            
            # If no sections were created (no headings), create one chunk with all content
            if not document_chunks and (text_chunks or all_images):
                chunk = DocumentChunk(
                    doc_id=doc_id,
                    unit="section",
                    index=0,
                    text_chunks=text_chunks,
                    images=all_images  # ALL VALID images
                )
                document_chunks.append(chunk)
            
            logger.info(f"DOCX parsing complete: {len(document_chunks)} sections, {len(all_images)} valid images")
            
            return document_chunks
            
        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path}: {e}")
            raise

    def _is_heading(self, paragraph) -> bool:
        """Check if paragraph is a heading"""
        try:
            return paragraph.style.name.startswith('Heading')
        except:
            return False

    def save_docx_extraction(self, chunks: List[DocumentChunk], output_dir: str, docx_file: str):
        """Save DOCX extraction results to JSON (same format as PDF/PPTX)"""
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(docx_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create data structure (same format as PDF/PPTX)
        docx_data = {
            "metadata": {
                "source_file": docx_file,
                "file_type": "docx",
                "extraction_time": timestamp,
                "total_sections": len(chunks),
                "total_text_chunks": sum(len(chunk.text_chunks) for chunk in chunks),
                "total_images": sum(len(chunk.images) for chunk in chunks)
            },
            "sections": []  # Same structure as "pages" in PDF, "slides" in PPTX
        }
        
        for chunk in chunks:
            section_data = {
                "section_number": chunk.index,
                "unit_type": chunk.unit,
                "text_chunks_count": len(chunk.text_chunks),
                "images_count": len(chunk.images),
                "text_chunks": chunk.text_chunks,
                "images": [
                    {
                        "path": img.path,
                        "caption": img.caption,
                        "bbox": img.bbox,
                        "metadata": img.metadata
                    }
                    for img in chunk.images
                ]
            }
            docx_data["sections"].append(section_data)
        
        # Save complete data
        output_filename = f"{base_name}_docx_extraction_{timestamp}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(docx_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ DOCX extraction saved: {output_path}")
        
        # Save text-only version
        text_filename = f"{base_name}_docx_text_{timestamp}.json"
        text_path = os.path.join(output_dir, text_filename)
        
        text_data = {
            "metadata": docx_data["metadata"],
            "text_content": []
        }
        
        for section in docx_data["sections"]:
            for i, text in enumerate(section["text_chunks"]):
                text_data["text_content"].append({
                    "section_number": section["section_number"],
                    "chunk_id": i,
                    "text": text
                })
        
        with open(text_path, 'w', encoding='utf-8') as f:
            json.dump(text_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ DOCX text-only saved: {text_path}")
        
        return output_path

def main():
    """Main function to test the DOCX parser"""
    docx_file = "sample.docx"  # Change to your DOCX file
    
    # Create parser
    parser = DOCXParser(output_image_dir="./docx_images_complete")
    
    # Parse DOCX - EXTRACT ONLY VALID IMAGES
    chunks = parser.parse_docx(docx_file)
    
    # Save results
    output_path = parser.save_docx_extraction(chunks, "./docx_results", docx_file)
    
    # Print summary
    total_text = sum(len(chunk.text_chunks) for chunk in chunks)
    total_images = sum(len(chunk.images) for chunk in chunks)
    
    print(f"\n📊 DOCX EXTRACTION SUMMARY:")
    print(f"   DOCX: {docx_file}")
    print(f"   Sections: {len(chunks)}")
    print(f"   Text chunks: {total_text}")
    print(f"   Valid images: {total_images}")
    print(f"   Results saved in: ./docx_results/")

if __name__ == "__main__":
    main()