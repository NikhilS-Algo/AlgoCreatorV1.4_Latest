# pptx_parser_advanced.py
import os
import tempfile
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pptx import Presentation
from pptx.shapes.base import BaseShape
from pptx.shapes.group import GroupShape
from pptx.enum.shapes import MSO_SHAPE_TYPE
import math
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

class AdvancedPPTXParser:
    """
    Advanced PPTX parser with complete image extraction (no filtering)
    """
    
    def __init__(self, output_image_dir: Optional[str] = None, user_id: str = "default", session_id: str = "default_session"):
        self.output_image_dir = output_image_dir or tempfile.gettempdir()
        self.user_id = user_id
        self.session_id = session_id
        os.makedirs(self.output_image_dir, exist_ok=True)
        
        # PPTX dimensions in EMU
        self.SLIDE_WIDTH = 12192000
        self.SLIDE_HEIGHT = 6858000
        self.EMU_PER_INCH = 914400

    def emu_to_inches(self, emu: int) -> float:
        """Convert EMU to inches"""
        return emu / self.EMU_PER_INCH

    def get_all_shapes_recursive(self, shape) -> List[Any]:
        """Recursively get all shapes including those in groups"""
        shapes = []
        
        try:
            # If it's a group shape, explore its children
            if hasattr(shape, 'shapes') and isinstance(shape, GroupShape):
                for child_shape in shape.shapes:
                    shapes.extend(self.get_all_shapes_recursive(child_shape))
            else:
                shapes.append(shape)
        except Exception as e:
            logger.debug(f"Error exploring shape: {e}")
            
        return shapes

    def extract_image_from_shape(self, shape, slide_index: int, image_counter: int) -> Optional[ImageChunk]:
        """Extract image from any shape type that contains an image"""
        try:
            # Check if shape has image data
            if not hasattr(shape, 'image') or not hasattr(shape.image, 'blob'):
                return None
                
            if not shape.image.blob or len(shape.image.blob) < 1000:
                return None
            
            # Get dimensions if available
            width = getattr(shape, 'width', 0)
            height = getattr(shape, 'height', 0)
            left = getattr(shape, 'left', 0)
            top = getattr(shape, 'top', 0)
            
            # Get image extension - EXTRACT ALL FORMATS
            ext = getattr(shape.image, 'ext', 'png').lower()
            if not ext:
                ext = 'png'
            
            # Save image (ALL formats now)
            filename = f"slide_{slide_index:03d}_img_{image_counter:03d}.{ext}"
            image_path = os.path.join(self.output_image_dir, filename)
            
            with open(image_path, "wb") as f:
                f.write(shape.image.blob)
            
            # Calculate area for filtering
            area = width * height
            
            return ImageChunk(
                path=image_path,
                bbox=[left, top, left + width, top + height],
                metadata={
                    'width': width,
                    'height': height,
                    'area': area,  # Important for filtering
                    'width_inches': self.emu_to_inches(width),
                    'height_inches': self.emu_to_inches(height),
                    'left_inches': self.emu_to_inches(left),
                    'top_inches': self.emu_to_inches(top),
                    'shape_type': str(type(shape)),
                    'is_placeholder': getattr(shape, 'is_placeholder', False),
                    'extension': ext,
                    'slide_index': slide_index,
                    'image_counter': image_counter
                },
                image_type="extracted"  # Will be classified later
            )
            
        except Exception as e:
            logger.warning(f"Error extracting image from shape: {e}")
            return None

    def extract_text_from_shape(self, shape) -> Optional[str]:
        """Extract text from any shape type"""
        try:
            if hasattr(shape, "text_frame") and shape.text_frame:
                text = shape.text_frame.text.strip()
                return text if text else None
        except Exception as e:
            logger.debug(f"Error extracting text from shape: {e}")
        return None

    def extract_all_content_from_slide(self, slide, slide_index: int) -> tuple:
        """Extract all text and images from a slide"""
        text_chunks = []
        all_images = []
        image_counter = 0
        
        # First pass: get all shapes recursively
        all_shapes = []
        for shape in slide.shapes:
            all_shapes.extend(self.get_all_shapes_recursive(shape))
        
        logger.info(f"Slide {slide_index}: Found {len(all_shapes)} total shapes")
        
        # Process each shape
        for shape in all_shapes:
            # Extract text
            text = self.extract_text_from_shape(shape)
            if text:
                text_chunks.append(text)
            
            # Extract images (ALL formats)
            image = self.extract_image_from_shape(shape, slide_index, image_counter)
            if image:
                all_images.append(image)
                image_counter += 1
                
                # Log extraction details
                logger.info(f"  📸 EXTRACTED: {os.path.basename(image.path)} "
                          f"({image.metadata['width_inches']:.1f}x{image.metadata['height_inches']:.1f}in) "
                          f"Area: {image.metadata['area']:,} EMU")
        
        return text_chunks, all_images

    def parse_pptx(self, file_path: str, doc_id: Optional[str] = None, 
                   extract_all: bool = True) -> List[DocumentChunk]:
        """Parse PPTX file with comprehensive extraction"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PPTX file not found: {file_path}")
        
        if doc_id is None:
            doc_id = os.path.splitext(os.path.basename(file_path))[0]
        
        document_chunks = []
        
        try:
            presentation = Presentation(file_path)
            logger.info(f"🔍 Parsing PPTX: {file_path}")
            logger.info(f"   Slides: {len(presentation.slides)}")
            logger.info(f"   Mode: EXTRACT ALL IMAGES")
            
            for slide_index, slide in enumerate(presentation.slides):
                logger.info(f"\n📊 Processing Slide {slide_index}...")
                
                # Extract all content
                text_chunks, all_images = self.extract_all_content_from_slide(slide, slide_index)
                
                # Create document chunk with ALL images
                chunk = DocumentChunk(
                    doc_id=doc_id,
                    unit="slide",
                    index=slide_index,
                    text_chunks=text_chunks,
                    images=all_images  # All images, no filtering
                )
                document_chunks.append(chunk)
                
                # Summary for this slide
                logger.info(f"   ✅ Text: {len(text_chunks)} chunks")
                logger.info(f"   ✅ Images: {len(all_images)} extracted")
            
            # Final summary
            total_images = sum(len(chunk.images) for chunk in document_chunks)
            
            logger.info(f"\n🎯 EXTRACTION COMPLETE:")
            logger.info(f"   Slides processed: {len(document_chunks)}")
            logger.info(f"   Total images extracted: {total_images}")
            logger.info(f"   All images saved to: {self.output_image_dir}")
            
            return document_chunks
            
        except Exception as e:
            logger.error(f"❌ Error parsing PPTX {file_path}: {e}")
            raise

    def save_pptx_extraction(self, chunks: List[DocumentChunk], output_dir: str, pptx_file: str):
        """Save extraction results"""
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(pptx_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create comprehensive data structure
        pptx_data = {
            "metadata": {
                "source_file": pptx_file,
                "file_type": "pptx",
                "extraction_time": timestamp,
                "total_slides": len(chunks),
                "total_text_chunks": sum(len(chunk.text_chunks) for chunk in chunks),
                "total_images": sum(len(chunk.images) for chunk in chunks)
            },
            "slides": []
        }
        
        for chunk in chunks:
            slide_data = {
                "slide_number": chunk.index,
                "text_chunks_count": len(chunk.text_chunks),
                "images_count": len(chunk.images),
                "text_chunks": chunk.text_chunks,
                "images": [
                    {
                        "path": img.path,
                        "filename": os.path.basename(img.path),
                        "caption": img.caption,
                        "bbox": img.bbox,
                        "image_type": img.image_type,
                        "metadata": img.metadata
                    }
                    for img in chunk.images
                ]
            }
            pptx_data["slides"].append(slide_data)
        
        # Save files
        output_filename = f"{base_name}_pptx_extraction_{timestamp}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pptx_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ PPTX extraction saved: {output_path}")
        return output_path

def main():
    """Test the advanced PPTX parser"""
    pptx_file = "presentation.pptx"  # Change to your file
    
    print("=== ADVANCED PPTX PARSER ===")
    
    # Parse with comprehensive extraction
    parser = AdvancedPPTXParser(output_image_dir="./pptx_images_complete")
    
    chunks = parser.parse_pptx(pptx_file, extract_all=True)
    output_path = parser.save_pptx_extraction(chunks, "./pptx_results", pptx_file)
    
    # Summary
    total_images = sum(len(chunk.images) for chunk in chunks)
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"   Total images extracted: {total_images}")
    print(f"   Results saved in: ./pptx_results/")

if __name__ == "__main__":
    main()