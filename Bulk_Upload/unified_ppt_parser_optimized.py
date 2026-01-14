# # unified_ppt_parser_optimized.py
# import os
# import json
# import base64
# import shutil
# import logging
# from typing import List, Optional, Dict, Any
# from datetime import datetime
# from pptx import Presentation
# from pptx.shapes.group import GroupShape
# from pydantic import BaseModel, Field
# from tqdm import tqdm
# from openai import OpenAI
# from dotenv import load_dotenv
# import tempfile

# # Load environment variables
# load_dotenv()

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(message)s')
# logger = logging.getLogger(__name__)

# # Data Models
# class DocumentUnit(BaseModel):
#     index: int
#     unit_type: str
#     text: List[str] = Field(default_factory=list)
#     images: List[str] = Field(default_factory=list)

# class DocumentOutput(BaseModel):
#     doc_id: str
#     doc_type: str
#     units: List[DocumentUnit] = Field(default_factory=list)

# class UnifiedOutput(BaseModel):
#     documents: List[DocumentOutput] = Field(default_factory=list)

# class ImageChunk(BaseModel):
#     path: str
#     caption: Optional[str] = None
#     bbox: Optional[List[float]] = None
#     metadata: Optional[Dict[str, Any]] = None
#     image_type: Optional[str] = None

# # Optimized PPTX Parser
# class OptimizedPPTXParser:
#     def __init__(self, output_base_dir: str = "./unified_output_optimized", user_id: str = "temp_user"):
#         self.output_base_dir = output_base_dir
#         self.user_id = user_id
        
#         # CHANGE THESE PATHS:
#         self.temp_images_dir = os.path.join(output_base_dir, "temp_images")
        
#         # NEW: Images go directly to final location
#         self.content_images_dir = f"images/{user_id}/main_corpus"  # ← FINAL LOCATION
        
#         self.removed_images_dir = os.path.join(output_base_dir, "removed_images")
#         self.json_output_dir = os.path.join(output_base_dir, "json")
        
#         # Create directories
#         os.makedirs(self.temp_images_dir, exist_ok=True)
#         os.makedirs(self.content_images_dir, exist_ok=True)  # Creates final location
#         os.makedirs(self.removed_images_dir, exist_ok=True)
#         os.makedirs(self.json_output_dir, exist_ok=True)
        
#         print(f"📁 Image storage: {self.content_images_dir}")  # Debug info
#         self.TINY_IMAGE_AREA = 200000  # ~0.24 square inches (very small)
        
#         # Initialize OpenAI client
#         if not os.getenv("OPENAI_API_KEY"):
#             raise ValueError("OPENAI_API_KEY not found in environment variables")
        
#         self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#         self.model = "gpt-4o"  # Using more accurate model

#         self.SLIDE_WIDTH = 12192000
#         self.SLIDE_HEIGHT = 6858000
#         self.EMU_PER_INCH = 914400

#     def emu_to_inches(self, emu: int) -> float:
#         return emu / self.EMU_PER_INCH

#     def get_all_shapes_recursive(self, shape) -> List[Any]:
#         shapes = []
#         try:
#             if hasattr(shape, 'shapes') and isinstance(shape, GroupShape):
#                 for child_shape in shape.shapes:
#                     shapes.extend(self.get_all_shapes_recursive(child_shape))
#             else:
#                 shapes.append(shape)
#         except Exception as e:
#             logger.debug(f"Error exploring shape: {e}")
#         return shapes

#     def extract_image_from_shape(self, shape, slide_index: int, image_counter: int) -> Optional[ImageChunk]:
#         try:
#             if not hasattr(shape, 'image') or not hasattr(shape.image, 'blob'):
#                 return None
                
#             if not shape.image.blob or len(shape.image.blob) < 1000:
#                 return None
            
#             width = getattr(shape, 'width', 0)
#             height = getattr(shape, 'height', 0)
#             left = getattr(shape, 'left', 0)
#             top = getattr(shape, 'top', 0)
            
#             ext = getattr(shape.image, 'ext', 'png').lower()
#             if ext not in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
#                 return None
            
#             # CHANGED: Save directly to FINAL location
#             filename = f"slide_{slide_index:03d}_img_{image_counter:03d}.{ext}"
#             image_path = os.path.join(self.content_images_dir, filename)  # ← FINAL LOCATION
            
#             # Ensure directory exists
#             os.makedirs(os.path.dirname(image_path), exist_ok=True)
            
#             with open(image_path, "wb") as f:
#                 f.write(shape.image.blob)
            
#             # Verify file was created
#             if os.path.exists(image_path):
#                 file_size = os.path.getsize(image_path)
#                 logger.info(f"  💾 EXTRACTED TO FINAL: {filename} ({file_size} bytes)")
#                 logger.info(f"     Location: {image_path}")
#             else:
#                 logger.error(f"  ❌ Failed to save: {image_path}")
#                 return None
            
#             return ImageChunk(
#                 path=image_path,  # ← This path points to FINAL location
#                 bbox=[left, top, left + width, top + height],
#                 metadata={
#                     'width': width,
#                     'height': height,
#                     'area': width * height,
#                     'width_inches': self.emu_to_inches(width),
#                     'height_inches': self.emu_to_inches(height),
#                     'left_inches': self.emu_to_inches(left),
#                     'top_inches': self.emu_to_inches(top),
#                     'shape_type': str(type(shape)),
#                     'is_placeholder': getattr(shape, 'is_placeholder', False),
#                     'extension': ext,
#                     'slide_index': slide_index,
#                     'image_counter': image_counter,
#                     'file_size': file_size,
#                     'extracted_to_final': True  # Flag to indicate direct extraction
#                 },
#                 image_type="extracted"
#             )
            
#         except Exception as e:
#             logger.warning(f"Error extracting image from shape: {e}")
#             return None

#     def extract_text_from_shape(self, shape) -> Optional[str]:
#         try:
#             if hasattr(shape, "text_frame") and shape.text_frame:
#                 text = shape.text_frame.text.strip()
#                 return text if text else None
#         except Exception as e:
#             logger.debug(f"Error extracting text from shape: {e}")
#         return None

#     def extract_all_content_from_slide(self, slide, slide_index: int) -> tuple:
#         text_chunks = []
#         all_images = []
#         image_counter = 0
        
#         all_shapes = []
#         for shape in slide.shapes:
#             all_shapes.extend(self.get_all_shapes_recursive(shape))
        
#         logger.info(f"Slide {slide_index}: Found {len(all_shapes)} total shapes")
        
#         for shape in all_shapes:
#             text = self.extract_text_from_shape(shape)
#             if text:
#                 text_chunks.append(text)
            
#             image = self.extract_image_from_shape(shape, slide_index, image_counter)
#             if image:
#                 all_images.append(image)
#                 image_counter += 1
                
#                 logger.info(f"  📸 Extracted: {os.path.basename(image.path)}")
        
#         return text_chunks, all_images

#     def is_tiny_logo(self, image_path: str, metadata: dict = None) -> bool:
#         """
#         Single heuristic: Filter out VERY tiny images (definitely logos/decorative)
#         """
#         if not metadata:
#             return False
        
#         area = metadata.get('area', 0)
        
#         # Very tiny images are definitely logos/decorative
#         if area < self.TINY_IMAGE_AREA:
#             logger.info(f"  📏 TINY LOGO: {os.path.basename(image_path)} ({area} EMU)")
#             return True
        
#         return False

#     def classify_image_with_llm(self, image_path: str) -> str:
#         """
#         Use your improved LLM prompt to classify images
#         """
#         try:
#             with open(image_path, "rb") as f:
#                 base64_image = base64.b64encode(f.read()).decode("utf-8")

#             prompt = """
#             Analyze this PNG image from a PowerPoint presentation. 
            
#             Is this valuable CONTENT/IMAGE that could be reused in another presentation?
#             Or is this a LOGO, DECORATIVE ELEMENT, IMAGE PLACEHOLDER, SHAPE or UI COMPONENT that should be removed?
            
#             CONTENT to KEEP (respond with 'keep'):
#             - Charts, graphs, diagrams, infographics
#             - Process flows, architectural diagrams
#             - Product images, technical illustrations  
#             - Data visualizations, maps
#             - High-quality photographs or complex illustrations, Screenshots of Screen
            
#             NON-CONTENT to REMOVE (respond with 'remove'):
#             - Logos, brand marks, watermarks, icons, Glyphs
#             - Image with a Transparent Background, GIF, SVG, PNG Images
#             - Decorative elements, borders, background patterns
#             - Person photos, headshots, team photos
#             - UI elements, buttons, form components
#             - Simple shapes, arrows, basic graphics
#             - Placeholder images, template graphics

#             Respond with ONLY one word: 'keep' or 'remove'
#             """

#             response = self.llm_client.chat.completions.create(
#                 model=self.model,
#                 messages=[{
#                     "role": "user",
#                     "content": [
#                         {"type": "text", "text": prompt},
#                         {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
#                     ]
#                 }],
#                 max_tokens=10,
#                 temperature=0.1
#             )
            
#             classification = response.choices[0].message.content.strip().lower()
#             return classification if classification in ['keep', 'remove'] else 'remove'
            
#         except Exception as e:
#             logger.error(f"LLM classification error for {os.path.basename(image_path)}: {e}")
#             return 'remove'  # Default to remove on error

#     def filter_images_optimized(self, images: List[ImageChunk]) -> List[str]:
#         """
#         Optimized strategy:
#         1. Keep ALL JPG/JPEG files automatically
#         2. Filter out VERY tiny images (definitely logos)
#         3. Use LLM on remaining non-JPG images
#         """
#         final_content_paths = []
        
#         logger.info(f"\n🎯 Optimized Image Filtering Started...")
        
#         # Separate images by type
#         jpg_images = [img for img in images if img.path.lower().endswith(('.jpg', '.jpeg'))]
#         other_images = [img for img in images if not img.path.lower().endswith(('.jpg', '.jpeg'))]
        
#         logger.info(f"   JPG/JPEG images: {len(jpg_images)} (AUTOMATICALLY KEPT)")
#         logger.info(f"   Other images: {len(other_images)} (FILTERED + LLM)")
        
#         # Step 1: Automatically keep ALL JPG/JPEG files
#         for jpg in jpg_images:
#             if os.path.exists(jpg.path):
#                 new_path = os.path.join(self.content_images_dir, os.path.basename(jpg.path))
#                 shutil.move(jpg.path, new_path)
#                 final_content_paths.append(new_path)
#                 logger.info(f"  ✅ JPG AUTOKEEP: {os.path.basename(jpg.path)}")
        
#         # Step 2: Apply size heuristic to other images
#         tiny_logos = []
#         remaining_other_images = []
        
#         for img in other_images:
#             if self.is_tiny_logo(img.path, img.metadata):
#                 tiny_logos.append(img)
#             else:
#                 remaining_other_images.append(img)
        
#         # Move tiny logos to removed folder
#         for logo in tiny_logos:
#             if os.path.exists(logo.path):
#                 new_path = os.path.join(self.removed_images_dir, os.path.basename(logo.path))
#                 shutil.move(logo.path, new_path)
#                 logger.info(f"  🪶 TINY LOGO REMOVED: {os.path.basename(logo.path)}")
        
#         # Step 3: Use LLM for remaining non-JPG images
#         if remaining_other_images:
#             logger.info(f"\n🔍 LLM Classifying {len(remaining_other_images)} remaining non-JPG images...")
            
#             for img in tqdm(remaining_other_images, desc="LLM classification"):
#                 if os.path.exists(img.path):
#                     classification = self.classify_image_with_llm(img.path)
                    
#                     if classification == 'keep':
#                         new_path = os.path.join(self.content_images_dir, os.path.basename(img.path))
#                         shutil.move(img.path, new_path)
#                         final_content_paths.append(new_path)
#                         logger.info(f"  ✅ LLM KEEP: {os.path.basename(img.path)}")
#                     else:
#                         new_path = os.path.join(self.removed_images_dir, os.path.basename(img.path))
#                         shutil.move(img.path, new_path)
#                         logger.info(f"  ❌ LLM REMOVE: {os.path.basename(img.path)}")
        
#         # Clean up temp folder
#         try:
#             if not os.listdir(self.temp_images_dir):
#                 os.rmdir(self.temp_images_dir)
#         except:
#             pass
        
#         # Final statistics
#         total_jpg = len(jpg_images)
#         total_tiny_removed = len(tiny_logos)
#         total_other_kept = len([p for p in final_content_paths if not p.lower().endswith(('.jpg', '.jpeg'))])
#         total_other_removed = len(remaining_other_images) - total_other_kept
        
#         logger.info(f"\n📊 FILTERING RESULTS:")
#         logger.info(f"   JPG/JPEG kept: {total_jpg} (100%)")
#         logger.info(f"   Tiny logos removed: {total_tiny_removed}")
#         logger.info(f"   Other images kept: {total_other_kept}")
#         logger.info(f"   Other images removed: {total_other_removed}")
#         logger.info(f"   Total content images: {len(final_content_paths)}")
#         logger.info(f"   LLM cost savings: {total_tiny_removed} images skipped")
        
#         return final_content_paths

#     def parse_pptx_file(self, file_path: str, doc_id: Optional[str] = None) -> DocumentOutput:
#         if not os.path.exists(file_path):
#             raise FileNotFoundError(f"PPTX file not found: {file_path}")
        
#         if doc_id is None:
#             doc_id = os.path.splitext(os.path.basename(file_path))[0]
        
#         logger.info(f"\n{'='*60}")
#         logger.info(f"📂 PROCESSING: {os.path.basename(file_path)}")
#         logger.info(f"🎯 STRATEGY: Keep ALL JPG + Size filter + LLM for rest")
#         logger.info(f"{'='*60}")
        
#         try:
#             presentation = Presentation(file_path)
#             document_units = []
#             all_extracted_images = []
            
#             # Extract all content
#             for slide_index, slide in enumerate(presentation.slides):
#                 logger.info(f"\n📊 Slide {slide_index}: Extracting content...")
                
#                 text_chunks, images = self.extract_all_content_from_slide(slide, slide_index)
#                 all_extracted_images.extend(images)
                
#                 document_units.append({
#                     'index': slide_index,
#                     'text_chunks': text_chunks,
#                     'all_images': images
#                 })
                
#                 logger.info(f"   ✅ Text: {len(text_chunks)} chunks")
#                 logger.info(f"   ✅ Images: {len(images)} extracted")
            
#             # Apply optimized filtering
#             logger.info(f"\n🎯 Applying Optimized Filtering...")
#             logger.info(f"   Total images extracted: {len(all_extracted_images)}")
            
#             final_content_paths = self.filter_images_optimized(all_extracted_images)
            
#             # Create final document units
#             final_units = []
#             for unit_data in document_units:
#                 # Match original images with final content paths
#                 slide_content_images = []
#                 for img in unit_data['all_images']:
#                     final_path = os.path.join(self.content_images_dir, os.path.basename(img.path))
#                     if final_path in final_content_paths:
#                         slide_content_images.append(final_path)
                
#                 final_units.append(DocumentUnit(
#                     index=unit_data['index'],
#                     unit_type="slide",
#                     text=unit_data['text_chunks'],
#                     images=slide_content_images
#                 ))
            
#             # Final summary
#             total_jpg = len([p for p in final_content_paths if p.lower().endswith(('.jpg', '.jpeg'))])
#             total_other = len([p for p in final_content_paths if not p.lower().endswith(('.jpg', '.jpeg'))])
            
#             logger.info(f"\n🎯 EXTRACTION COMPLETE: {os.path.basename(file_path)}")
#             logger.info(f"   Slides processed: {len(document_units)}")
#             logger.info(f"   Final content images: {len(final_content_paths)}")
#             logger.info(f"   → JPG/JPEG content: {total_jpg}")
#             logger.info(f"   → Other content: {total_other}")
#             logger.info(f"   Content folder: {self.content_images_dir}")
            
#             return DocumentOutput(
#                 doc_id=doc_id,
#                 doc_type="pptx",
#                 units=final_units
#             )
            
#         except Exception as e:
#             logger.error(f"❌ Error parsing PPTX {file_path}: {e}")
#             raise

#     def parse_ppt_folder(self, folder_path: str, output_filename: str = "unified_ppt_documents.json") -> str:
#         supported_extensions = {'.pptx'}
#         documents = []
        
#         logger.info(f"📁 PROCESSING FOLDER: {folder_path}")
        
#         pptx_files = []
#         for filename in os.listdir(folder_path):
#             file_path = os.path.join(folder_path, filename)
#             if os.path.isfile(file_path):
#                 file_ext = os.path.splitext(filename)[1].lower()
#                 if file_ext in supported_extensions:
#                     pptx_files.append(file_path)
        
#         logger.info(f"📄 Found {len(pptx_files)} PPTX files to process")
        
#         for file_path in pptx_files:
#             try:
#                 doc_output = self.parse_pptx_file(file_path)
#                 documents.append(doc_output.model_dump())
#                 logger.info(f"✅ Completed: {os.path.basename(file_path)}")
#             except Exception as e:
#                 logger.error(f"❌ Failed to parse {os.path.basename(file_path)}: {e}")
#                 continue
        
#         unified_output = UnifiedOutput(documents=documents)
#         output_path = os.path.join(self.json_output_dir, output_filename)
        
#         with open(output_path, 'w', encoding='utf-8') as f:
#             json.dump(unified_output.model_dump(), f, indent=2, ensure_ascii=False)
        
#         # Count final images
#         content_files = os.listdir(self.content_images_dir)
#         jpg_count = len([f for f in content_files if f.lower().endswith(('.jpg', '.jpeg'))])
#         other_count = len([f for f in content_files if not f.lower().endswith(('.jpg', '.jpeg'))])
        
#         logger.info(f"\n🎯 FOLDER PROCESSING COMPLETE!")
#         logger.info(f"   Documents processed: {len(documents)}")
#         logger.info(f"   Final content images: {len(content_files)}")
#         logger.info(f"   → JPG/JPEG: {jpg_count}")
#         logger.info(f"   → Other formats: {other_count}")
#         logger.info(f"   Content folder: {self.content_images_dir} ← YOUR CLEAN IMAGES")
#         logger.info(f"   Removed folder: {self.removed_images_dir}")
#         logger.info(f"   JSON output: {output_path}")
        
#         return output_path

# def main():
#     parser = OptimizedPPTXParser(output_base_dir="./unified_output_optimized")
    
#     # Process all PPTX files in a folder
#     folder_path = "which_ppt"  # Change to your folder path
#     unified_output = parser.parse_ppt_folder(folder_path)
    
#     print(f"\n✅ Processing complete!")
#     print(f"📁 Your clean images are in: ./unified_output_optimized/content_images/")
#     print(f"🗑️  Removed images are in: ./unified_output_optimized/removed_images/")
#     print(f"📊 Data file: {unified_output}")

# if __name__ == "__main__":
#     main()






# unified_ppt_parser_optimized.py
import os
import json
import base64
import shutil
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pptx import Presentation
from pptx.shapes.group import GroupShape
from pydantic import BaseModel, Field
from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Data Models
class DocumentUnit(BaseModel):
    index: int
    unit_type: str
    text: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)

class DocumentOutput(BaseModel):
    doc_id: str
    doc_type: str
    units: List[DocumentUnit] = Field(default_factory=list)

class UnifiedOutput(BaseModel):
    documents: List[DocumentOutput] = Field(default_factory=list)

class ImageChunk(BaseModel):
    path: str
    caption: Optional[str] = None
    bbox: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    image_type: Optional[str] = None

# Optimized PPTX Parser
class OptimizedPPTXParser:
# AFTER (accept user_id as parameter):
    def __init__(self, output_base_dir: str = "./unified_output_optimized", user_id: str = None):
        self.output_base_dir = output_base_dir
        
        # Accept dynamic user_id, default to test-email@gmail.com for backward compatibility
        self.user_id = user_id or "test-email@gmail.com"
        self.temp_images_dir = os.path.join(output_base_dir, "temp_images")
        
        # CHANGED: Direct to main_corpus for all processing - using dynamic user_id
        self.content_images_dir = f"images/{self.user_id}/main_corpus"
        self.removed_images_dir = os.path.join(output_base_dir, "removed_images")
        self.json_output_dir = os.path.join(output_base_dir, "json")
        
        # Create output directories
        os.makedirs(self.temp_images_dir, exist_ok=True)
        os.makedirs(self.content_images_dir, exist_ok=True)  # Main corpus for everything
        os.makedirs(self.removed_images_dir, exist_ok=True)
        os.makedirs(self.json_output_dir, exist_ok=True)
        
        # Size threshold for tiny images (definitely logos)
        self.TINY_IMAGE_AREA = 200000  # ~0.24 square inches (very small)
        
        # Initialize OpenAI client
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"  # Using more accurate model

        self.SLIDE_WIDTH = 12192000
        self.SLIDE_HEIGHT = 6858000
        self.EMU_PER_INCH = 914400

        logger.info(f"🔧 Parser configured for user: {self.user_id}")
        logger.info(f"🔧 All images will be processed in: {self.content_images_dir}")

    def emu_to_inches(self, emu: int) -> float:
        return emu / self.EMU_PER_INCH

    def get_all_shapes_recursive(self, shape) -> List[Any]:
        shapes = []
        try:
            if hasattr(shape, 'shapes') and isinstance(shape, GroupShape):
                for child_shape in shape.shapes:
                    shapes.extend(self.get_all_shapes_recursive(child_shape))
            else:
                shapes.append(shape)
        except Exception as e:
            logger.debug(f"Error exploring shape: {e}")
        return shapes

    def extract_image_from_shape(self, shape, slide_index: int, image_counter: int) -> Optional[ImageChunk]:
        """Extract image and save directly to main_corpus"""
        try:
            if not hasattr(shape, 'image') or not hasattr(shape.image, 'blob'):
                return None
                
            if not shape.image.blob or len(shape.image.blob) < 1000:
                return None
            
            width = getattr(shape, 'width', 0)
            height = getattr(shape, 'height', 0)
            left = getattr(shape, 'left', 0)
            top = getattr(shape, 'top', 0)
            
            ext = getattr(shape.image, 'ext', 'png').lower()
            if ext not in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                return None
            
            # Save DIRECTLY to main_corpus
            # filename = f"slide_{slide_index:03d}_img_{image_counter:03d}.{ext}"
            import uuid
            filename = f"slide_{slide_index:03d}_img_{image_counter:03d}_{uuid.uuid4().hex[:6]}.{ext}"

            image_path = os.path.join(self.content_images_dir, filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            
            with open(image_path, "wb") as f:
                f.write(shape.image.blob)
            
            # Verify the file was created
            if not os.path.exists(image_path):
                logger.warning(f"Failed to save image: {image_path}")
                return None
                
            file_size = os.path.getsize(image_path)
            logger.info(f"  💾 Saved to main_corpus: {filename} ({file_size} bytes)")
            
            return ImageChunk(
                path=image_path,
                bbox=[left, top, left + width, top + height],
                metadata={
                    'width': width,
                    'height': height,
                    'area': width * height,
                    'width_inches': self.emu_to_inches(width),
                    'height_inches': self.emu_to_inches(height),
                    'left_inches': self.emu_to_inches(left),
                    'top_inches': self.emu_to_inches(top),
                    'shape_type': str(type(shape)),
                    'is_placeholder': getattr(shape, 'is_placeholder', False),
                    'extension': ext,
                    'slide_index': slide_index,
                    'image_counter': image_counter,
                    'file_size': file_size,
                    'location': 'main_corpus'
                },
                image_type="extracted"
            )
            
        except Exception as e:
            logger.warning(f"Error extracting image from shape: {e}")
            return None

    def extract_text_from_shape(self, shape) -> Optional[str]:
        try:
            if hasattr(shape, "text_frame") and shape.text_frame:
                text = shape.text_frame.text.strip()
                return text if text else None
        except Exception as e:
            logger.debug(f"Error extracting text from shape: {e}")
        return None

    def extract_all_content_from_slide(self, slide, slide_index: int) -> tuple:
        text_chunks = []
        all_images = []
        image_counter = 0
        
        all_shapes = []
        for shape in slide.shapes:
            all_shapes.extend(self.get_all_shapes_recursive(shape))
        
        logger.info(f"Slide {slide_index}: Found {len(all_shapes)} total shapes")
        
        for shape in all_shapes:
            text = self.extract_text_from_shape(shape)
            if text:
                text_chunks.append(text)
            
            image = self.extract_image_from_shape(shape, slide_index, image_counter)
            if image:
                all_images.append(image)
                image_counter += 1
                
                logger.info(f"  📸 Extracted to main_corpus: {os.path.basename(image.path)}")
        
        return text_chunks, all_images

    def is_tiny_logo(self, image_path: str, metadata: dict = None) -> bool:
        """
        Single heuristic: Filter out VERY tiny images (definitely logos/decorative)
        """
        if not metadata:
            return False
        
        area = metadata.get('area', 0)
        
        # Very tiny images are definitely logos/decorative
        if area < self.TINY_IMAGE_AREA:
            logger.info(f"  📏 TINY LOGO: {os.path.basename(image_path)} ({area} EMU)")
            return True
        
        return False

    def classify_image_with_llm(self, image_path: str) -> str:
        """
        Use your improved LLM prompt to classify images
        """
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")

            prompt = """
            Analyze this PNG image from a PowerPoint presentation. 
            
            Is this valuable CONTENT/IMAGE that could be reused in another presentation?
            Or is this a LOGO, DECORATIVE ELEMENT, IMAGE PLACEHOLDER, SHAPE or UI COMPONENT that should be removed?
            
            CONTENT to KEEP (respond with 'keep'):
            - Charts, graphs, diagrams, infographics
            - Process flows, architectural diagrams
            - Product images, technical illustrations  
            - Data visualizations, maps
            - High-quality photographs or complex illustrations, Screenshots of Screen
            
            NON-CONTENT to REMOVE (respond with 'remove'):
            - Logos, brand marks, watermarks, icons, Glyphs, Letters
            - Image with a Transparent Background, GIF, SVG, PNG Images
            - Decorative elements, borders, background patterns
            - Person photos, headshots, team photos
            - UI elements, buttons, form components
            - Simple shapes, arrows, basic graphics
            - Placeholder images, template graphics

            Respond with ONLY one word: 'keep' or 'remove'
            """

            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                max_tokens=10,
                temperature=0.1
            )
            
            classification = response.choices[0].message.content.strip().lower()
            return classification if classification in ['keep', 'remove'] else 'remove'
            
        except Exception as e:
            logger.error(f"LLM classification error for {os.path.basename(image_path)}: {e}")
            return 'remove'  # Default to remove on error

    def filter_images_optimized(self, images: List[ImageChunk]) -> List[str]:
        """
        Filter images that are already in main_corpus
        """
        final_content_paths = []
        
        logger.info(f"\n🎯 Filtering images in main_corpus...")
        
        # Separate images by type
        jpg_images = [img for img in images if img.path.lower().endswith(('.jpg', '.jpeg'))]
        other_images = [img for img in images if not img.path.lower().endswith(('.jpg', '.jpeg'))]
        
        logger.info(f"   JPG/JPEG images: {len(jpg_images)} (AUTOMATICALLY KEPT)")
        logger.info(f"   Other images: {len(other_images)} (FILTERED + LLM)")
        
        # Step 1: Automatically keep ALL JPG/JPEG files in main_corpus
        for jpg in jpg_images:
            if os.path.exists(jpg.path):
                final_content_paths.append(jpg.path)
                logger.info(f"  ✅ JPG AUTOKEEP: {os.path.basename(jpg.path)}")
        
        # Step 2: Apply size heuristic to other images in main_corpus
        tiny_logos = []
        remaining_other_images = []
        
        for img in other_images:
            if self.is_tiny_logo(img.path, img.metadata):
                tiny_logos.append(img)
            else:
                remaining_other_images.append(img)
        
        # Remove tiny logos from main_corpus
        for logo in tiny_logos:
            if os.path.exists(logo.path):
                os.remove(logo.path)
                logger.info(f"  🪶 TINY LOGO REMOVED from main_corpus: {os.path.basename(logo.path)}")
        
        # Step 3: Use LLM for remaining non-JPG images in main_corpus
        if remaining_other_images:
            logger.info(f"\n🔍 LLM Classifying {len(remaining_other_images)} remaining non-JPG images in main_corpus...")
            
            for img in tqdm(remaining_other_images, desc="LLM classification"):
                if os.path.exists(img.path):
                    classification = self.classify_image_with_llm(img.path)
                    
                    if classification == 'keep':
                        final_content_paths.append(img.path)
                        logger.info(f"  ✅ LLM KEEP in main_corpus: {os.path.basename(img.path)}")
                    else:
                        os.remove(img.path)
                        logger.info(f"  ❌ LLM REMOVE from main_corpus: {os.path.basename(img.path)}")
        
        # Clean up temp folder
        try:
            if os.path.exists(self.temp_images_dir):
                shutil.rmtree(self.temp_images_dir)
        except:
            pass
        
        # Final statistics
        total_jpg = len(jpg_images)
        total_tiny_removed = len(tiny_logos)
        total_other_kept = len([p for p in final_content_paths if not p.lower().endswith(('.jpg', '.jpeg'))])
        total_other_removed = len(remaining_other_images) - total_other_kept
        
        logger.info(f"\n📊 FILTERING RESULTS (main_corpus):")
        logger.info(f"   JPG/JPEG kept: {total_jpg} (100%)")
        logger.info(f"   Tiny logos removed: {total_tiny_removed}")
        logger.info(f"   Other images kept: {total_other_kept}")
        logger.info(f"   Other images removed: {total_other_removed}")
        logger.info(f"   Total content images in main_corpus: {len(final_content_paths)}")
        
        return final_content_paths

    def parse_pptx_file(self, file_path: str, doc_id: Optional[str] = None) -> DocumentOutput:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PPTX file not found: {file_path}")
        
        if doc_id is None:
            doc_id = os.path.splitext(os.path.basename(file_path))[0]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📂 PROCESSING: {os.path.basename(file_path)}")
        logger.info(f"🎯 STRATEGY: All images processed in main_corpus")
        logger.info(f"👤 USER: {self.user_id}")
        logger.info(f"{'='*60}")
        
        try:
            presentation = Presentation(file_path)
            document_units = []
            all_extracted_images = []
            
            # Extract all content
            for slide_index, slide in enumerate(presentation.slides):
                logger.info(f"\n📊 Slide {slide_index}: Extracting content to main_corpus...")
                
                text_chunks, images = self.extract_all_content_from_slide(slide, slide_index)
                all_extracted_images.extend(images)
                
                document_units.append({
                    'index': slide_index,
                    'text_chunks': text_chunks,
                    'all_images': images
                })
                
                logger.info(f"   ✅ Text: {len(text_chunks)} chunks")
                logger.info(f"   ✅ Images: {len(images)} extracted to main_corpus")
            
            # Apply optimized filtering (images are already in main_corpus)
            logger.info(f"\n🎯 Applying Filtering in main_corpus...")
            logger.info(f"   Total images extracted to main_corpus: {len(all_extracted_images)}")
            
            final_content_paths = self.filter_images_optimized(all_extracted_images)
            
            # Create final document units
            final_units = []
            for unit_data in document_units:
                # Match original images with final content paths
                slide_content_images = []
                for img in unit_data['all_images']:
                    if img.path in final_content_paths:
                        slide_content_images.append(img.path)
                
                final_units.append(DocumentUnit(
                    index=unit_data['index'],
                    unit_type="slide",
                    text=unit_data['text_chunks'],
                    images=slide_content_images
                ))
            
            # Final summary
            total_jpg = len([p for p in final_content_paths if p.lower().endswith(('.jpg', '.jpeg'))])
            total_other = len([p for p in final_content_paths if not p.lower().endswith(('.jpg', '.jpeg'))])
            
            logger.info(f"\n🎯 EXTRACTION COMPLETE: {os.path.basename(file_path)}")
            logger.info(f"   Slides processed: {len(document_units)}")
            logger.info(f"   Final content images in main_corpus: {len(final_content_paths)}")
            logger.info(f"   → JPG/JPEG content: {total_jpg}")
            logger.info(f"   → Other content: {total_other}")
            logger.info(f"   Main corpus location: {self.content_images_dir}")
            
            return DocumentOutput(
                doc_id=doc_id,
                doc_type="pptx",
                units=final_units
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing PPTX {file_path}: {e}")
            raise

    def parse_ppt_folder(self, folder_path: str, output_filename: str = "unified_ppt_documents.json") -> str:
        supported_extensions = {'.pptx'}
        documents = []
        
        logger.info(f"📁 PROCESSING FOLDER: {folder_path}")
        logger.info(f"👤 USER: {self.user_id}")
        logger.info(f"📁 MAIN_CORPUS: {self.content_images_dir}")
        
        # CHANGED: Recursively search for PPTX files
        pptx_files = []
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                if filename.lower().endswith('.pptx'):
                    file_path = os.path.join(root, filename)
                    pptx_files.append(file_path)
                    logger.info(f"📄 Found: {filename} in {root}")
        
        logger.info(f"📄 Found {len(pptx_files)} PPTX files to process")
        
        if len(pptx_files) == 0:
            logger.warning(f"⚠️ No PPTX files found in {folder_path} or its subdirectories!")
            logger.warning(f"   Looking for files with .pptx extension")
            # List all files for debugging
            all_files = []
            for root, dirs, files in os.walk(folder_path):
                for filename in files:
                    all_files.append(os.path.join(root, filename))
            logger.warning(f"   All files found: {all_files}")
        
        for file_path in pptx_files:
            try:
                doc_output = self.parse_pptx_file(file_path)
                documents.append(doc_output.model_dump())
                logger.info(f"✅ Completed: {os.path.basename(file_path)}")
            except Exception as e:
                logger.error(f"❌ Failed to parse {os.path.basename(file_path)}: {e}")
                continue
        
        unified_output = UnifiedOutput(documents=documents)
        output_path = os.path.join(self.json_output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(unified_output.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Count final images in main_corpus
        if os.path.exists(self.content_images_dir):
            content_files = os.listdir(self.content_images_dir)
            jpg_count = len([f for f in content_files if f.lower().endswith(('.jpg', '.jpeg'))])
            other_count = len([f for f in content_files if not f.lower().endswith(('.jpg', '.jpeg'))])
            
            logger.info(f"\n🎯 FOLDER PROCESSING COMPLETE!")
            logger.info(f"   User: {self.user_id}")
            logger.info(f"   Documents processed: {len(documents)}")
            logger.info(f"   Final content images in main_corpus: {len(content_files)}")
            logger.info(f"   → JPG/JPEG: {jpg_count}")
            logger.info(f"   → Other formats: {other_count}")
            logger.info(f"   Main corpus: {self.content_images_dir} ← ALL FINAL IMAGES HERE")
            logger.info(f"   JSON output: {output_path}")
        
        return output_path

    # def parse_ppt_folder(self, folder_path: str, output_filename: str = "unified_ppt_documents.json") -> str:
    #     supported_extensions = {'.pptx'}
    #     documents = []
        
    #     logger.info(f"📁 PROCESSING FOLDER: {folder_path}")
    #     logger.info(f"👤 USER: {self.user_id}")
    #     logger.info(f"📁 MAIN_CORPUS: {self.content_images_dir}")
        
    #     pptx_files = []
    #     for filename in os.listdir(folder_path):
    #         file_path = os.path.join(folder_path, filename)
    #         if os.path.isfile(file_path):
    #             file_ext = os.path.splitext(filename)[1].lower()
    #             if file_ext in supported_extensions:
    #                 pptx_files.append(file_path)
        
    #     logger.info(f"📄 Found {len(pptx_files)} PPTX files to process")
        
    #     for file_path in pptx_files:
    #         try:
    #             doc_output = self.parse_pptx_file(file_path)
    #             documents.append(doc_output.model_dump())
    #             logger.info(f"✅ Completed: {os.path.basename(file_path)}")
    #         except Exception as e:
    #             logger.error(f"❌ Failed to parse {os.path.basename(file_path)}: {e}")
    #             continue
        
    #     unified_output = UnifiedOutput(documents=documents)
    #     output_path = os.path.join(self.json_output_dir, output_filename)
        
    #     with open(output_path, 'w', encoding='utf-8') as f:
    #         json.dump(unified_output.model_dump(), f, indent=2, ensure_ascii=False)
        
    #     # Count final images in main_corpus
    #     if os.path.exists(self.content_images_dir):
    #         content_files = os.listdir(self.content_images_dir)
    #         jpg_count = len([f for f in content_files if f.lower().endswith(('.jpg', '.jpeg'))])
    #         other_count = len([f for f in content_files if not f.lower().endswith(('.jpg', '.jpeg'))])
            
    #         logger.info(f"\n🎯 FOLDER PROCESSING COMPLETE!")
    #         logger.info(f"   User: {self.user_id}")
    #         logger.info(f"   Documents processed: {len(documents)}")
    #         logger.info(f"   Final content images in main_corpus: {len(content_files)}")
    #         logger.info(f"   → JPG/JPEG: {jpg_count}")
    #         logger.info(f"   → Other formats: {other_count}")
    #         logger.info(f"   Main corpus: {self.content_images_dir} ← ALL FINAL IMAGES HERE")
    #         logger.info(f"   JSON output: {output_path}")
        
    #     return output_path

def main():
    parser = OptimizedPPTXParser(output_base_dir="./unified_output_optimized")
    
    # Process all PPTX files in a folder
    folder_path = "which_ppt"  # Change to your folder path
    unified_output = parser.parse_ppt_folder(folder_path)
    
    print(f"\n✅ Processing complete!")
    print(f"📁 All images are in: images/test-email@gmail.com/main_corpus/")
    print(f"👤 User: test-email@gmail.com")
    print(f"📊 Data file: {unified_output}")

if __name__ == "__main__":
    main()