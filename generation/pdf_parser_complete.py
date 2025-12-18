# # pdf_parser_complete.py
# import fitz  # PyMuPDF
# import os
# import tempfile
# import json
# import logging
# from typing import List, Optional, Dict, Any, Tuple
# from datetime import datetime
# from pydantic import BaseModel

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(message)s')
# logger = logging.getLogger(__name__)

# # Data Models
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

# class PDFParser:
#     """
#     Fixed PDF parser with robust image extraction (all formats)
#     """
    
#     def __init__(self, output_image_dir: Optional[str] = None, user_id: str = "default", session_id: str = "default_session"):
#         self.output_image_dir = output_image_dir or tempfile.gettempdir()
#         self.user_id = user_id
#         self.session_id = session_id
#         os.makedirs(self.output_image_dir, exist_ok=True)

#     def extract_text_blocks(self, page) -> List[str]:
#         """Extract text blocks from PDF page"""
#         text_chunks = []
#         try:
#             # Extract text with structure preservation
#             text_blocks = page.get_text("dict")
            
#             for block in text_blocks["blocks"]:
#                 if "lines" in block:  # Text block
#                     block_text = ""
#                     for line in block["lines"]:
#                         for span in line["spans"]:
#                             block_text += span["text"] + " "
                    
#                     text = block_text.strip()
#                     if text and len(text) > 10:
#                         text_chunks.append(text)
                        
#         except Exception as e:
#             logger.warning(f"Error extracting text from page: {e}")
            
#         return text_chunks

#     def safe_extract_images(self, page, page_index: int) -> List[ImageChunk]:
#         """Safely extract images with proper error handling - ALL FORMATS"""
#         images = []
        
#         try:
#             # Get image information
#             image_list = page.get_images()
#             image_info_list = page.get_image_info()
            
#             logger.info(f"Page {page_index}: Found {len(image_list)} image objects, {len(image_info_list)} positioned images")
            
#             # Create mapping from xref to bbox
#             bbox_map = {}
#             for img_info in image_info_list:
#                 bbox_map[img_info['xref']] = img_info['bbox']
            
#             extracted_count = 0
#             for img_index, img in enumerate(image_list):
#                 try:
#                     xref = img[0]
                    
#                     # Method 1: Try extract_image first (more reliable)
#                     try:
#                         base_image = page.parent.extract_image(xref)
#                         if base_image and "image" in base_image:
#                             # Use original extension or default to png
#                             ext = base_image.get('ext', 'png')
#                             filename = f"page_{page_index:03d}_img_{extracted_count:03d}.{ext}"
#                             image_path = os.path.join(self.output_image_dir, filename)
                            
#                             with open(image_path, "wb") as f:
#                                 f.write(base_image["image"])
                            
#                             # Get dimensions
#                             width = base_image.get('width', 0)
#                             height = base_image.get('height', 0)
#                             area = width * height
                            
#                             images.append(ImageChunk(
#                                 path=image_path,
#                                 bbox=bbox_map.get(xref),
#                                 metadata={
#                                     'width': width,
#                                     'height': height,
#                                     'area': area,  # Important for filtering
#                                     'ext': ext,
#                                     'method': 'extract_image',
#                                     'xref': xref,
#                                     'page_index': page_index,
#                                     'image_index': extracted_count
#                                 },
#                                 image_type="extracted"
#                             ))
#                             logger.info(f"  ✅ Extracted image {extracted_count} via extract_image: {width}x{height} ({ext})")
#                             extracted_count += 1
#                             continue  # Success with this method
#                     except Exception as e1:
#                         logger.debug(f"  extract_image failed for xref {xref}: {e1}")
                    
#                     # Method 2: Fall back to Pixmap method
#                     try:
#                         pix = fitz.Pixmap(page.parent, xref)
                        
#                         if pix.width > 0 and pix.height > 0:
#                             # Convert to RGB if needed
#                             if pix.n != 3:
#                                 pix = fitz.Pixmap(fitz.csRGB, pix)
                            
#                             filename = f"page_{page_index:03d}_img_{extracted_count:03d}.png"
#                             image_path = os.path.join(self.output_image_dir, filename)
#                             pix.save(image_path)
                            
#                             area = pix.width * pix.height
                            
#                             images.append(ImageChunk(
#                                 path=image_path,
#                                 bbox=bbox_map.get(xref),
#                                 metadata={
#                                     'width': pix.width,
#                                     'height': pix.height,
#                                     'area': area,  # Important for filtering
#                                     'method': 'pixmap',
#                                     'xref': xref,
#                                     'page_index': page_index,
#                                     'image_index': extracted_count
#                                 },
#                                 image_type="extracted"
#                             ))
#                             logger.info(f"  ✅ Extracted image {extracted_count} via Pixmap: {pix.width}x{pix.height}")
#                             extracted_count += 1
                        
#                         pix = None  # Free memory
                        
#                     except Exception as e2:
#                         logger.debug(f"  Pixmap failed for xref {xref}: {e2}")
                    
#                 except Exception as e:
#                     logger.warning(f"  Error processing image {img_index}: {e}")
#                     continue
            
#             logger.info(f"Page {page_index}: Successfully extracted {extracted_count} images")
            
#         except Exception as e:
#             logger.error(f"Error in safe_extract_images for page {page_index}: {e}")
#             # Don't re-raise, just return empty images list
        
#         return images

#     def parse_pdf(self, file_path: str, doc_id: Optional[str] = None) -> List[DocumentChunk]:
#         """Parse PDF file with robust error handling - EXTRACT ALL IMAGES"""
#         if not os.path.exists(file_path):
#             raise FileNotFoundError(f"PDF file not found: {file_path}")
        
#         if doc_id is None:
#             doc_id = os.path.splitext(os.path.basename(file_path))[0]
        
#         document_chunks = []
#         pdf_document = None
        
#         try:
#             # Open PDF
#             pdf_document = fitz.open(file_path)
#             logger.info(f"Parsing PDF: {file_path} with {len(pdf_document)} pages")
#             logger.info(f"Mode: EXTRACT ALL IMAGES")
            
#             for page_index in range(len(pdf_document)):
#                 page = pdf_document[page_index]
                
#                 try:
#                     # Extract text
#                     text_chunks = self.extract_text_blocks(page)
                    
#                     # Extract images with safe method - ALL IMAGES
#                     images = self.safe_extract_images(page, page_index)
                    
#                     # Create document chunk with ALL images
#                     chunk = DocumentChunk(
#                         doc_id=doc_id,
#                         unit="page",
#                         index=page_index,
#                         text_chunks=text_chunks,
#                         images=images  # All images, no filtering
#                     )
#                     document_chunks.append(chunk)
                    
#                     logger.info(f"Page {page_index}: {len(text_chunks)} text chunks, {len(images)} images")
                    
#                 except Exception as page_error:
#                     logger.error(f"Error processing page {page_index}: {page_error}")
#                     # Continue with next page even if this one fails
#                     continue
            
#             logger.info(f"PDF parsing complete: {len(document_chunks)} pages processed")
#             logger.info(f"Total images extracted: {sum(len(chunk.images) for chunk in document_chunks)}")
            
#             return document_chunks
            
#         except Exception as e:
#             logger.error(f"Error parsing PDF {file_path}: {e}")
#             raise
#         finally:
#             # Ensure PDF is always closed
#             if pdf_document:
#                 pdf_document.close()

#     def save_pdf_extraction(self, chunks: List[DocumentChunk], output_dir: str, pdf_file: str):
#         """Save PDF extraction results to JSON"""
#         os.makedirs(output_dir, exist_ok=True)
        
#         base_name = os.path.splitext(os.path.basename(pdf_file))[0]
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
#         # Create data structure
#         pdf_data = {
#             "metadata": {
#                 "source_file": pdf_file,
#                 "file_type": "pdf",
#                 "extraction_time": timestamp,
#                 "total_pages": len(chunks),
#                 "total_text_chunks": sum(len(chunk.text_chunks) for chunk in chunks),
#                 "total_images": sum(len(chunk.images) for chunk in chunks)
#             },
#             "pages": []
#         }
        
#         for chunk in chunks:
#             page_data = {
#                 "page_number": chunk.index,
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
#             pdf_data["pages"].append(page_data)
        
#         # Save complete data
#         output_filename = f"{base_name}_pdf_extraction_{timestamp}.json"
#         output_path = os.path.join(output_dir, output_filename)
        
#         with open(output_path, 'w', encoding='utf-8') as f:
#             json.dump(pdf_data, f, indent=2, ensure_ascii=False)
        
#         print(f"✓ PDF extraction saved: {output_path}")
#         return output_path

# def debug_pdf_simple(pdf_path: str):
#     """Simple debug function to check PDF structure"""
#     print(f"\n=== SIMPLE PDF DEBUG: {pdf_path} ===")
    
#     try:
#         doc = fitz.open(pdf_path)
        
#         for page_num in range(len(doc)):
#             page = doc[page_num]
            
#             # Basic info
#             text = page.get_text()
#             images = page.get_images()
#             image_info = page.get_image_info()
            
#             print(f"Page {page_num}: {len(text)} chars, {len(images)} images, {len(image_info)} positioned")
            
#             # Try to extract first image if exists
#             if images:
#                 try:
#                     img = images[0]
#                     xref = img[0]
                    
#                     # Try extract_image method
#                     base_image = doc.extract_image(xref)
#                     if base_image:
#                         print(f"  First image: can extract via extract_image, format: {base_image['ext']}")
#                     else:
#                         print(f"  First image: extract_image failed")
                        
#                 except Exception as e:
#                     print(f"  First image: error - {e}")
        
#         doc.close()
        
#     except Exception as e:
#         print(f"Error debugging PDF: {e}")

# def main():
#     """Main function with robust error handling"""
#     pdf_file = "sample.pdf"  # Change to your PDF file
    
#     print("=== ROBUST PDF PARSER ===")
    
#     # Simple debug first
#     debug_pdf_simple(pdf_file)
    
#     try:
#         # Create parser
#         parser = PDFParser(output_image_dir="./pdf_images_complete")
        
#         # Parse PDF - EXTRACT ALL IMAGES
#         chunks = parser.parse_pdf(pdf_file)
        
#         # Save results
#         output_path = parser.save_pdf_extraction(chunks, "./pdf_results", pdf_file)
        
#         # Summary
#         total_text = sum(len(chunk.text_chunks) for chunk in chunks)
#         total_images = sum(len(chunk.images) for chunk in chunks)
        
#         print(f"\n📊 FINAL SUMMARY:")
#         print(f"   PDF: {pdf_file}")
#         print(f"   Pages: {len(chunks)}")
#         print(f"   Text chunks: {total_text}")
#         print(f"   Images extracted: {total_images}")
        
#     except Exception as e:
#         print(f"❌ Critical error: {e}")
#         # Try to continue with at least text extraction
#         print("Attempting text-only extraction...")
#         try:
#             doc = fitz.open(pdf_file)
#             text_content = []
#             for page_num in range(len(doc)):
#                 text = doc[page_num].get_text()
#                 text_content.append(f"--- Page {page_num} ---\n{text}")
#             doc.close()
            
#             # Save text only
#             os.makedirs("./pdf_results", exist_ok=True)
#             with open("./pdf_results/text_only.txt", "w", encoding="utf-8") as f:
#                 f.write("\n\n".join(text_content))
#             print("✓ Text-only extraction completed")
            
#         except Exception as e2:
#             print(f"❌ Even text extraction failed: {e2}")

# if __name__ == "__main__":
#     main()



# pdf_parser_complete.py
import fitz  # PyMuPDF
import os
import tempfile
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Data Models
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

class PDFParser:
    """
    Fixed PDF parser with robust image extraction (all formats)
    """
    
    def __init__(self, output_image_dir: Optional[str] = None, user_id: str = "default", session_id: str = "default_session"):
        self.output_image_dir = output_image_dir or tempfile.gettempdir()
        self.user_id = user_id
        self.session_id = session_id
        os.makedirs(self.output_image_dir, exist_ok=True)

    def extract_text_blocks(self, page) -> List[str]:
        """Extract text blocks from PDF page"""
        text_chunks = []
        try:
            # Extract text with structure preservation
            text_blocks = page.get_text("dict")
            
            for block in text_blocks["blocks"]:
                if "lines" in block:  # Text block
                    block_text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            block_text += span["text"] + " "
                    
                    text = block_text.strip()
                    if text and len(text) > 10:
                        text_chunks.append(text)
                        
        except Exception as e:
            logger.warning(f"Error extracting text from page: {e}")
            
        return text_chunks

    def safe_extract_images(self, page, page_index: int) -> List[ImageChunk]:
        """Safely extract images with proper error handling - ALL FORMATS"""
        images = []
        
        try:
            # Get image information
            image_list = page.get_images()
            image_info_list = page.get_image_info()
            
            logger.info(f"Page {page_index}: Found {len(image_list)} image objects, {len(image_info_list)} positioned images")
            
            # Create mapping from xref to bbox
            bbox_map = {}
            for img_info in image_info_list:
                xref = img_info.get('xref', 0)
                if xref:
                    bbox_map[xref] = img_info['bbox']
            
            extracted_count = 0
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    
                    # Method 1: Try extract_image first (more reliable)
                    try:
                        base_image = page.parent.extract_image(xref)
                        if base_image and "image" in base_image:
                            # Use original extension or default to png
                            ext = base_image.get('ext', 'png')
                            filename = f"page_{page_index:03d}_img_{extracted_count:03d}.{ext}"
                            image_path = os.path.join(self.output_image_dir, filename)
                            
                            with open(image_path, "wb") as f:
                                f.write(base_image["image"])
                            
                            # Get dimensions
                            width = base_image.get('width', 0)
                            height = base_image.get('height', 0)
                            area = width * height
                            
                            images.append(ImageChunk(
                                path=image_path,
                                bbox=bbox_map.get(xref),
                                metadata={
                                    'width': width,
                                    'height': height,
                                    'area': area,  # Important for filtering
                                    'ext': ext,
                                    'method': 'extract_image',
                                    'xref': xref,
                                    'page_index': page_index,
                                    'image_index': extracted_count
                                },
                                image_type="extracted"
                            ))
                            logger.info(f"  ✅ Extracted image {extracted_count} via extract_image: {width}x{height} ({ext})")
                            extracted_count += 1
                            continue  # Success with this method
                    except Exception as e1:
                        logger.debug(f"  extract_image failed for xref {xref}: {e1}")
                    
                    # Method 2: Fall back to Pixmap method
                    try:
                        pix = fitz.Pixmap(page.parent, xref)
                        
                        if pix.width > 0 and pix.height > 0:
                            # Convert to RGB if needed
                            if pix.n != 3:
                                pix = fitz.Pixmap(fitz.csRGB, pix)
                            
                            filename = f"page_{page_index:03d}_img_{extracted_count:03d}.png"
                            image_path = os.path.join(self.output_image_dir, filename)
                            pix.save(image_path)
                            
                            area = pix.width * pix.height
                            
                            images.append(ImageChunk(
                                path=image_path,
                                bbox=bbox_map.get(xref),
                                metadata={
                                    'width': pix.width,
                                    'height': pix.height,
                                    'area': area,  # Important for filtering
                                    'method': 'pixmap',
                                    'xref': xref,
                                    'page_index': page_index,
                                    'image_index': extracted_count
                                },
                                image_type="extracted"
                            ))
                            logger.info(f"  ✅ Extracted image {extracted_count} via Pixmap: {pix.width}x{pix.height}")
                            extracted_count += 1
                        
                        pix = None  # Free memory
                        
                    except Exception as e2:
                        logger.debug(f"  Pixmap failed for xref {xref}: {e2}")
                    
                except Exception as e:
                    logger.warning(f"  Error processing image {img_index}: {e}")
                    continue
            
            logger.info(f"Page {page_index}: Successfully extracted {extracted_count} images")
            
        except Exception as e:
            logger.error(f"Error in safe_extract_images for page {page_index}: {e}")
            # Don't re-raise, just return empty images list
        
        return images

    def extract_images_simple(self, page, page_index: int) -> List[ImageChunk]:
        """Simplified image extraction that works with most PDFs"""
        images = []
        try:
            # Get all images on the page
            image_list = page.get_images()
            logger.info(f"Page {page_index}: Found {len(image_list)} images")
            
            for i, img in enumerate(image_list):
                try:
                    xref = img[0]
                    
                    # Extract image using PyMuPDF's built-in method
                    pix = fitz.Pixmap(page.parent, xref)
                    
                    if pix.n - pix.alpha < 4:  # Check if it's a valid image
                        # Convert to RGB if needed
                        if pix.n != 3:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        
                        filename = f"page_{page_index:03d}_img_{i:03d}.png"
                        image_path = os.path.join(self.output_image_dir, filename)
                        pix.save(image_path)
                        
                        area = pix.width * pix.height
                        
                        images.append(ImageChunk(
                            path=image_path,
                            metadata={
                                'width': pix.width,
                                'height': pix.height,
                                'area': area,
                                'method': 'simple_pixmap',
                                'xref': xref,
                                'page_index': page_index,
                                'image_index': i
                            },
                            image_type="extracted"
                        ))
                        logger.info(f"  ✅ Simple extraction: {pix.width}x{pix.height}")
                    
                    pix = None  # Free memory
                    
                except Exception as e:
                    logger.warning(f"  Failed to extract image {i}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in simple image extraction for page {page_index}: {e}")
            
        return images

    def parse_pdf(self, file_path: str, doc_id: Optional[str] = None) -> List[DocumentChunk]:
        """Parse PDF file with robust error handling - EXTRACT ALL IMAGES"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        if doc_id is None:
            doc_id = os.path.splitext(os.path.basename(file_path))[0]
        
        document_chunks = []
        pdf_document = None
        
        try:
            # Open PDF
            pdf_document = fitz.open(file_path)
            logger.info(f"Parsing PDF: {file_path} with {len(pdf_document)} pages")
            logger.info(f"Mode: EXTRACT ALL IMAGES")
            
            for page_index in range(len(pdf_document)):
                page = pdf_document[page_index]
                
                try:
                    # Extract text
                    text_chunks = self.extract_text_blocks(page)
                    
                    # Try simple extraction first, fall back to advanced if needed
                    images = self.extract_images_simple(page, page_index)
                    if not images:
                        logger.info(f"  Trying advanced extraction for page {page_index}...")
                        images = self.safe_extract_images(page, page_index)
                    
                    # Create document chunk with ALL images
                    chunk = DocumentChunk(
                        doc_id=doc_id,
                        unit="page",
                        index=page_index,
                        text_chunks=text_chunks,
                        images=images  # All images, no filtering
                    )
                    document_chunks.append(chunk)
                    
                    logger.info(f"Page {page_index}: {len(text_chunks)} text chunks, {len(images)} images")
                    
                except Exception as page_error:
                    logger.error(f"Error processing page {page_index}: {page_error}")
                    # Continue with next page even if this one fails
                    continue
            
            total_images = sum(len(chunk.images) for chunk in document_chunks)
            logger.info(f"PDF parsing complete: {len(document_chunks)} pages processed")
            logger.info(f"Total images extracted: {total_images}")
            
            return document_chunks
            
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
            raise
        finally:
            # Ensure PDF is always closed
            if pdf_document:
                pdf_document.close()

    def save_pdf_extraction(self, chunks: List[DocumentChunk], output_dir: str, pdf_file: str):
        """Save PDF extraction results to JSON"""
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create data structure
        pdf_data = {
            "metadata": {
                "source_file": pdf_file,
                "file_type": "pdf",
                "extraction_time": timestamp,
                "total_pages": len(chunks),
                "total_text_chunks": sum(len(chunk.text_chunks) for chunk in chunks),
                "total_images": sum(len(chunk.images) for chunk in chunks)
            },
            "pages": []
        }
        
        for chunk in chunks:
            page_data = {
                "page_number": chunk.index,
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
            pdf_data["pages"].append(page_data)
        
        # Save complete data
        output_filename = f"{base_name}_pdf_extraction_{timestamp}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pdf_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ PDF extraction saved: {output_path}")
        return output_path

def debug_pdf_simple(pdf_path: str):
    """Simple debug function to check PDF structure"""
    print(f"\n=== SIMPLE PDF DEBUG: {pdf_path} ===")
    
    try:
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Basic info
            text = page.get_text()
            images = page.get_images()
            image_info = page.get_image_info()
            
            print(f"Page {page_num}: {len(text)} chars, {len(images)} images, {len(image_info)} positioned")
            
            # Try to extract first image if exists
            if images:
                try:
                    img = images[0]
                    xref = img[0]
                    print(f"  First image xref: {xref}")
                    
                    # Try extract_image method
                    base_image = doc.extract_image(xref)
                    if base_image:
                        print(f"  First image: can extract via extract_image, format: {base_image.get('ext', 'unknown')}")
                    else:
                        print(f"  First image: extract_image failed")
                        
                except Exception as e:
                    print(f"  First image: error - {e}")
        
        doc.close()
        
    except Exception as e:
        print(f"Error debugging PDF: {e}")

def main():
    """Main function with robust error handling"""
    pdf_file = "sample.pdf"  # Change to your PDF file
    
    print("=== ROBUST PDF PARSER ===")
    
    # Simple debug first
    debug_pdf_simple(pdf_file)
    
    try:
        # Create parser
        parser = PDFParser(output_image_dir="./pdf_images_complete")
        
        # Parse PDF - EXTRACT ALL IMAGES
        chunks = parser.parse_pdf(pdf_file)
        
        # Save results
        output_path = parser.save_pdf_extraction(chunks, "./pdf_results", pdf_file)
        
        # Summary
        total_text = sum(len(chunk.text_chunks) for chunk in chunks)
        total_images = sum(len(chunk.images) for chunk in chunks)
        
        print(f"\n📊 FINAL SUMMARY:")
        print(f"   PDF: {pdf_file}")
        print(f"   Pages: {len(chunks)}")
        print(f"   Text chunks: {total_text}")
        print(f"   Images extracted: {total_images}")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        # Try to continue with at least text extraction
        print("Attempting text-only extraction...")
        try:
            doc = fitz.open(pdf_file)
            text_content = []
            for page_num in range(len(doc)):
                text = doc[page_num].get_text()
                text_content.append(f"--- Page {page_num} ---\n{text}")
            doc.close()
            
            # Save text only
            os.makedirs("./pdf_results", exist_ok=True)
            with open("./pdf_results/text_only.txt", "w", encoding="utf-8") as f:
                f.write("\n\n".join(text_content))
            print("✓ Text-only extraction completed")
            
        except Exception as e2:
            print(f"❌ Even text extraction failed: {e2}")

if __name__ == "__main__":
    main()