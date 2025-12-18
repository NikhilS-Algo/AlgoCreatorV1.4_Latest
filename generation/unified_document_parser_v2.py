# unified_document_parser_v2.py
import os
import json
import base64
import shutil
import logging
import asyncio
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import time
import uuid
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

# Import the individual parsers
from pptx_parser_advanced import AdvancedPPTXParser
from pdf_parser_complete import PDFParser
from docx_parser_complete import DOCXParser
from txt_parser_complete import TXTParser

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Data Models (Same as original)
class DocumentUnit(BaseModel):
    index: int
    unit_type: str  # "slide", "page", "section", "paragraph"
    text: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)  # Just image paths

class DocumentOutput(BaseModel):
    doc_id: str
    doc_type: str  # "pptx", "pdf", "docx", "txt"
    units: List[DocumentUnit] = Field(default_factory=list)

class UnifiedOutput(BaseModel):
    documents: List[DocumentOutput] = Field(default_factory=list)

class ImageChunk(BaseModel):
    path: str
    caption: Optional[str] = None
    bbox: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    image_type: Optional[str] = None

class UnifiedDocumentParserV2:
    """
    Optimized unified parser with mode-dependent image storage
    """
    
    def __init__(self, output_base_dir: str = "./unified_output", user_id: str = "default", session_id: str = "default_session"):
        self.output_base_dir = output_base_dir
        self.user_id = user_id
        self.session_id = session_id
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create image directories with same structure as original
        self.image_main_dir = os.path.join("images", user_id, "main_corpus")
        self.image_temp_dir = os.path.join("images", user_id, "temp_uploads", session_id)
        os.makedirs(self.image_main_dir, exist_ok=True)
        os.makedirs(self.image_temp_dir, exist_ok=True)
        
        # JSON output directory (same as original)
        self.json_output_dir = os.path.join("processed_json", user_id)
        os.makedirs(self.json_output_dir, exist_ok=True)
        
        # Initialize OpenAI client
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"  # Using more accurate model
        
        # Initialize individual parsers with optimized filtering
        self.pptx_parser = AdvancedPPTXParser(
            output_image_dir=self.image_temp_dir,
            user_id=user_id,
            session_id=session_id
        )
        self.pdf_parser = PDFParser(
            output_image_dir=self.image_temp_dir,
            user_id=user_id,
            session_id=session_id
        )
        self.docx_parser = DOCXParser(
            output_image_dir=self.image_temp_dir,
            user_id=user_id,
            session_id=session_id
        )
        self.txt_parser = TXTParser()
        
        # 🆕 OPTIMIZED Batch processing settings
        self.batch_size = 3  # Increased from 3
        self.delay_between_batches = 0.5  # Reduced from 2 seconds
        
        # 🆕 Timing metrics
        self.total_llm_time = 0
        self.total_images_processed = 0
        self.llm_cache = {}  # Cache for identical images
        
        logger.info(f"🚀 OPTIMIZED Unified Parser initialized for user: {user_id}")
        logger.info(f"🔧 LLM Model: {self.model}")
        logger.info(f"⚡ Batch Size: {self.batch_size}, Delay: {self.delay_between_batches}s")

    def _generate_unique_image_name(self, doc_id: str, unit_index: int, image_index: int, ext: str) -> str:
        """Generate unique image filename (same logic as original but with extension)"""
        doc_hash = hashlib.md5(doc_id.encode()).hexdigest()[:8]
        unique_id = uuid.uuid4().hex[:6]  # Add unique ID to prevent collisions
        return f"img_{self.user_id}_{self.session_id}_{doc_hash}_unit{unit_index}_img{image_index}_{unique_id}.{ext}"

    def _store_image_with_relative_path(self, image_path: str, doc_id: str, unit_index: int, image_index: int, mode: str = "uploaded_only") -> str:
        """
        Store image based on mode and return RELATIVE path
        """
        if not os.path.exists(image_path):
            return ""
            
        # Get file extension
        ext = os.path.splitext(image_path)[1].lower().replace('.', '')
        if not ext:
            ext = 'png'  # default
            
        # Generate unique name
        unique_name = self._generate_unique_image_name(doc_id, unit_index, image_index, ext)
        
        if mode == "uploaded_only":
            # Store in temp_uploads for current session only
            session_temp_dir = self.image_temp_dir  # Already includes session_id in path
            os.makedirs(session_temp_dir, exist_ok=True)
            
            temp_absolute_path = os.path.join(session_temp_dir, unique_name)
            shutil.copy2(image_path, temp_absolute_path)
            
            # Return RELATIVE path that points to temp_uploads/session_id
            relative_path = f"images/{self.user_id}/temp_uploads/{self.session_id}/{unique_name}"
            
        else:  # corpus_only or uploaded_plus_corpus
            # Store in main_corpus (permanent location)
            main_absolute_path = os.path.join(self.image_main_dir, unique_name)
            shutil.copy2(image_path, main_absolute_path)
            
            # Return RELATIVE path that points to main_corpus
            relative_path = f"images/{self.user_id}/main_corpus/{unique_name}"
        
        logger.info(f"💾 Stored image ({mode}): {unique_name}")
        return relative_path

    def _is_tiny_logo(self, image: ImageChunk, doc_type: str = "unknown") -> bool:
        """Check if image is definitely a tiny logo - with format-specific thresholds"""
        
        # DISABLE tiny filtering for PDF and DOCX entirely - KEEP ALL IMAGES
        if doc_type in ['pdf', 'docx']:
            return False  # Keep ALL PDF and DOCX images regardless of size
        
        metadata = image.metadata or {}
        area = metadata.get('area', 0)
        width = metadata.get('width', 0)
        height = metadata.get('height', 0)
        
        # Only apply filtering to PPTX files
        if doc_type == 'pptx':
            # PPTX uses EMU units
            tiny_threshold = 200000  # EMU
            size_type = "EMU"
            
            # Very tiny images are definitely logos/decorative
            if area > 0 and area < tiny_threshold:
                logger.info(f"  📏 TINY PPTX LOGO: {os.path.basename(image.path)} {width}x{height} ({area} {size_type})")
                return True
            
            # Check dimensions for very small PPTX images
            if width > 0 and height > 0 and (width < 100000 or height < 100000):
                logger.info(f"  📏 TINY PPTX DIMENSIONS: {os.path.basename(image.path)} {width}x{height}")
                return True
        
        return False

    def _optimize_image_for_llm(self, image_path: str) -> str:
        """Resize and compress image for faster API calls"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')
                
                original_size = img.size
                max_dimension = 1024  # Optimal size for GPT-4V
                
                # Resize if too large
                if max(original_size) > max_dimension:
                    ratio = max_dimension / max(original_size)
                    new_size = (int(original_size[0] * ratio), int(original_size[1] * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                else:
                    new_size = original_size
                
                # Save optimized version
                temp_path = image_path.replace('.png', '_optimized.jpg').replace('.jpeg', '_optimized.jpg')
                img.save(temp_path, 'JPEG', quality=85, optimize=True)
                
                original_kb = os.path.getsize(image_path) / 1024
                optimized_kb = os.path.getsize(temp_path) / 1024
                
                if optimized_kb < original_kb:
                    logger.info(f"🔄 Optimized: {original_size} → {new_size} | {original_kb:.1f}KB → {optimized_kb:.1f}KB")
                    return temp_path
                
            return image_path
        except Exception as e:
            logger.warning(f"Image optimization failed: {e}")
            return image_path

    # def classify_image_with_llm(self, image_path: str) -> str:d
    #     """Use LLM to classify images with optimization and timing"""
    #     # 🆕 CHECK CACHE FIRST
    #     image_hash = hashlib.md5(open(image_path, 'rb').read()).hexdigest()
    #     if image_hash in self.llm_cache:
    #         logger.info(f"  🔄 CACHED RESULT: {os.path.basename(image_path)}")
    #         return self.llm_cache[image_hash]
        
    #     start_time = time.time()
    #     optimized_path = image_path
    #     use_optimized = False
        
    #     try:
    #         # 🆕 OPTIMIZE IMAGE FIRST
    #         optimized_path = self._optimize_image_for_llm(image_path)
    #         use_optimized = optimized_path != image_path
            
    #         with open(optimized_path, "rb") as f:
    #             base64_image = base64.b64encode(f.read()).decode("utf-8")

    #         prompt = """
    #         Analyze this image from a document. 
            
    #         Is this valuable CONTENT/IMAGE that could be reused in another presentation?
    #         Or is this a LOGO, DECORATIVE ELEMENT, IMAGE PLACEHOLDER, SHAPE or UI COMPONENT that should be removed?
            
    #         CONTENT to KEEP (respond with 'keep'):
    #         - Charts, graphs, diagrams, infographics
    #         - Process flows, architectural diagrams
    #         - Product images, technical illustrations  
    #         - Data visualizations, maps
    #         - High-quality photographs or complex illustrations, Screenshots of Screen
            
    #         NON-CONTENT to REMOVE (respond with 'remove'):
    #         - Logos, brand marks, watermarks, icons, Glyphs, Letters
    #         - Image with a Transparent Background, GIF, SVG, PNG Images
    #         - Decorative elements, borders, background patterns
    #         - Person photos, headshots, team photos, person faces in photos
    #         - UI elements, buttons, form components
    #         - Simple shapes, arrows, basic graphics
    #         - Placeholder images, template graphics

    #         Respond with ONLY one word: 'keep' or 'remove'
    #         """

    #         response = self.llm_client.chat.completions.create(
    #             model=self.model,
    #             messages=[{
    #                 "role": "user",
    #                 "content": [
    #                     {"type": "text", "text": prompt},
    #                     {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
    #                 ]
    #             }],
    #             max_tokens=10,
    #             temperature=0.1
    #         )
            
    #         classification = response.choices[0].message.content.strip().lower()
    #         final_classification = classification if classification in ['keep', 'remove'] else 'remove'
            
    #         # 🆕 STORE IN CACHE
    #         self.llm_cache[image_hash] = final_classification
            
    #         # 🆕 TIMING METRICS
    #         llm_time = time.time() - start_time
    #         self.total_llm_time += llm_time
    #         self.total_images_processed += 1
            
    #         logger.info(f"⏱️ LLM Time: {llm_time:.2f}s - {os.path.basename(image_path)}")
            
    #         return final_classification
            
    #     except Exception as e:
    #         logger.error(f"LLM classification error for {os.path.basename(image_path)}: {e}")
    #         return 'remove'
    #     finally:
    #         # 🆕 CLEAN UP OPTIMIZED IMAGE
    #         if use_optimized and os.path.exists(optimized_path):
    #             os.remove(optimized_path)



    def classify_image_with_llm(self, image_path: str) -> str:
        """Use LLM to classify images with optimization and timing"""
        # 🆕 CHECK CACHE FIRST - use original image for hash
        original_image_path = image_path
        image_hash = hashlib.md5(open(original_image_path, 'rb').read()).hexdigest()
        if image_hash in self.llm_cache:
            logger.info(f"  🔄 CACHED RESULT: {os.path.basename(original_image_path)}")
            return self.llm_cache[image_hash]
        
        start_time = time.time()
        optimized_path = image_path
        use_optimized = False
        
        try:
            # 🆕 OPTIMIZE IMAGE FIRST
            optimized_path = self._optimize_image_for_llm(original_image_path)
            use_optimized = optimized_path != original_image_path
            
            # Use optimized path for API call
            api_image_path = optimized_path if use_optimized else original_image_path
            
            with open(api_image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")

            prompt = """
            Analyze this image from a document. 
            
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
            - Person photos, headshots, team photos, person faces in photos
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
            final_classification = classification if classification in ['keep', 'remove'] else 'remove'
            
            # 🆕 STORE IN CACHE
            self.llm_cache[image_hash] = final_classification
            
            # 🆕 TIMING METRICS
            llm_time = time.time() - start_time
            self.total_llm_time += llm_time
            self.total_images_processed += 1
            
            logger.info(f"⏱️ LLM Time: {llm_time:.2f}s - {os.path.basename(original_image_path)}")
            
            return final_classification
            
        except Exception as e:
            logger.error(f"LLM classification error for {os.path.basename(original_image_path)}: {e}")
            return 'remove'
        finally:
            # 🆕 CLEAN UP OPTIMIZED IMAGE - but only if it's different from original
            if use_optimized and os.path.exists(optimized_path) and optimized_path != original_image_path:
                try:
                    os.remove(optimized_path)
                    logger.debug(f"🧹 Cleaned up temporary optimized image: {os.path.basename(optimized_path)}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not cleanup optimized image: {e}")

    # def _batch_classify_images(self, images: List[ImageChunk], doc_id: str, unit_index: int) -> List[ImageChunk]:
    #     """Batch process images through LLM classification with true parallel processing"""
    #     if not images:
    #         return []
            
    #     logger.info(f"🔍 LLM Classifying {len(images)} images in parallel...")
        
    #     kept_images = []
    #     batch_start_time = time.time()
        
    #     # Process in true parallel batches
    #     for i in range(0, len(images), self.batch_size):
    #         batch = images[i:i + self.batch_size]
    #         logger.info(f"   Processing parallel batch {i//self.batch_size + 1}/{(len(images)-1)//self.batch_size + 1}")
            
    #         # 🆕 TRUE PARALLEL PROCESSING
    #         with ThreadPoolExecutor(max_workers=len(batch)) as executor:
    #             # Submit all images in batch for parallel processing
    #             future_to_image = {executor.submit(self.classify_image_with_llm, img.path): img for img in batch}
                
    #             # Collect results as they complete
    #             for future in concurrent.futures.as_completed(future_to_image):
    #                 img = future_to_image[future]
    #                 try:
    #                     classification = future.result()
                        
    #                     if classification == 'keep':
    #                         kept_images.append(img)
    #                         logger.info(f"  ✅ LLM KEEP: {os.path.basename(img.path)}")
    #                     else:
    #                         logger.info(f"  ❌ LLM REMOVE: {os.path.basename(img.path)}")
                        
    #                 except Exception as e:
    #                     logger.error(f"❌ LLM classification failed for {os.path.basename(img.path)}: {e}")
    #                     # Keep on failure (safe approach)
    #                     kept_images.append(img)
    #                     logger.info(f"  ✅ KEPT (LLM failed): {os.path.basename(img.path)}")
            
    #         # Delay between batches to avoid rate limiting
    #         if i + self.batch_size < len(images):
    #             time.sleep(self.delay_between_batches)
        
    #     batch_time = time.time() - batch_start_time
    #     logger.info(f"⏱️ Batch {unit_index} processed {len(images)} images in {batch_time:.2f}s")
        
    #     return kept_images


    def _batch_classify_images(self, images: List[ImageChunk], doc_id: str, unit_index: int) -> List[ImageChunk]:
        """Batch process images through LLM classification with true parallel processing"""
        if not images:
            return []
            
        logger.info(f"🔍 LLM Classifying {len(images)} images in parallel...")
        
        kept_images = []
        batch_start_time = time.time()
        
        # Track optimized images for cleanup
        optimized_images_to_cleanup = []
        
        # Process in true parallel batches
        for i in range(0, len(images), self.batch_size):
            batch = images[i:i + self.batch_size]
            logger.info(f"   Processing parallel batch {i//self.batch_size + 1}/{(len(images)-1)//self.batch_size + 1}")
            
            # 🆕 TRUE PARALLEL PROCESSING
            with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                # Submit all images in batch for parallel processing
                future_to_image = {executor.submit(self.classify_image_with_llm, img.path): img for img in batch}
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_image):
                    img = future_to_image[future]
                    try:
                        classification = future.result()
                        
                        if classification == 'keep':
                            kept_images.append(img)
                            logger.info(f"  ✅ LLM KEEP: {os.path.basename(img.path)}")
                        else:
                            logger.info(f"  ❌ LLM REMOVE: {os.path.basename(img.path)}")
                        
                    except Exception as e:
                        logger.error(f"❌ LLM classification failed for {os.path.basename(img.path)}: {e}")
                        # Keep on failure (safe approach)
                        kept_images.append(img)
                        logger.info(f"  ✅ KEPT (LLM failed): {os.path.basename(img.path)}")
            
            # Delay between batches to avoid rate limiting
            if i + self.batch_size < len(images):
                time.sleep(self.delay_between_batches)
        
        # 🆕 CLEANUP ALL OPTIMIZED IMAGES
        self._cleanup_optimized_images(images)
        
        batch_time = time.time() - batch_start_time
        logger.info(f"⏱️ Batch {unit_index} processed {len(images)} images in {batch_time:.2f}s")
        
        return kept_images

    def _cleanup_optimized_images(self, images: List[ImageChunk]):
        """Clean up all optimized temporary images"""
        for img in images:
            original_path = img.path
            # Remove any optimized versions
            if '_optimized' in original_path:
                try:
                    if os.path.exists(original_path):
                        os.remove(original_path)
                        logger.debug(f"🧹 Cleaned up optimized image: {os.path.basename(original_path)}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not cleanup optimized image {original_path}: {e}")
            
            # Also check for optimized versions of the original
            base_path = original_path.replace('_optimized', '')
            optimized_path = base_path.replace('.png', '_optimized.jpg').replace('.jpeg', '_optimized.jpg')
            if os.path.exists(optimized_path) and optimized_path != original_path:
                try:
                    os.remove(optimized_path)
                    logger.debug(f"🧹 Cleaned up optimized version: {os.path.basename(optimized_path)}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not cleanup {optimized_path}: {e}")


    def _apply_optimized_filtering(self, images: List[ImageChunk], doc_id: str, unit_index: int, doc_type: str = "unknown", mode: str = "uploaded_only") -> List[str]:
        """
        Apply optimized filtering: Keep JPG → Remove tiny → LLM classify rest
        Returns list of relative paths to kept images
        """
        if not images:
            return []
            
        logger.info(f"🎯 Applying optimized filtering for {len(images)} images in unit {unit_index} (mode: {mode})...")
        
        # Separate images by type
        jpg_images = [img for img in images if img.path.lower().endswith(('.jpg', '.jpeg'))]
        other_images = [img for img in images if not img.path.lower().endswith(('.jpg', '.jpeg'))]
        
        logger.info(f"   JPG/JPEG images: {len(jpg_images)} (AUTOMATICALLY KEPT)")
        logger.info(f"   Other images: {len(other_images)} (FILTERED + LLM)")
        
        final_relative_paths = []
        
        # Step 1: Automatically keep ALL JPG/JPEG files
        for jpg_idx, jpg in enumerate(jpg_images):
            if os.path.exists(jpg.path):
                relative_path = self._store_image_with_relative_path(jpg.path, doc_id, unit_index, jpg_idx, mode)
                if relative_path:
                    final_relative_paths.append(relative_path)
                    logger.info(f"  ✅ JPG AUTOKEEP ({mode}): {os.path.basename(jpg.path)} → {os.path.basename(relative_path)}")
        
        # Step 2: Apply size heuristic to other images - WITH FORMAT-SPECIFIC THRESHOLDS
        tiny_logos = []
        remaining_other_images = []
        
        for img in other_images:
            if self._is_tiny_logo(img, doc_type):
                tiny_logos.append(img)
            else:
                remaining_other_images.append(img)
        
        logger.info(f"   Tiny logos removed: {len(tiny_logos)}")
        logger.info(f"   Remaining for LLM: {len(remaining_other_images)}")
        
        # Step 3: Use LLM for remaining non-JPG images (with batching)
        if remaining_other_images:
            kept_other_images = self._batch_classify_images(remaining_other_images, doc_id, unit_index)
            for img_idx, img in enumerate(kept_other_images):
                # Use the original image index from metadata if available, otherwise use current index
                original_img_index = img.metadata.get('image_index', img_idx)
                relative_path = self._store_image_with_relative_path(img.path, doc_id, unit_index, original_img_index, mode)
                if relative_path:
                    final_relative_paths.append(relative_path)
                    logger.info(f"  ✅ LLM KEEP ({mode}): {os.path.basename(img.path)} → {os.path.basename(relative_path)}")
        
        # Clean up temp files
        self._cleanup_temp_images(images)
        
        logger.info(f"📊 Filtering complete: {len(final_relative_paths)} images kept for unit {unit_index}")
        return final_relative_paths

    def _cleanup_temp_images(self, images: List[ImageChunk]):
        """Clean up temporary image files"""
        for img in images:
            if os.path.exists(img.path) and "temp" in img.path:
                try:
                    os.remove(img.path)
                    logger.debug(f"🧹 Cleaned up temp image: {os.path.basename(img.path)}")
                except:
                    pass

    def _process_document_with_filtering(self, file_path: str, doc_id: str, doc_type: str, mode: str = "uploaded_only") -> DocumentOutput:
        """Process document with mode-dependent filtering"""
        # Use appropriate parser based on file type
        if doc_type == 'pptx':
            chunks = self.pptx_parser.parse_pptx(file_path, doc_id, extract_all=True)
        elif doc_type == 'pdf':
            chunks = self.pdf_parser.parse_pdf(file_path, doc_id)
        elif doc_type == 'docx':
            chunks = self.docx_parser.parse_docx(file_path, doc_id)
        else:
            chunks = self.txt_parser.parse_txt(file_path, doc_id)
        
        units = []
        for chunk in chunks:
            # Extract text chunks
            text_chunks = getattr(chunk, 'text_chunks', []) or []
            clean_texts = [text.strip() for text in text_chunks if text and text.strip()]
            
            # Apply optimized filtering to images - pass the actual unit index and doc_type
            images = getattr(chunk, 'images', []) or []
            filtered_image_paths = self._apply_optimized_filtering(images, doc_id, chunk.index, doc_type, mode)
            
            # Create unit with same structure as original
            units.append(DocumentUnit(
                index=chunk.index,
                unit_type=chunk.unit,
                text=clean_texts,
                images=filtered_image_paths  # Relative paths to appropriate storage
            ))
        
        return DocumentOutput(
            doc_id=doc_id,
            doc_type=doc_type,
            units=units
        )

    def parse_document(self, file_path: str, doc_id: Optional[str] = None, mode: str = "uploaded_only") -> DocumentOutput:
        """Parse any document type with mode-dependent storage"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        if doc_id is None:
            doc_id = os.path.splitext(os.path.basename(file_path))[0]
        
        filename = os.path.basename(file_path)
        file_ext = os.path.splitext(filename)[1].lower()
        
        logger.info(f"🔍 Parsing document with mode-dependent storage: {filename} (mode: {mode})")
        
        try:
            if file_ext == '.pptx':
                return self._process_document_with_filtering(file_path, doc_id, 'pptx', mode)
            elif file_ext == '.pdf':
                return self._process_document_with_filtering(file_path, doc_id, 'pdf', mode)
            elif file_ext == '.docx':
                return self._process_document_with_filtering(file_path, doc_id, 'docx', mode)
            elif file_ext == '.txt':
                return self._process_document_with_filtering(file_path, doc_id, 'txt', mode)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
        except Exception as e:
            logger.error(f"❌ Error parsing {filename}: {e}")
            raise

    def parse_folder(self, folder_path: str, output_filename: str = None, mode: str = "uploaded_only") -> str:
        """Parse all supported documents in a folder with mode-dependent storage"""
        if output_filename is None:
            output_filename = f"unified_documents_{self.user_id}_{self.session_id}.json"
            
        supported_extensions = {'.pptx', '.pdf', '.docx', '.txt'}
        documents = []
        
        logger.info(f"📁 Processing folder with mode-dependent storage: {folder_path} (mode: {mode})")
        
        # 🆕 OVERALL TIMING
        total_start_time = time.time()
        
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext in supported_extensions:
                    try:
                        doc_start_time = time.time()
                        doc_output = self.parse_document(file_path, mode=mode)
                        doc_time = time.time() - doc_start_time
                        
                        documents.append(doc_output.model_dump())
                        logger.info(f"✅ Added: {filename} ({doc_time:.2f}s)")
                    except Exception as e:
                        logger.error(f"❌ Failed to parse {filename}: {e}")
                        continue
        
        # Create unified output (same format as original)
        unified_output = UnifiedOutput(documents=documents)
        
        # Save unified file
        output_path = os.path.join(self.json_output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(unified_output.model_dump(), f, indent=2, ensure_ascii=False)
        
        # 🆕 COMPREHENSIVE TIMING SUMMARY
        total_time = time.time() - total_start_time
        
        # Print summary
        total_units = sum(len(doc['units']) for doc in documents)
        total_text_chunks = sum(len(unit['text']) for doc in documents for unit in doc['units'])
        total_images = sum(len(unit['images']) for doc in documents for unit in doc['units'])
        
        # Count actual files in appropriate storage
        if mode == "uploaded_only":
            storage_dir = self.image_temp_dir
            storage_type = "temp_uploads"
        else:
            storage_dir = self.image_main_dir
            storage_type = "main_corpus"
        
        storage_files = []
        if os.path.exists(storage_dir):
            storage_files = os.listdir(storage_dir)
        
        logger.info(f"\n🎯 MODE-DEPENDENT PROCESSING COMPLETE:")
        logger.info(f"   User: {self.user_id}, Session: {self.session_id}")
        logger.info(f"   Mode: {mode}")
        logger.info(f"   Documents processed: {len(documents)}")
        logger.info(f"   Total units: {total_units}")
        logger.info(f"   Total text chunks: {total_text_chunks}")
        logger.info(f"   Total images in JSON: {total_images}")
        logger.info(f"   Actual images in {storage_type}: {len(storage_files)}")
        
        # 🆕 TIMING METRICS
        logger.info(f"\n⏱️ PERFORMANCE METRICS:")
        logger.info(f"   Total processing time: {total_time:.2f}s")
        if self.total_images_processed > 0:
            logger.info(f"   Total LLM processing time: {self.total_llm_time:.2f}s")
            logger.info(f"   Images processed by LLM: {self.total_images_processed}")
            logger.info(f"   Average LLM time per image: {self.total_llm_time/self.total_images_processed:.2f}s")
            logger.info(f"   Cache hits: {len(self.llm_cache)}")
        
        logger.info(f"   Output: {output_path}")
        
        return output_path

# Backward compatibility

def main():
    """Test the optimized unified parser with timing"""
    parser = UnifiedDocumentParserV2(
        output_base_dir="./unified_output_optimized",
        user_id="test-user",
        session_id="test-session-optimized"
    )
    
    # Test with a folder
    folder_path = "test_documents"
    output_file = parser.parse_folder(folder_path)
    
    print(f"\n✅ OPTIMIZED Processing complete!")
    print(f"📊 Output file: {output_file}")

if __name__ == "__main__":
    main()