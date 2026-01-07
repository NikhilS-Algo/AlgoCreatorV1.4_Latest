
# Add this import at the top of app.py (after other imports)
import zipfile
from pathlib import Path    

#this is change
# app.py
# Add these imports (after other imports, before app initialization)
import threading
import uuid
from typing import Dict, Any, Optional
from enum import Enum

# Add these global variables (after user_sessions, user_outlines, user_presentations)
bulk_upload_progress = {}
bulk_upload_lock = threading.Lock()
bulk_upload_tasks = {}

import os
import uuid
import json
import time
import shutil
import tempfile
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pptx import Presentation
from datetime import datetime, timedelta

# Import your pipeline components
from step6_outlinegen_text_and_image import create_complete_presentation_pipeline
from unified_document_parser_v2 import UnifiedDocumentParserV2
from Step2_Processing_unified_document_json_file_for_vector_store import JSONPreprocessor
from step3_Image_caption_generator_Openai import ImageCaptionProcessor
from step4_deduplicate_chunks_and_images import DocumentDeduplicator
from step5_four_vector_store_with_image_caption_and_text import main_embedding_pipeline
from storage_manager import StorageManager
# In app.py, add this import:
from unified_ppt_parser_optimized import OptimizedPPTXParser
# Initialize FastAPI app
app = FastAPI(title="Presentation Generation API", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models (unchanged for frontend compatibility)
class UploadResponse(BaseModel):
    user_id: str
    session_id: str
    is_file_uploaded_by_user: bool
    available_modes: List[str]
    message: str

class ModesResponse(BaseModel):
    user_id: str
    available_modes: List[str]
    has_uploaded_files: bool

class GenerateOutlineRequest(BaseModel):
    query: str
    user_id: str
    mode: str
    num_slides: int = 8
    presentation_style: str = "corporate"

class TemplateOption(BaseModel):
    id: str
    name: str
    description: str
    image_path: str
    template_file: Optional[str] = None

class GenerateDefaultTemplateRequest(BaseModel):
    user_id: str
    template_id: str

class PresentationResponse(BaseModel):
    user_id: str
    presentation_id: str
    presentation_path: str
    pdf_path: str
    template_used: str
    status: str


class BulkUploadProgressTracker:
    """Tracks progress of bulk upload processing - FIXED for minimal locking"""
    
    class Step(Enum):
        EXTRACTING = "extracting"
        PARSING = "parsing"
        PREPROCESSING = "preprocessing"
        IMAGE_CAPTIONING = "image_captioning"
        DEDUPLICATION = "deduplication"
        EMBEDDING = "embedding"
        FINALIZING = "finalizing"
        COMPLETE = "complete"
        FAILED = "failed"
    
    STEP_WEIGHTS = {
        Step.EXTRACTING: 5,
        Step.PARSING: 30,
        Step.PREPROCESSING: 10,
        Step.IMAGE_CAPTIONING: 25,
        Step.DEDUPLICATION: 5,
        Step.EMBEDDING: 20,
        Step.FINALIZING: 5,
    }
    
    def __init__(self, user_id: str, task_id: str, total_files: int = 0):
        self.user_id = user_id
        self.task_id = task_id
        self.total_files = total_files
        self.processed_files = 0
        self.current_step = self.Step.EXTRACTING
        self.step_progress = 0  # 0-100 within current step
        self.message = "Starting bulk upload..."
        self.start_time = time.time()
        self.end_time = None
        self.error = None
        self.result = None
        self._lock = threading.Lock()  # Individual lock per tracker
        
    def update_step(self, step: Step, step_progress: int = 0, message: str = None):
        """Update current step and progress - MINIMAL LOCKING"""
        # Only lock for the actual assignment
        with self._lock:
            self.current_step = step
            self.step_progress = max(0, min(100, step_progress))
            if message:
                self.message = message
    
    def update_file_progress(self, processed_files: int, total_files: int = None):
        """Update file processing progress - MINIMAL LOCKING"""
        with self._lock:
            self.processed_files = processed_files
            if total_files:
                self.total_files = total_files
    
    def set_error(self, error: str):
        """Set error state - MINIMAL LOCKING"""
        with self._lock:
            self.current_step = self.Step.FAILED
            self.error = error
            self.message = f"Error: {error}"
            self.end_time = time.time()
    
    def set_complete(self, result: Dict[str, Any]):
        """Set completion state - MINIMAL LOCKING"""
        with self._lock:
            self.current_step = self.Step.COMPLETE
            self.step_progress = 100
            self.message = "Bulk upload completed successfully"
            self.result = result
            self.end_time = time.time()
            self.processed_files = self.total_files
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress as dictionary - MINIMAL LOCKING"""
        # Use local variables to minimize lock time
        with self._lock:
            current_step = self.current_step
            step_progress = self.step_progress
            processed_files = self.processed_files
            total_files = self.total_files
            message = self.message
            error = self.error
            result = self.result
            start_time = self.start_time
            end_time = self.end_time
        
        # Calculate outside of lock
        overall_progress = 0
        if current_step == self.Step.COMPLETE:
            overall_progress = 100
        elif current_step == self.Step.FAILED:
            overall_progress = 0
        else:
            # Calculate progress based on completed steps
            completed_weight = 0
            total_weight = sum(self.STEP_WEIGHTS.values())
            
            # Add weight for completed steps
            for step, weight in self.STEP_WEIGHTS.items():
                if step.value == current_step.value:
                    # Add partial weight for current step
                    completed_weight += (step_progress / 100) * weight
                    break
                else:
                    # Add full weight for completed steps
                    completed_weight += weight
            
            overall_progress = (completed_weight / total_weight) * 100
        
        elapsed_time = time.time() - start_time
        if end_time:
            elapsed_time = end_time - start_time
        
        status = "running" if current_step not in [self.Step.COMPLETE, self.Step.FAILED] else current_step.value
        
        return {
            "user_id": self.user_id,
            "task_id": self.task_id,
            "current_step": current_step.value,
            "step_progress": step_progress,
            "overall_progress": round(overall_progress, 1),
            "processed_files": processed_files,
            "total_files": total_files,
            "message": message,
            "status": status,
            "elapsed_time": round(elapsed_time, 1),
            "error": error,
            "result": result,
            "start_time": start_time,
            "end_time": end_time
        }


# Global storage for user sessions and outlines
user_sessions = {}
user_outlines = {}
user_presentations = {}

# Available templates
available_templates = {
    "template1": {
        "id": "template1",
        "name": "Split Diagonal Layout",
        "description": "Modern alternating layout with images on left/right sides",
        "image_path": "template_images/template1.png",
        "template_file": None
    },
    "template2": {
        "id": "template2", 
        "name": "Dynamic Layout",
        "description": "Flexible layout with rounded images and adaptive text",
        "image_path": "template_images/template2.png",
        "template_file": None
    },
    "template3": {
        "id": "template3",
        "name": "Professional Blue",
        "description": "Corporate blue theme with clean modern design",
        "image_path": "template_images/template3.png",
        "template_file": None
    },
    "template4": {
        "id": "template4",
        "name": "Minimal Dark", 
        "description": "Dark theme with minimalistic layout",
        "image_path": "template_images/template4.png",
        "template_file": None
    }
}

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.pptx', '.pdf', '.docx', '.txt'}

# Create necessary directories
os.makedirs("template_images", exist_ok=True)
os.makedirs("user_uploads", exist_ok=True)
os.makedirs("processed_json", exist_ok=True)
os.makedirs("unified_output", exist_ok=True)
os.makedirs("generated_presentations", exist_ok=True)
os.makedirs("user_templates", exist_ok=True)
os.makedirs("generated_pdfs", exist_ok=True)

# Image serving endpoints
@app.get("/template-images/{template_id}")
async def get_template_image(template_id: str):
    """Serve template preview images"""
    if template_id not in available_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    image_path = available_templates[template_id]["image_path"]
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Template image not found")
    
    return FileResponse(image_path)

@app.get("/corpus-images/{user_id}/{image_filename}")
async def get_corpus_image(user_id: str, image_filename: str):
    """Serve images from user's main corpus"""
    if ".." in image_filename or "/" in image_filename:
        raise HTTPException(status_code=400, detail="Invalid image name")
    
    image_path = f"images/{user_id}/main_corpus/{image_filename}"
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Corpus image not found")
    
    return FileResponse(image_path)

@app.get("/temp-images/{user_id}/{session_id}/{image_filename}")
async def get_temp_image(user_id: str, session_id: str, image_filename: str):
    """Serve images from user's temp session"""
    if ".." in image_filename or "/" in image_filename:
        raise HTTPException(status_code=400, detail="Invalid image name")
    
    image_path = f"images/{user_id}/temp_uploads/{image_filename}"
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Temp image not found")
    
    return FileResponse(image_path)

@app.get("/hybrid-images/{user_id}/{session_id}/{image_filename}")
async def get_hybrid_image(user_id: str, session_id: str, image_filename: str):
    """Serve images with fallback logic for hybrid mode"""
    if ".." in image_filename or "/" in image_filename:
        raise HTTPException(status_code=400, detail="Invalid image name")
    
    # Try temp first
    temp_path = f"images/{user_id}/temp_uploads/{image_filename}"
    if os.path.exists(temp_path):
        return FileResponse(temp_path)
    
    # Fallback to main corpus
    main_path = f"images/{user_id}/main_corpus/{image_filename}"
    if os.path.exists(main_path):
        return FileResponse(main_path)
    
    raise HTTPException(status_code=404, detail="Image not found in temp or main corpus")

def convert_image_paths_to_urls(slides_data, user_id, mode, session_id=None):
    """Convert image paths to URLs for frontend display"""
    print(f"🖼️ Converting image paths to URLs for mode: {mode}")
    
    for slide in slides_data:
        for image in slide.get('images', []):
            image_path = image.get('image_path', '')
            if image_path:
                # Extract filename
                filename = os.path.basename(image_path)
                
                if mode == "corpus_only":
                    image['image_url'] = f"/corpus-images/{user_id}/{filename}"
                elif mode == "uploaded_only":
                    if session_id:
                        image['image_url'] = f"/temp-images/{user_id}/{session_id}/{filename}"
                elif mode == "uploaded_plus_corpus":
                    # For hybrid mode, use hybrid image endpoint
                    if session_id:
                        image['image_url'] = f"/hybrid-images/{user_id}/{session_id}/{filename}"
                else:
                    image['image_url'] = f"/corpus-images/{user_id}/{filename}"
                    
                print(f"   📷 Image URL: {image['image_url']}")
    
    return slides_data

async def process_uploaded_files_sync(user_id: str, session_id: str, files: List[UploadFile]):
    """Process files synchronously - wait for ALL pipeline steps to complete"""
    print(f"🔄 Starting synchronous file processing for session: {session_id}")
    
    try:
        # Create user upload directory
        upload_dir = f"user_uploads/{user_id}/{session_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save uploaded files
        saved_files = []
        for file in files:
            # Check file extension
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in SUPPORTED_EXTENSIONS:
                print(f"⚠️ Skipping unsupported file: {file.filename}")
                continue
            
            # Save file
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(file_path)
            print(f"💾 Saved file: {file.filename}")
        
        if not saved_files:
            print("⚠️ No supported files to process")
            return
        
        print(f"🔍 STEP 1: Parsing {len(saved_files)} uploaded documents...")
        
        # STEP 1: Parse documents with UnifiedDocumentParserV2
        unified_parser = UnifiedDocumentParserV2(
            output_base_dir="./unified_output",
            user_id=user_id,
            session_id=session_id
        )
        
        unified_output_path = unified_parser.parse_folder(upload_dir)
        print(f"✅ Unified parsing complete: {unified_output_path}")
        
        # STEP 2: Preprocess documents
        print("🔄 STEP 2: Preprocessing documents...")
        with open(unified_output_path, 'r', encoding='utf-8') as f:
            unified_data = json.load(f)
        
        preprocessor = JSONPreprocessor()
        processed_data = preprocessor.preprocess_documents(
            unified_data, 
            user_id=user_id, 
            session_id=session_id
        )
        
        # Save step2 output
        step2_output_path = f"processed_json/{user_id}/step2_processed_{user_id}_{session_id}.json"
        preprocessor.save_processed_json(processed_data, step2_output_path)
        print(f"✅ Preprocessing complete: {step2_output_path}")
        
        # STEP 3: Generate image captions
        print("🖼️ STEP 3: Generating image captions...")
        caption_processor = ImageCaptionProcessor()
        step3_output_path = caption_processor.process_user_documents(
            user_id=user_id,
            session_id=session_id,
            step2_input_file=step2_output_path,
            batch_delay=0.1
        )
        print(f"✅ Image captioning complete: {step3_output_path}")
        
        # STEP 4: Deduplicate chunks
        print("🧹 STEP 4: Deduplicating content...")
        deduplicator = DocumentDeduplicator()
        deduplication_result = deduplicator.deduplicate_documents(
            input_file=step3_output_path,
            user_id=user_id,
            session_id=session_id
        )
        
        if not deduplication_result['success']:
            raise Exception(f"Deduplication failed: {deduplication_result['error']}")
        
        step4_output_path = deduplication_result['output_file']
        print(f"✅ Deduplication complete: {step4_output_path}")
        
        # STEP 5: Create embeddings - FIXED: Remove vector_store_path parameter
        print("📚 STEP 5: Creating vector embeddings in temp store...")
        try:
            # Get OpenAI API key
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            # FIXED: Your function expects openai_api_key, user_id, session_id - no vector_store_path
            embedding_processor = main_embedding_pipeline(
                openai_api_key=openai_api_key,  # ✅ ADDED
                user_id=user_id,
                session_id=session_id
                # ❌ REMOVED: vector_store_path parameter
            )
            print("✅ Embeddings created and stored in TEMP vector database (temp_uploads)")
        except Exception as e:
            print(f"⚠️ Embedding creation had issues: {e}")
            # Continue anyway - outline generation might still work
        
        print(f"🎉 All file processing steps completed for session: {session_id}")
        
    except Exception as e:
        print(f"❌ File processing failed for session {session_id}: {e}")
        raise

@app.post("/upload_file", response_model=UploadResponse)
async def upload_file(
    user_id: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    """
    Handle user file upload and process them through the pipeline
    Returns 200 only after ALL processing is complete
    """
    print(f"📥 Upload request received for user: {user_id}")
    
    try:
        # Clean previous session to start fresh
        if user_id in user_sessions:
            print(f"🧹 Cleaning previous session for user: {user_id}")
            storage = StorageManager(user_id)
            session_id = user_sessions[user_id].get('session_id')
            if session_id:
                storage.cleanup_temp_data(session_id)
            del user_sessions[user_id]
        
        if user_id in user_outlines:
            del user_outlines[user_id]
            print(f"🧹 Cleared previous outline for user: {user_id}")
        
        # Validate user_id
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Create session ID for this flow
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        print(f"🆕 Created session: {session_id} for user: {user_id}")
        
        # Check if files were uploaded
        has_files = files and len(files) > 0 and files[0].filename and files[0].filename != ""
        
        if has_files:
            print(f"📁 Processing {len(files)} files for user {user_id}...")
            
            # Process files SYNCHRONOUSLY (wait for completion)
            await process_uploaded_files_sync(user_id, session_id, files)
            
            # Store session information
            user_sessions[user_id] = {
                'session_id': session_id,
                'is_file_uploaded_by_user': True,
                'available_modes': ["uploaded_only", "uploaded_plus_corpus"],
                'created_at': time.time(),
                'files_processed': True
            }
            
            print(f"✅ File processing COMPLETED for user {user_id}")
            
            return UploadResponse(
                user_id=user_id,
                session_id=session_id,
                is_file_uploaded_by_user=True,
                available_modes=["uploaded_only", "uploaded_plus_corpus"],
                message=f"Successfully uploaded and processed {len(files)} files"
            )
        else:
            # No files uploaded - corpus only mode
            print(f"📝 No files uploaded for user {user_id}, using corpus only mode")
            
            user_sessions[user_id] = {
                'session_id': session_id,
                'is_file_uploaded_by_user': False,
                'available_modes': ["corpus_only"],
                'created_at': time.time(),
                'files_processed': False
            }
            
            return UploadResponse(
                user_id=user_id,
                session_id=session_id,
                is_file_uploaded_by_user=False,
                available_modes=["corpus_only"],
                message="Session created successfully for corpus-only mode"
            )
        
    except Exception as e:
        print(f"❌ Upload failed for user {user_id}: {e}")
        # Cleanup on error
        if user_id in user_sessions:
            storage = StorageManager(user_id)
            session_id = user_sessions[user_id].get('session_id')
            if session_id:
                storage.cleanup_temp_data(session_id)
            del user_sessions[user_id]
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    



@app.post("/bulk_upload")
async def bulk_upload(
    user_id: str = Form(...),
    zip_file: UploadFile = File(...)
):
    """
    Bulk upload and process zip file containing PPTX files
    Creates/updates vector database and image corpus
    Returns immediately with task ID, use /bulk_upload_progress to track
    """
    print(f"📦 Bulk upload request for user: {user_id}")
    
    try:
        # Validate user_id
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Validate file type
        if not zip_file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="Only .zip files are supported")
        
        # Generate task ID
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # Create a temporary directory to save the file
        temp_save_dir = f"temp_uploads/{user_id}/{task_id}"
        os.makedirs(temp_save_dir, exist_ok=True)
        
        # Save the uploaded file IMMEDIATELY before returning response
        zip_file_path = os.path.join(temp_save_dir, zip_file.filename)
        
        print(f"💾 Saving uploaded file to: {zip_file_path}")
        
        # Read and save the file content
        file_content = await zip_file.read()  # Read all content before returning
        
        with open(zip_file_path, "wb") as buffer:
            buffer.write(file_content)
        
        print(f"✅ File saved: {zip_file_path} ({len(file_content)} bytes)")
        
        # Initialize progress tracker
        tracker = BulkUploadProgressTracker(user_id, task_id)
        
        # Store tracker
        with bulk_upload_lock:
            bulk_upload_progress[task_id] = tracker
        
        # Start processing in background thread - PASS THE SAVED FILE PATH
        def process_in_background():
            try:
                process_bulk_upload_background(user_id, zip_file_path, tracker, task_id)
            except Exception as e:
                print(f"❌ Background processing failed for task {task_id}: {e}")
                import traceback
                traceback.print_exc()
                tracker.set_error(str(e))
                
                # Cleanup temp directory on error
                if os.path.exists(temp_save_dir):
                    try:
                        shutil.rmtree(temp_save_dir)
                        print(f"🧹 Cleaned temp directory on error: {temp_save_dir}")
                    except:
                        pass
                
                # DO NOT start immediate cleanup here! Let the failed task stay for progress tracking
                # The stale task cleanup will handle it later
        
        # Start background thread
        thread = threading.Thread(target=process_in_background, daemon=True)
        thread.start()
        
        print(f"✅ Bulk upload started for user {user_id}, task ID: {task_id}")
        
        # Return immediately with task ID
        return {
            "status": "processing_started",
            "user_id": user_id,
            "task_id": task_id,
            "message": "Bulk upload processing started in background",
            "progress_url": f"/bulk_upload_progress/{task_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Bulk upload failed for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")


def process_bulk_upload_background(user_id: str, zip_file_path: str, tracker: BulkUploadProgressTracker, task_id: str):
    """Process bulk upload in background with progress tracking - FIXED for minimal locking"""
    print(f"🔄 Starting background processing for task: {task_id}")
    
    # NO LONG GLOBAL LOCK HERE!
    # Just quick check
    with bulk_upload_lock:
        if task_id not in bulk_upload_progress:
            print(f"⚠️ Task {task_id} not found, might have been cleaned up")
            return
    
    temp_dir = None
    temp_save_dir = os.path.dirname(zip_file_path)
    try:
        # STEP 1: Extract ZIP file
        tracker.update_step(tracker.Step.EXTRACTING, 0, "Extracting ZIP file...")
        
        # Use a different directory for extraction (inside the temp save dir)
        temp_dir = os.path.join(temp_save_dir, "extracted")
        os.makedirs(temp_dir, exist_ok=True)
        
        tracker.update_step(tracker.Step.EXTRACTING, 50, "Extracting files from ZIP...")
        
        extract_dir = os.path.join(temp_dir, "content")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        tracker.update_step(tracker.Step.EXTRACTING, 100, "Extraction complete")
        
        # Find PPTX files
        tracker.update_step(tracker.Step.PARSING, 0, "Scanning for PPTX files...")
        
        pptx_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith('.pptx'):
                    pptx_files.append(os.path.join(root, file))
        
        if not pptx_files:
            tracker.set_error("No PPTX files found in the zip archive")
            return
        
        tracker.update_file_progress(0, len(pptx_files))
        tracker.update_step(tracker.Step.PARSING, 10, f"Found {len(pptx_files)} PPTX files")
        
        # Get common directory
        common_dir = extract_dir
        if pptx_files:
            common_parents = [os.path.dirname(f) for f in pptx_files]
            if common_parents:
                common_dir = os.path.commonprefix(common_parents)
        
        # Process files
        result = process_bulk_pptx_files_with_progress(user_id, common_dir, pptx_files, tracker)
        
        # Finalize
        tracker.update_step(tracker.Step.FINALIZING, 100, "Cleaning up temporary files...")
        
        # Cleanup all temp directories
        cleanup_dirs = []
        if temp_save_dir and os.path.exists(temp_save_dir):
            cleanup_dirs.append(temp_save_dir)
        
        for dir_path in cleanup_dirs:
            try:
                shutil.rmtree(dir_path)
                print(f"🧹 Cleaned up temp directory: {dir_path}")
            except Exception as e:
                print(f"⚠️ Could not clean temp directory {dir_path}: {e}")
        
        tracker.set_complete(result)
        
        print(f"✅ Background processing completed for task: {task_id}")
        
        # Schedule cleanup of completed task (keep for 1 hour)
        def cleanup_completed_task():
            time.sleep(3600)
            with bulk_upload_lock:
                if task_id in bulk_upload_progress:
                    del bulk_upload_progress[task_id]
        
        threading.Thread(target=cleanup_completed_task, daemon=True).start()
        
    except Exception as e:
        print(f"❌ Background processing error for task {task_id}: {e}")
        import traceback
        traceback.print_exc()
        tracker.set_error(str(e))
        
        # Cleanup temp directories on error
        cleanup_dirs = []
        if temp_save_dir and os.path.exists(temp_save_dir):
            cleanup_dirs.append(temp_save_dir)
        
        for dir_path in cleanup_dirs:
            try:
                shutil.rmtree(dir_path)
            except:
                pass



# @app.get("/bulk_upload_progress/{task_id}")
# async def get_bulk_upload_progress(task_id: str):
#     """
#     Get progress of bulk upload processing
#     UI can poll this endpoint every 2-5 seconds
#     """
#     try:
#         with bulk_upload_lock:
#             print(f"📊 Checking progress for task: {task_id}")
#             print(f"📊 Available tasks: {list(bulk_upload_progress.keys())}")
            
#             if task_id not in bulk_upload_progress:
#                 raise HTTPException(status_code=404, detail="Task not found or has expired")
            
#             tracker = bulk_upload_progress[task_id]
#             progress_data = tracker.get_progress()
        
#         print(f"📊 Progress request for task {task_id}: {progress_data['overall_progress']}% - {progress_data['message']}")
        
#         return progress_data
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"❌ Error getting progress for task {task_id}: {e}")
#         raise HTTPException(status_code=500, detail=f"Error getting progress: {str(e)}")



@app.get("/bulk_upload_progress/{user_id}")
async def get_bulk_upload_progress(
    user_id: str, 
    task_id: Optional[str] = None
):
    """
    Get progress of bulk upload processing
    - If only user_id: returns latest task progress
    - If user_id + task_id: returns specific task progress
    FIXED: No global lock to prevent blocking
    """
    try:
        # FIRST: Get the tracker WITHOUT holding global lock
        tracker = None
        found_task_id = None
        
        # Quick snapshot of available tasks
        with bulk_upload_lock:  # VERY BRIEF lock
            task_ids_snapshot = list(bulk_upload_progress.keys())
        
        print(f"🔍 Progress check for user: {user_id}")
        print(f"📋 Available tasks: {task_ids_snapshot}")
        
        if task_id:
            # Specific task requested
            print(f"🎯 Looking for specific task: {task_id}")
            
            # Check if task exists (brief lock)
            with bulk_upload_lock:
                if task_id not in bulk_upload_progress:
                    raise HTTPException(status_code=404, detail="Task not found or has expired")
                tracker = bulk_upload_progress[task_id]
                found_task_id = task_id
        else:
            # Find latest task for user
            print(f"🔎 Finding latest task for user: {user_id}")
            
            latest_task_id = None
            latest_time = 0
            
            # Iterate through snapshot without holding lock
            for t_id in task_ids_snapshot:
                # Brief check for each task
                with bulk_upload_lock:
                    if t_id in bulk_upload_progress:
                        task_tracker = bulk_upload_progress[t_id]
                        if task_tracker.user_id == user_id:
                            if task_tracker.start_time > latest_time:
                                latest_time = task_tracker.start_time
                                latest_task_id = t_id
                                tracker = task_tracker
            
            if not tracker:
                raise HTTPException(status_code=404, detail="No bulk upload tasks found for this user")
            
            found_task_id = latest_task_id
            print(f"✅ Using latest task: {found_task_id}")
        
        # Verify ownership (after we have the tracker)
        if tracker.user_id != user_id:
            raise HTTPException(status_code=403, detail="Task does not belong to this user")
        
        # Get progress data WITHOUT any locks (tracker has its own lock)
        progress_data = tracker.get_progress()
        
        print(f"📊 Progress: {progress_data['overall_progress']}% - {progress_data['message']}")
        
        return progress_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting progress: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting progress: {str(e)}")
    



# @app.get("/bulk_upload_progress/{user_id}")
# async def get_bulk_upload_progress(
#     user_id: str, 
#     task_id: Optional[str] = None  # Optional query parameter
# ):
#     """
#     Get progress of bulk upload processing
#     - If only user_id: returns latest task progress
#     - If user_id + task_id: returns specific task progress
#     """
#     try:
#         with bulk_upload_lock:
#             # List all available tasks for debugging
#             print(f"🔍 Looking up progress for user: {user_id}")
#             print(f"📋 Available tasks in system: {list(bulk_upload_progress.keys())}")
            
#             # Track which tasks belong to this user
#             user_tasks = []
#             for t_id, tracker in bulk_upload_progress.items():
#                 if tracker.user_id == user_id:
#                     user_tasks.append(t_id)
            
#             print(f"👤 Tasks for user {user_id}: {user_tasks}")
            
#             if task_id:
#                 # Specific task requested
#                 print(f"🎯 Looking for specific task: {task_id}")
                
#                 if task_id not in bulk_upload_progress:
#                     raise HTTPException(status_code=404, detail="Task not found or has expired")
                
#                 tracker = bulk_upload_progress[task_id]
                
#                 # Verify task belongs to user
#                 if tracker.user_id != user_id:
#                     raise HTTPException(status_code=403, detail="Task does not belong to this user")
                    
#                 print(f"✅ Found specific task: {task_id}")
#             else:
#                 # Find latest task for user
#                 print(f"🔎 Finding latest task for user: {user_id}")
                
#                 if not user_tasks:
#                     raise HTTPException(status_code=404, detail="No bulk upload tasks found for this user")
                
#                 # Get the most recent task (highest start_time)
#                 latest_task_id = None
#                 latest_time = 0
                
#                 for t_id in user_tasks:
#                     tracker = bulk_upload_progress[t_id]
#                     if tracker.start_time > latest_time:
#                         latest_time = tracker.start_time
#                         latest_task_id = t_id
                
#                 if not latest_task_id:
#                     raise HTTPException(status_code=404, detail="No active bulk upload found")
                
#                 tracker = bulk_upload_progress[latest_task_id]
#                 task_id = latest_task_id
#                 print(f"✅ Using latest task: {task_id} (started at {tracker.start_time})")
            
#             progress_data = tracker.get_progress()
        
#         print(f"📊 Progress: {progress_data['overall_progress']}% - {progress_data['message']}")
        
#         return progress_data
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"❌ Error getting progress: {e}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Error getting progress: {str(e)}")
    
    
@app.get("/bulk_upload_tasks/{user_id}")
async def get_user_bulk_upload_tasks(user_id: str):
    """Get all bulk upload tasks for a user"""
    try:
        user_tasks = []
        with bulk_upload_lock:
            for task_id, tracker in bulk_upload_progress.items():
                if tracker.user_id == user_id:
                    user_tasks.append({
                        "task_id": task_id,
                        "status": tracker.get_progress()["status"],
                        "start_time": tracker.start_time,
                        "progress": tracker.get_progress()["overall_progress"]
                    })
        
        return {
            "user_id": user_id,
            "tasks": user_tasks,
            "total_tasks": len(user_tasks)
        }
        
    except Exception as e:
        print(f"❌ Error getting tasks for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting tasks: {str(e)}")

@app.delete("/bulk_upload_task/{task_id}")
async def cancel_bulk_upload_task(task_id: str, user_id: str):
    """Cancel a bulk upload task"""
    try:
        with bulk_upload_lock:
            if task_id not in bulk_upload_progress:
                raise HTTPException(status_code=404, detail="Task not found")
            
            tracker = bulk_upload_progress[task_id]
            if tracker.user_id != user_id:
                raise HTTPException(status_code=403, detail="Task does not belong to this user")
            
            # Mark as failed with cancellation message
            tracker.set_error("Task cancelled by user")
            
            # Remove from tracking after delay
            def delayed_cleanup():
                time.sleep(300)  # Keep cancelled tasks for 5 minutes
                with bulk_upload_lock:
                    if task_id in bulk_upload_progress:
                        del bulk_upload_progress[task_id]
                    if task_id in bulk_upload_tasks:
                        del bulk_upload_tasks[task_id]
            
            threading.Thread(target=delayed_cleanup, daemon=True).start()
        
        print(f"🗑️ Task {task_id} cancelled by user {user_id}")
        
        return {
            "status": "cancelled",
            "message": f"Task {task_id} has been cancelled",
            "task_id": task_id,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error cancelling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error cancelling task: {str(e)}")
    

def cleanup_stale_tasks():
    """Clean up stale tasks that have been completed/failed for too long"""
    while True:
        try:
            time.sleep(300)  # Run every 5 minutes
            
            current_time = time.time()
            stale_tasks = []
            
            with bulk_upload_lock:
                for task_id, tracker in list(bulk_upload_progress.items()):
                    if tracker.end_time and (current_time - tracker.end_time > 3600):  # 1 hour
                        stale_tasks.append(task_id)
                
                for task_id in stale_tasks:
                    del bulk_upload_progress[task_id]
                    if task_id in bulk_upload_tasks:
                        del bulk_upload_tasks[task_id]
                    
                    print(f"🧹 Cleaned up stale task: {task_id}")
        
        except Exception as e:
            print(f"⚠️ Error in cleanup_stale_tasks: {e}")

# Start cleanup thread when app starts
cleanup_thread = threading.Thread(target=cleanup_stale_tasks, daemon=True)
cleanup_thread.start()
print("✅ Started stale task cleanup thread")



async def process_bulk_pptx_files(user_id: str, input_folder: str, pptx_files: List[str]):
    """Process multiple PPTX files and create/update corpus"""
    
    print(f"🔄 Processing bulk PPTX files for user: {user_id}")
    print(f"📁 Processing folder: {input_folder}")
    print(f"📄 PPTX files to process: {len(pptx_files)}")
    
    # Create a modified version of SimpleCorpusBuilder
    class BulkCorpusBuilder:
        def __init__(self, user_id: str):
            self.user_id = user_id
            self.session_id = f"bulk_{uuid.uuid4().hex[:8]}"
            
            # Dynamic paths based on user_id
            self.output_vector_db = f"chroma_db/{self.user_id}/main_corpus"
            self.output_images = f"images/{self.user_id}/main_corpus"
            
            # Create all directories
            self._create_directories()
            
            print(f"🚀 Bulk Corpus Builder for: {self.user_id}")
            print(f"📤 Vector DB: {self.output_vector_db}")
            print(f"🖼️ Images: {self.output_images}")
        
        def _create_directories(self):
            """Create all necessary directories"""
            directories = [
                f"processed_json/{self.user_id}",
                f"unified_output/{self.user_id}",
                f"user_uploads/{self.user_id}",
                f"images/{self.user_id}/main_corpus",
                f"chroma_db/{self.user_id}/main_corpus",
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ Created: {directory}")
        
        def build_corpus(self, input_folder: str) -> Dict[str, Any]:
            """Process all files and create/update embeddings"""
            try:
                # STEP 1: Parse all PPTX files
                unified_json_path = self._step1_parse_pptx(input_folder)
                
                # Check if we actually processed any files
                if not os.path.exists(unified_json_path) or os.path.getsize(unified_json_path) == 0:
                    print(f"⚠️ No PPTX files were processed from {input_folder}")
                    # Return empty statistics
                    return {
                        'total_images': 0,
                        'vector_documents': 0,
                        'vector_db_path': self.output_vector_db,
                        'images_path': self.output_images,
                        'user_id': self.user_id,
                        'status': 'no_files_processed'
                    }
                
                # STEP 2: Preprocessing
                step2_output_path = self._step2_preprocessing(unified_json_path)
                
                # STEP 3: Image captioning
                step3_output_path = self._step3_image_captioning(step2_output_path)
                
                # STEP 4: Deduplication (handles empty case)
                step4_output_path = self._step4_deduplication(step3_output_path)
                
                # STEP 5: Create embeddings only if we have content
                file_size = os.path.getsize(step4_output_path) if os.path.exists(step4_output_path) else 0
                if file_size > 100:  # Arbitrary threshold for "has content"
                    self._step5_create_embeddings(step4_output_path)
                else:
                    print(f"⚠️ No content to create embeddings for")
                
                # STEP 6: Get statistics
                final_stats = self._step6_get_statistics()
                
                return final_stats
                
            except Exception as e:
                print(f"❌ Corpus building failed: {e}")
                import traceback
                traceback.print_exc()
                raise
        
        def _step1_parse_pptx(self, input_folder: str) -> str:
            """Parse all PPTX files - pass the correct folder"""
            print(f"\n🔍 STEP 1: Parsing PPTX files from: {input_folder}")
            
            # DEBUG: List what's in the folder
            print(f"🔍 Contents of {input_folder}:")
            for root, dirs, files in os.walk(input_folder):
                level = root.replace(input_folder, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f'{indent}📁 {os.path.basename(root)}/')
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    print(f'{subindent}📄 {file}')
            
            # Parser will extract images to user's main_corpus
            parser = OptimizedPPTXParser(output_base_dir=f"unified_output/{self.user_id}", user_id=self.user_id)
            unified_output_path = parser.parse_ppt_folder(
                folder_path=input_folder,  # This should be the folder containing PPTX files
                output_filename=f"unified_ppt_{self.session_id}.json"
            )
            
            print(f"✅ Unified parsing complete: {unified_output_path}")
            return unified_output_path
        
        def _step2_preprocessing(self, unified_json_path: str) -> str:
            """Preprocess documents"""
            print(f"\n🔄 STEP 2: Preprocessing documents...")
            
            with open(unified_json_path, 'r', encoding='utf-8') as f:
                unified_data = json.load(f)
            
            preprocessor = JSONPreprocessor()
            processed_data = preprocessor.preprocess_documents(
                unified_data, 
                user_id=self.user_id, 
                session_id=self.session_id
            )
            
            step2_output_path = f"processed_json/{self.user_id}/step2_processed_{self.user_id}_{self.session_id}.json"
            preprocessor.save_processed_json(processed_data, step2_output_path)
            
            print(f"✅ Preprocessing complete: {step2_output_path}")
            return step2_output_path
        
        def _step3_image_captioning(self, step2_input_path: str) -> str:
            """Generate image captions"""
            print(f"\n🖼️ STEP 3: Generating image captions...")
            
            caption_processor = ImageCaptionProcessor()
            step3_output_path = caption_processor.process_user_documents(
                user_id=self.user_id,
                session_id=self.session_id,
                step2_input_file=step2_input_path,
                batch_delay=0.1
            )
            
            print(f"✅ Image captioning complete: {step3_output_path}")
            return step3_output_path
        

        def _step4_deduplication(self, step3_input_path: str) -> str:
            """Deduplicate content - handle empty files"""
            print(f"\n🧹 STEP 4: Deduplicating content...")
            
            # Check if file exists and has content
            if not os.path.exists(step3_input_path) or os.path.getsize(step3_input_path) == 0:
                print(f"⚠️ Input file is empty or doesn't exist: {step3_input_path}")
                print(f"   Returning input file as is")
                return step3_input_path
            
            deduplicator = DocumentDeduplicator()
            deduplication_result = deduplicator.deduplicate_documents(
                input_file=step3_input_path,
                user_id=self.user_id,
                session_id=self.session_id
            )
            
            if not deduplication_result['success']:
                # If there are no chunks, return the original file instead of raising error
                if "No chunks found" in deduplication_result.get('error', ''):
                    print(f"⚠️ No chunks to deduplicate, returning original file")
                    return step3_input_path
                else:
                    raise Exception(f"Deduplication failed: {deduplication_result['error']}")
            
            step4_output_path = deduplication_result['output_file']
            print(f"✅ Deduplication complete: {step4_output_path}")
            return step4_output_path
        
        # def _step4_deduplication(self, step3_input_path: str) -> str:
        #     """Deduplicate content"""
        #     print(f"\n🧹 STEP 4: Deduplicating content...")
            
        #     deduplicator = DocumentDeduplicator()
        #     deduplication_result = deduplicator.deduplicate_documents(
        #         input_file=step3_input_path,
        #         user_id=self.user_id,
        #         session_id=self.session_id
        #     )
            
        #     if not deduplication_result['success']:
        #         raise Exception(f"Deduplication failed: {deduplication_result['error']}")
            
        #     step4_output_path = deduplication_result['output_file']
        #     print(f"✅ Deduplication complete: {step4_output_path}")
        #     return step4_output_path
        
        # def _step5_create_embeddings(self, step4_input_path: str):
        #     """Create embeddings - append to existing vector DB"""
        #     print(f"\n📚 STEP 5: Creating/updating vector embeddings...")
            
        #     openai_api_key = os.getenv("OPENAI_API_KEY")
        #     if not openai_api_key:
        #         print("❌ OPENAI_API_KEY not found - SKIPPING EMBEDDINGS")
        #         return
            
        #     if not os.path.exists(step4_input_path):
        #         print(f"❌ Input file not found - SKIPPING EMBEDDINGS")
        #         return
            
        #     print(f"📁 Using input file: {step4_input_path}")
            
        #     # Try to append to existing vector DB
        #     try:
        #         # We need to modify the main_embedding_pipeline to support appending
        #         # For now, we'll create new embeddings
        #         embedding_processor = main_embedding_pipeline(
        #             openai_api_key=openai_api_key,
        #             user_id=self.user_id,
        #             session_id=self.session_id,
        #             storage_mode="main_corpus"  # Add this parameter if supported
        #         )
        #         print("✅ Embeddings created/updated successfully")
        #     except Exception as e:
        #         print(f"❌ Embedding failed: {e}")
        #         print("🔄 Trying manual embedding approach...")
        #         self._create_embeddings_manual(step4_input_path)

        def _step5_create_embeddings(self, step4_input_path: str):
            """Create embeddings - ALWAYS use manual method for bulk to go to main_corpus"""
            print(f"\n📚 STEP 5: Creating/updating vector embeddings in MAIN CORPUS...")
            
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                print("❌ OPENAI_API_KEY not found - SKIPPING EMBEDDINGS")
                return
            
            if not os.path.exists(step4_input_path):
                print(f"❌ Input file not found - SKIPPING EMBEDDINGS")
                return
            
            print(f"📁 Using input file: {step4_input_path}")
            
            # 🚨 CRITICAL: SKIP main_embedding_pipeline COMPLETELY for bulk uploads!
            # It ALWAYS stores in temp_uploads, but we want main_corpus for bulk
            
            print("🔄 Using manual embedding method to store in MAIN_CORPUS...")
            self._create_embeddings_manual(step4_input_path)
            
                
        # def _create_embeddings_manual(self, step4_input_path: str):
        #     """Manual embedding creation - FIXED"""
        #     try:
        #         from step5_four_vector_store_with_image_caption_and_text import DocumentProcessor
                
        #         openai_api_key = os.getenv("OPENAI_API_KEY")
        #         processor = DocumentProcessor(openai_api_key=openai_api_key)
                
        #         # ✅ FIXED: Use process_json_file instead of process_document
        #         documents = processor.process_json_file(
        #             json_file_path=step4_input_path,
        #             user_id=self.user_id,
        #             session_id=self.session_id
        #         )
                
        #         print(f"📊 Generated {len(documents)} documents for embedding")
                
        #         if documents:
        #             # ✅ FIXED: Store in main_corpus instead of temp_uploads
        #             try:
        #                 # Check if vector DB already exists
        #                 if os.path.exists(self.output_vector_db):
        #                     print(f"📁 Appending to existing vector DB: {self.output_vector_db}")
        #                     # Store in main_corpus for bulk upload
        #                     processor.store_in_chromadb(
        #                         documents, 
        #                         self.user_id, 
        #                         storage_mode="main_corpus",  # ✅ This goes to main_corpus
        #                         collection_name="document_embeddings"
        #                     )
        #                 else:
        #                     print(f"📁 Creating new vector DB: {self.output_vector_db}")
        #                     processor.store_in_chromadb(
        #                         documents, 
        #                         self.user_id, 
        #                         storage_mode="main_corpus",  # ✅ This goes to main_corpus
        #                         collection_name="document_embeddings"
        #                     )
                        
        #                 print(f"✅ Stored {len(documents)} documents in vector database (main_corpus)")
        #             except Exception as e:
        #                 print(f"❌ Failed to store in ChromaDB: {e}")
        #         else:
        #             print("⚠️ No documents to embed")
                    
        #     except Exception as e:
        #         print(f"❌ Manual embedding failed: {e}")
        #         print("💡 Continuing without embeddings for this batch")

        def _create_embeddings_manual(self, step4_input_path: str):
            """Manual embedding creation for bulk uploads - goes to main_corpus"""
            try:
                from step5_four_vector_store_with_image_caption_and_text import DocumentProcessor
                
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    print("❌ OPENAI_API_KEY not found")
                    return
                    
                print(f"🔧 Creating DocumentProcessor...")
                processor = DocumentProcessor(openai_api_key=openai_api_key)
                
                # Check if file exists
                if not os.path.exists(step4_input_path):
                    print(f"❌ File not found: {step4_input_path}")
                    return
                    
                file_size = os.path.getsize(step4_input_path)
                print(f"📄 Processing file: {step4_input_path} ({file_size} bytes)")
                
                # Process the JSON file
                print(f"🔄 Calling process_json_file...")
                documents = processor.process_json_file(
                    json_file_path=step4_input_path,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                
                if not documents:
                    print("⚠️ No documents generated from JSON file")
                    return
                    
                print(f"📊 Generated {len(documents)} documents for embedding")
                
                # 🎯 CRITICAL: Store in main_corpus, not temp_uploads!
                print(f"💾 Storing in MAIN_CORPUS: {self.output_vector_db}")
                collection = processor.store_in_chromadb(
                    documents, 
                    self.user_id, 
                    storage_mode="main_corpus",  # 🎯 THIS IS THE KEY!
                    collection_name="document_embeddings"
                )
                
                print(f"✅ Successfully stored {len(documents)} documents in MAIN CORPUS vector DB")
                print(f"📊 Collection now has {collection.count()} total documents")
                
            except Exception as e:
                print(f"❌ Manual embedding failed: {e}")
                import traceback
                traceback.print_exc()
                print("💡 Continuing without embeddings for this batch")

        
        def _step6_get_statistics(self) -> Dict[str, Any]:
            """Get final statistics"""
            print(f"\n📊 STEP 6: Collecting statistics...")
            
            # Count images
            final_image_path = f"images/{self.user_id}/main_corpus"
            image_count = 0
            if os.path.exists(final_image_path):
                image_files = [f for f in os.listdir(final_image_path) 
                             if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
                image_count = len(image_files)
            
            # Count vector documents
            vector_count = self._count_vector_documents()
            
            # Cleanup temp data
            self._cleanup_temp_data()
            
            return {
                'total_images': image_count,
                'vector_documents': vector_count,
                'vector_db_path': self.output_vector_db,
                'images_path': final_image_path,
                'user_id': self.user_id
            }
        
        def _count_vector_documents(self) -> int:
            """Count documents in vector database"""
            try:
                from step5_four_vector_store_with_image_caption_and_text import MultiUserChromaDBManager
                chroma_manager = MultiUserChromaDBManager()
                vector_stats = chroma_manager.get_user_stats(self.user_id)
                return vector_stats.get('main_corpus_documents', 0)
            except:
                return 0
        
        def _cleanup_temp_data(self):
            """Cleanup temporary processing data"""
            print(f"\n🧹 Cleaning up temporary data...")
            
            temp_dirs = [
                f"processed_json/{self.user_id}",
                f"unified_output/{self.user_id}",
                f"user_uploads/{self.user_id}",
                f"chroma_db/{self.user_id}/temp_uploads",  # Only cleanup temp, not main_corpus
            ]
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                        print(f"  ✅ Removed: {temp_dir}")
                    except Exception as e:
                        print(f"  ⚠️ Could not remove {temp_dir}: {e}")
    
    # Create builder and process files
    builder = BulkCorpusBuilder(user_id)
    result = builder.build_corpus(input_folder)
    
    return result








def process_bulk_pptx_files_with_progress(user_id: str, input_folder: str, pptx_files: List[str], tracker: BulkUploadProgressTracker):
    """Process multiple PPTX files with progress tracking"""
    
    print(f"🔄 Processing {len(pptx_files)} PPTX files for user: {user_id}")
    
    # Create a modified version of SimpleCorpusBuilder with progress tracking
    class BulkCorpusBuilderWithProgress:
        def __init__(self, user_id: str, tracker: BulkUploadProgressTracker):
            self.user_id = user_id
            self.tracker = tracker
            self.session_id = f"bulk_{uuid.uuid4().hex[:8]}"
            
            # Dynamic paths
            self.output_vector_db = f"chroma_db/{self.user_id}/main_corpus"
            self.output_images = f"images/{self.user_id}/main_corpus"
            
            # Create directories
            self._create_directories()
            
            print(f"🚀 Bulk Corpus Builder for: {self.user_id}")
        
        def _create_directories(self):
            """Create all necessary directories"""
            directories = [
                f"processed_json/{self.user_id}",
                f"unified_output/{self.user_id}",
                f"user_uploads/{self.user_id}",
                f"images/{self.user_id}/main_corpus",
                f"chroma_db/{self.user_id}/main_corpus",
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
        
        def build_corpus(self, input_folder: str) -> Dict[str, Any]:
            """Process all files with progress tracking"""
            try:
                # STEP 1: Parsing PPTX files
                self.tracker.update_step(self.tracker.Step.PARSING, 20, "Parsing PPTX files...")
                unified_json_path = self._step1_parse_pptx(input_folder)
                
                # Check if any files were processed
                if not os.path.exists(unified_json_path) or os.path.getsize(unified_json_path) == 0:
                    self.tracker.update_step(self.tracker.Step.PARSING, 100, "No PPTX files to process")
                    return {
                        'total_images': 0,
                        'vector_documents': 0,
                        'vector_db_path': self.output_vector_db,
                        'images_path': self.output_images,
                        'user_id': self.user_id,
                        'status': 'no_files_processed'
                    }
                
                self.tracker.update_step(self.tracker.Step.PARSING, 100, "PPTX parsing complete")
                
                # STEP 2: Preprocessing
                self.tracker.update_step(self.tracker.Step.PREPROCESSING, 0, "Preprocessing documents...")
                step2_output_path = self._step2_preprocessing(unified_json_path)
                self.tracker.update_step(self.tracker.Step.PREPROCESSING, 100, "Preprocessing complete")
                
                # STEP 3: Image captioning
                self.tracker.update_step(self.tracker.Step.IMAGE_CAPTIONING, 0, "Generating image captions...")
                step3_output_path = self._step3_image_captioning(step2_output_path)
                self.tracker.update_step(self.tracker.Step.IMAGE_CAPTIONING, 100, "Image captioning complete")
                
                # STEP 4: Deduplication
                self.tracker.update_step(self.tracker.Step.DEDUPLICATION, 0, "Deduplicating content...")
                step4_output_path = self._step4_deduplication(step3_output_path)
                self.tracker.update_step(self.tracker.Step.DEDUPLICATION, 100, "Deduplication complete")
                
                # STEP 5: Create embeddings
                self.tracker.update_step(self.tracker.Step.EMBEDDING, 0, "Creating vector embeddings...")
                self._step5_create_embeddings(step4_output_path)
                self.tracker.update_step(self.tracker.Step.EMBEDDING, 100, "Embeddings created")
                
                # STEP 6: Get statistics
                final_stats = self._step6_get_statistics()
                
                return final_stats
                
            except Exception as e:
                print(f"❌ Corpus building failed: {e}")
                import traceback
                traceback.print_exc()
                raise
        
        def _step1_parse_pptx(self, input_folder: str) -> str:
            """Parse all PPTX files"""
            # Update progress within parsing
            self.tracker.update_step(self.tracker.Step.PARSING, 30, "Parsing started...")
            
            parser = OptimizedPPTXParser(output_base_dir=f"unified_output/{self.user_id}", user_id=self.user_id)
            unified_output_path = parser.parse_ppt_folder(
                folder_path=input_folder,
                output_filename=f"unified_ppt_{self.session_id}.json"
            )
            
            self.tracker.update_step(self.tracker.Step.PARSING, 80, "PPTX parsing in progress...")
            return unified_output_path
        
        def _step2_preprocessing(self, unified_json_path: str) -> str:
            """Preprocess documents"""
            self.tracker.update_step(self.tracker.Step.PREPROCESSING, 30, "Loading documents...")
            
            with open(unified_json_path, 'r', encoding='utf-8') as f:
                unified_data = json.load(f)
            
            self.tracker.update_step(self.tracker.Step.PREPROCESSING, 60, "Processing documents...")
            
            preprocessor = JSONPreprocessor()
            processed_data = preprocessor.preprocess_documents(
                unified_data, 
                user_id=self.user_id, 
                session_id=self.session_id
            )
            
            step2_output_path = f"processed_json/{self.user_id}/step2_processed_{self.user_id}_{self.session_id}.json"
            preprocessor.save_processed_json(processed_data, step2_output_path)
            
            return step2_output_path
        
        def _step3_image_captioning(self, step2_input_path: str) -> str:
            """Generate image captions"""
            self.tracker.update_step(self.tracker.Step.IMAGE_CAPTIONING, 10, "Initializing image captioning...")
            
            caption_processor = ImageCaptionProcessor()
            step3_output_path = caption_processor.process_user_documents(
                user_id=self.user_id,
                session_id=self.session_id,
                step2_input_file=step2_input_path,
                batch_delay=0.1
            )
            
            return step3_output_path
        
        def _step4_deduplication(self, step3_input_path: str) -> str:
            """Deduplicate content"""
            self.tracker.update_step(self.tracker.Step.DEDUPLICATION, 30, "Analyzing content for duplicates...")
            
            deduplicator = DocumentDeduplicator()
            deduplication_result = deduplicator.deduplicate_documents(
                input_file=step3_input_path,
                user_id=self.user_id,
                session_id=self.session_id
            )
            
            if not deduplication_result['success']:
                if "No chunks found" in deduplication_result.get('error', ''):
                    print(f"⚠️ No chunks to deduplicate")
                    return step3_input_path
                else:
                    raise Exception(f"Deduplication failed: {deduplication_result['error']}")
            
            step4_output_path = deduplication_result['output_file']
            return step4_output_path
        
        def _step5_create_embeddings(self, step4_input_path: str):
            """Create embeddings"""
            self.tracker.update_step(self.tracker.Step.EMBEDDING, 20, "Preparing for embedding...")
            
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                print("❌ OPENAI_API_KEY not found - SKIPPING EMBEDDINGS")
                return
            
            if not os.path.exists(step4_input_path):
                print(f"❌ Input file not found - SKIPPING EMBEDDINGS")
                return
            
            self.tracker.update_step(self.tracker.Step.EMBEDDING, 40, "Processing documents for embedding...")
            
            # Manual embedding method
            try:
                from step5_four_vector_store_with_image_caption_and_text import DocumentProcessor
                
                processor = DocumentProcessor(openai_api_key=openai_api_key)
                
                self.tracker.update_step(self.tracker.Step.EMBEDDING, 60, "Generating embeddings...")
                documents = processor.process_json_file(
                    json_file_path=step4_input_path,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                
                if documents:
                    self.tracker.update_step(self.tracker.Step.EMBEDDING, 80, "Storing embeddings...")
                    processor.store_in_chromadb(
                        documents, 
                        self.user_id, 
                        storage_mode="main_corpus",
                        collection_name="document_embeddings"
                    )
                    
                    print(f"✅ Stored {len(documents)} documents in vector database")
                else:
                    print("⚠️ No documents to embed")
                    
            except Exception as e:
                print(f"❌ Manual embedding failed: {e}")
        
        def _step6_get_statistics(self) -> Dict[str, Any]:
            """Get final statistics"""
            self.tracker.update_step(self.tracker.Step.FINALIZING, 0, "Collecting statistics...")
            
            # Count images
            final_image_path = f"images/{self.user_id}/main_corpus"
            image_count = 0
            if os.path.exists(final_image_path):
                image_files = [f for f in os.listdir(final_image_path) 
                             if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
                image_count = len(image_files)
            
            # Count vector documents
            vector_count = self._count_vector_documents()
            
            # Cleanup temp data
            self._cleanup_temp_data()
            
            self.tracker.update_step(self.tracker.Step.FINALIZING, 50, "Finalizing...")
            
            return {
                'total_images': image_count,
                'vector_documents': vector_count,
                'vector_db_path': self.output_vector_db,
                'images_path': final_image_path,
                'user_id': self.user_id
            }
        
        def _count_vector_documents(self) -> int:
            """Count documents in vector database"""
            try:
                from step5_four_vector_store_with_image_caption_and_text import MultiUserChromaDBManager
                chroma_manager = MultiUserChromaDBManager()
                vector_stats = chroma_manager.get_user_stats(self.user_id)
                return vector_stats.get('main_corpus_documents', 0)
            except:
                return 0
        
        def _cleanup_temp_data(self):
            """Cleanup temporary processing data"""
            print(f"\n🧹 Cleaning up temporary data...")
            
            temp_dirs = [
                f"processed_json/{self.user_id}",
                f"unified_output/{self.user_id}",
                f"user_uploads/{self.user_id}",
                f"chroma_db/{self.user_id}/temp_uploads",
            ]
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        print(f"  ⚠️ Could not remove {temp_dir}: {e}")
    
    # Create builder and process files
    builder = BulkCorpusBuilderWithProgress(user_id, tracker)
    result = builder.build_corpus(input_folder)
    
    return result





@app.get("/get_modes", response_model=ModesResponse)
async def get_modes(user_id: str):
    """Get available presentation modes for the current user"""
    print(f"📋 Get modes request for user: {user_id}")
    
    try:
        # Check if user has uploaded files
        if user_id in user_sessions:
            session_info = user_sessions[user_id]
            has_uploaded_files = session_info['is_file_uploaded_by_user']
            available_modes = session_info['available_modes']
        else:
            # User hasn't uploaded anything yet
            has_uploaded_files = False
            available_modes = ["corpus_only"]
        
        print(f"✅ Mode check: uploaded_files={has_uploaded_files}, modes={available_modes}")
        
        return ModesResponse(
            user_id=user_id,
            available_modes=available_modes,
            has_uploaded_files=has_uploaded_files
        )
        
    except Exception as e:
        print(f"❌ Error getting modes for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting modes: {str(e)}")

@app.post("/generate_outline")
async def generate_outline(request: GenerateOutlineRequest):
    """Generate presentation outline and initial content"""
    print(f"🚀 Outline generation request: user={request.user_id}, mode={request.mode}, query='{request.query}'")
    
    try:
        # Validate request
        if not request.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        if not request.query:
            raise HTTPException(status_code=400, detail="query is required")
        
        # Clean previous outline to start fresh
        if request.user_id in user_outlines:
            del user_outlines[request.user_id]
            print(f"🧹 Cleared previous outline for user: {request.user_id}")
        
        # Check if user has uploaded files and validate mode
        has_uploaded_files = False
        session_id = None
        
        if request.user_id in user_sessions:
            session_info = user_sessions[request.user_id]
            has_uploaded_files = session_info['is_file_uploaded_by_user']
            session_id = session_info['session_id']
        
        # Validate mode selection
        if not has_uploaded_files and request.mode != "corpus_only":
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot use mode '{request.mode}'. No files uploaded by user. Please use 'corpus_only' mode."
            )
        
        if has_uploaded_files and request.mode not in ["uploaded_only", "uploaded_plus_corpus"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode '{request.mode}' for user with uploaded files. Use 'uploaded_only' or 'uploaded_plus_corpus'."
            )
        
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        print(f"🔧 Outline generation parameters:")
        print(f"   - User: {request.user_id}")
        print(f"   - Query: {request.query}")
        print(f"   - Mode: {request.mode}")
        print(f"   - Slides: {request.num_slides}")
        print(f"   - Style: {request.presentation_style}")
        print(f"   - Files uploaded: {has_uploaded_files}")
        print(f"   - Session ID: {session_id}")
        
        # Generate presentation using the complete pipeline
        print("🎨 Generating presentation outline...")
        result = create_complete_presentation_pipeline(
            query=request.query,
            user_id=request.user_id,
            is_file_uploaded_by_user=has_uploaded_files,
            mode=request.mode,
            num_slides=request.num_slides,
            presentation_style=request.presentation_style,
            openai_api_key=openai_api_key,
            save_package=True,
            merge_after_success=False,
            session_id=session_id  # 🆕 ADD THIS LINE
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=f"Presentation generation failed: {result['error']}")
        
        # Get the saved JSON file path from step6 result
        saved_json_path = None
        if "files" in result and result["files"]:
            saved_json_path = result["files"].get("presentation_file")
        
        if not saved_json_path or not os.path.exists(saved_json_path):
            raise HTTPException(status_code=500, detail="Outline file was not saved properly")
        
        # Store the outline data in memory for template generation
        user_outlines[request.user_id] = {
            'full_outline': result['outline'],
            'full_presentation': result['presentation'],
            'files': result.get('files'),
            'saved_json_path': saved_json_path,
            'timestamp': time.time(),
            'query': request.query,
            'mode': request.mode,
            'presentation_style': request.presentation_style,
            'session_id': session_id
        }
        
        # Prepare simplified slides for response
        presentation = result['presentation']
        simplified_slides = []
        for slide in presentation.get('slides', []):
            simplified_slide = {
                'slide_number': slide.get('slide_number'),
                'slide_title': slide.get('slide_title', ''),
                'slide_type': slide.get('slide_type', 'content'),
                'content': slide.get('content', ''),
                'key_points': slide.get('key_points', []),
                'images': [
                    {
                        'image_path': img.get('image_path', ''),
                        'caption': img.get('caption', ''),
                        'similarity_score': img.get('similarity_score', 0)
                    }
                    for img in slide.get('images', [])
                ]
            }
            simplified_slides.append(simplified_slide)
        
        # Prepare response with image URLs
        response_data = {
            'presentation_title': presentation.get('presentation_title', 'Professional Presentation'),
            'total_slides': presentation.get('total_slides', 0),
            'presentation_style': presentation.get('presentation_style', 'corporate'),
            'slides': simplified_slides,
            'user_id': request.user_id,
            'search_mode': request.mode,
            'status': 'success',
            'generated_at': time.time()
        }

        # Convert image paths to URLs
        response_data['slides'] = convert_image_paths_to_urls(
            simplified_slides, 
            request.user_id, 
            request.mode, 
            session_id
        )
        
        print(f"✅ Outline generation completed successfully for user: {request.user_id}")
        print(f"   - Title: {response_data['presentation_title']}")
        print(f"   - Slides: {response_data['total_slides']}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Outline generation failed for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Outline generation failed: {str(e)}")

@app.get("/get_outline")
async def get_outline(user_id: str):
    """Retrieve the latest generated outline for a user"""
    print(f"📋 Get outline request for user: {user_id}")
    
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        if user_id not in user_outlines:
            raise HTTPException(status_code=404, detail="No outline found for this user. Please generate an outline first.")
        
        outline_data = user_outlines[user_id]
        presentation = outline_data['full_presentation']
        
        simplified_slides = []
        for slide in presentation.get('slides', []):
            simplified_slide = {
                'slide_number': slide.get('slide_number'),
                'slide_title': slide.get('slide_title', ''),
                'slide_type': slide.get('slide_type', 'content'),
                'content': slide.get('content', ''),
                'key_points': slide.get('key_points', []),
                'images': [
                    {
                        'image_path': img.get('image_path', ''),
                        'caption': img.get('caption', ''),
                        'similarity_score': img.get('similarity_score', 0)
                    }
                    for img in slide.get('images', [])
                ]
            }
            simplified_slides.append(simplified_slide)
        
        response_data = {
            'presentation_title': presentation.get('presentation_title', 'Professional Presentation'),
            'total_slides': presentation.get('total_slides', 0),
            'presentation_style': presentation.get('presentation_style', 'corporate'),
            'slides': simplified_slides,
            'user_id': user_id,
            'original_query': outline_data.get('query', ''),
            'search_mode': outline_data.get('mode', ''),
            'status': 'retrieved',
            'generated_at': outline_data.get('timestamp')
        }

        # Convert image paths to URLs
        response_data['slides'] = convert_image_paths_to_urls(
            simplified_slides, 
            user_id, 
            outline_data.get('mode', 'corpus_only'), 
            outline_data.get('session_id')
        )
        
        print(f"✅ Outline retrieved for user: {user_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving outline for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving outline: {str(e)}")

@app.get("/get_template_options")
async def get_template_options():
    """Get available template options for the UI"""
    print("📋 Get template options request")
    
    try:
        templates_list = []
        for template_id, template_data in available_templates.items():
            image_path = template_data["image_path"]
            if not os.path.exists(image_path):
                print(f"⚠️ Template image not found: {image_path}")
                continue
                
            templates_list.append({
                "id": template_data["id"],
                "name": template_data["name"],
                "description": template_data["description"],
                "image_url": f"/template-images/{template_id}",
                "template_file": template_data.get("template_file")
            })
        
        print(f"✅ Returning {len(templates_list)} available templates")
        return {
            "templates": templates_list,
            "total_templates": len(templates_list)
        }
    except Exception as e:
        print(f"❌ Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting templates: {str(e)}")

@app.post("/generate_default_template")
async def generate_default_template(request: GenerateDefaultTemplateRequest):
    """Generate presentation using a default template"""
    print(f"🎨 Default template generation request: user={request.user_id}, template={request.template_id}")
    
    try:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        if request.template_id not in available_templates:
            raise HTTPException(status_code=400, detail=f"Template {request.template_id} not found")
        
        # Check if user has a generated outline
        if request.user_id not in user_outlines:
            raise HTTPException(
                status_code=400, 
                detail="No outline found. Please generate an outline first using /generate_outline"
            )
        
        outline_data = user_outlines[request.user_id]
        session_id = outline_data.get('session_id')
        storage = StorageManager(request.user_id)
        
        # Generate presentation ID
        presentation_id = f"pres_{uuid.uuid4().hex[:8]}"
        
        # Create output directory
        presentations_dir = f"generated_presentations/{request.user_id}"
        os.makedirs(presentations_dir, exist_ok=True)
        
        # Generate output filename
        # title_slug = outline_data['full_presentation']['presentation_title'].lower().replace(" ", "_")[:30]
        # output_filename = f"{presentation_id}_{title_slug}.pptx"
        output_filename = f"{presentation_id}.pptx"
        output_path = os.path.join(presentations_dir, output_filename)
        
        print(f"📊 Generating presentation with template {request.template_id}...")
        print(f"   - Output path: {output_path}")
        print(f"   - Session ID: {session_id}")
        
        # Generate presentation using default template
        presentation_path = await generate_with_default_template(
            request.user_id, 
            request.template_id, 
            outline_data, 
            output_path
        )
        
        # Convert to PDF
        print("🔄 Converting PPT to PDF...")
        pdf_path = await convert_ppt_to_pdf_windows(presentation_path)
        
        # SUCCESSFUL GENERATION - MERGE TEMP TO MAIN CORPUS
        print("🔄 Presentation generation successful - merging temp data to main corpus...")
        if session_id:
            merged_count = storage.merge_temp_to_main(session_id)
            print(f"✅ Merged {merged_count} items from temp to main corpus")
        
        # CLEANUP USER SESSION FROM MEMORY
        print("🧹 Cleaning up user session from memory...")
        if request.user_id in user_sessions:
            del user_sessions[request.user_id]
            print("✅ User session cleaned up from memory")
        
        if request.user_id in user_outlines:
            del user_outlines[request.user_id]
            print("✅ User outline cleaned up from memory")
        
        # Store presentation info
        user_presentations[presentation_id] = {
            "user_id": request.user_id,
            "presentation_path": presentation_path,
            "pdf_path": pdf_path,
            "template_used": request.template_id,
            "generated_at": time.time(),
            "outline_data": outline_data
        }
        
        print(f"✅ Presentation generation completed: {presentation_id}")
        print(f"   - PPT: {presentation_path}")
        print(f"   - PDF: {pdf_path}")

        return PresentationResponse(
            user_id=request.user_id,
            presentation_id=presentation_id,
            presentation_path=presentation_path,
            pdf_path=pdf_path,
            template_used=request.template_id,
            status="generated"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generating presentation with default template: {e}")
        # Cleanup on error
        if 'request' in locals() and 'session_id' in locals():
            storage = StorageManager(request.user_id)
            storage.cleanup_temp_data(session_id)
        if 'request' in locals() and request.user_id in user_sessions:
            del user_sessions[request.user_id]
        if 'request' in locals() and request.user_id in user_outlines:
            del user_outlines[request.user_id]
        raise HTTPException(status_code=500, detail=f"Error generating presentation with default template: {str(e)}")

@app.post("/generate_custom_template")
async def generate_custom_template(
    user_id: str = Form(...),
    template_file: UploadFile = File(...)
):
    """Generate presentation using a custom uploaded template"""
    print(f"🎨 Custom template generation request for user: {user_id}")
    
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Validate file type
        if not template_file.filename.endswith('.pptx'):
            raise HTTPException(status_code=400, detail="Only .pptx files are supported")
        
        # Check if user has a generated outline
        if user_id not in user_outlines:
            raise HTTPException(
                status_code=400, 
                detail="No outline found. Please generate an outline first using /generate_outline"
            )
        
        outline_data = user_outlines[user_id]
        session_id = outline_data.get('session_id')
        storage = StorageManager(user_id)
        
        # Create user templates directory
        user_templates_dir = f"user_templates/{user_id}"
        os.makedirs(user_templates_dir, exist_ok=True)
        
        # Save uploaded template
        template_id = f"custom_{uuid.uuid4().hex[:8]}"
        template_filename = f"{template_id}_{template_file.filename}"
        template_path = os.path.join(user_templates_dir, template_filename)
        
        with open(template_path, "wb") as buffer:
            shutil.copyfileobj(template_file.file, buffer)
        
        print(f"💾 Saved custom template: {template_path}")
        
        # Generate presentation ID
        presentation_id = f"pres_{uuid.uuid4().hex[:8]}"
        
        # Create output directory
        presentations_dir = f"generated_presentations/{user_id}"
        os.makedirs(presentations_dir, exist_ok=True)
        
        # Generate output filename
        # title_slug = outline_data['full_presentation']['presentation_title'].lower().replace(" ", "_")[:30]
        # output_filename = f"{presentation_id}_{title_slug}.pptx"
        output_filename = f"{presentation_id}.pptx"

        output_path = os.path.join(presentations_dir, output_filename)
        
        print(f"📊 Generating presentation with custom template...")
        print(f"   - Output path: {output_path}")
        print(f"   - Session ID: {session_id}")
        
        # Generate presentation using custom template
        presentation_path = await generate_with_custom_template(
            user_id,
            template_path,
            outline_data,
            output_path
        )
        
        # Convert to PDF
        print("🔄 Converting PPT to PDF...")
        pdf_path = await convert_ppt_to_pdf_windows(presentation_path)
        
        # SUCCESSFUL GENERATION - MERGE TEMP TO MAIN CORPUS
        print("🔄 Presentation generation successful - merging temp data to main corpus...")
        if session_id:
            merged_count = storage.merge_temp_to_main(session_id)
            print(f"✅ Merged {merged_count} items from temp to main corpus")
        
        # CLEANUP USER SESSION FROM MEMORY
        print("🧹 Cleaning up user session from memory...")
        if user_id in user_sessions:
            del user_sessions[user_id]
            print("✅ User session cleaned up from memory")
        
        if user_id in user_outlines:
            del user_outlines[user_id]
            print("✅ User outline cleaned up from memory")
        
        # Store presentation info
        user_presentations[presentation_id] = {
            "user_id": user_id,
            "presentation_path": presentation_path,
            "pdf_path": pdf_path,
            "template_used": "custom_template",
            "generated_at": time.time(),
            "outline_data": outline_data
        }
        
        print(f"✅ Custom template presentation completed: {presentation_id}")
        print(f"   - PPT: {presentation_path}")
        print(f"   - PDF: {pdf_path}")

        return PresentationResponse(
            user_id=user_id,
            presentation_id=presentation_id,
            presentation_path=presentation_path,
            pdf_path=pdf_path,
            template_used="custom_template",
            status="generated"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generating presentation with custom template: {e}")
        # Cleanup on error
        if 'session_id' in locals():
            storage = StorageManager(user_id)
            storage.cleanup_temp_data(session_id)
        if user_id in user_sessions:
            del user_sessions[user_id]
        if user_id in user_outlines:
            del user_outlines[user_id]
        raise HTTPException(status_code=500, detail=f"Error generating presentation with custom template: {str(e)}")

# Template generation helper functions (unchanged from your original)
async def generate_with_default_template(user_id: str, template_id: str, outline_data: Dict, output_path: str) -> str:
    """Generate presentation using default template"""
    try:
        # First, adapt the JSON structure for the template
        adapted_json_path = f"temp_adapted_{user_id}_{uuid.uuid4().hex[:8]}.json"
        
        # Save outline data to temporary file
        temp_outline_path = _save_temp_outline(outline_data)
        
        # Template 1
        if template_id == "template1":
            from template1 import JSONAdapter, DynamicLayoutPresentationGenerator
            JSONAdapter.adapt_json_for_ppt(temp_outline_path, adapted_json_path)
            generator = DynamicLayoutPresentationGenerator(adapted_json_path)
            generator.create_presentation(output_path)
            
        # Template 2  
        elif template_id == "template2":
            from template2 import JSONAdapter, DynamicLayoutPresentationGenerator
            JSONAdapter.adapt_json_for_ppt(temp_outline_path, adapted_json_path)
            generator = DynamicLayoutPresentationGenerator(adapted_json_path)
            generator.create_presentation(output_path)
            
        # ADD YOUR TWO NEW TEMPLATES HERE:
        elif template_id == "template3":
            from template3 import JSONAdapter, ProfessionalBluePresentationGenerator
            JSONAdapter.adapt_json_for_ppt(temp_outline_path, adapted_json_path)
            generator = ProfessionalBluePresentationGenerator(adapted_json_path)
            generator.create_presentation(output_path)
            
        elif template_id == "template4":
            from template4 import JSONAdapter, MinimalDarkPresentationGenerator  
            JSONAdapter.adapt_json_for_ppt(temp_outline_path, adapted_json_path)
            generator = MinimalDarkPresentationGenerator(adapted_json_path)
            generator.create_presentation(output_path)
            
        else:
            raise HTTPException(status_code=400, detail=f"Template {template_id} not found")
        
        # Cleanup temp files
        if os.path.exists(temp_outline_path):
            os.remove(temp_outline_path)
        if os.path.exists(adapted_json_path):
            os.remove(adapted_json_path)
        
        print(f"✅ Presentation generated with {template_id}: {output_path}")
        return output_path
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating with default template: {str(e)}")

async def generate_with_custom_template(user_id: str, template_path: str, outline_data: Dict, output_path: str) -> str:
    """Generate presentation using custom uploaded template"""
    try:
        # Import your custom template generator
        from upload_file import generate_presentation_with_custom_template
        
        # Save outline data to temporary JSON file
        temp_json_path = f"temp_outline_{user_id}_{uuid.uuid4().hex[:8]}.json"
        with open(temp_json_path, 'w', encoding='utf-8') as f:
            json.dump(outline_data['full_presentation'], f, indent=2, ensure_ascii=False)
        
        # Generate presentation using custom template - PASS THE TEMPLATE PATH DIRECTLY
        generate_presentation_with_custom_template(
            json_path=temp_json_path,
            template_path=template_path,  # Use the uploaded template path
            output_path=output_path
        )
        
        # Cleanup temp JSON file
        if os.path.exists(temp_json_path):
            os.remove(temp_json_path)
        
        print(f"✅ Presentation generated with custom template: {output_path}")
        return output_path
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating with custom template: {str(e)}")

def _save_temp_outline(outline_data: Dict) -> str:
    """Save outline data to temporary JSON file"""
    temp_path = f"temp_outline_{uuid.uuid4().hex[:8]}.json"
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(outline_data['full_presentation'], f, indent=2, ensure_ascii=False)
    return temp_path

# PDF conversion (unchanged from your original)
async def convert_ppt_to_pdf_linux(ppt_path: str) -> str:
    """Convert PowerPoint to PDF using LibreOffice (Linux compatible)"""
    try:
        pdf_path = ppt_path.replace('.pptx', '.pdf')
        
        # If PDF already exists, return it
        if os.path.exists(pdf_path):
            return pdf_path
            
        print(f"🔄 Converting PPT to PDF using LibreOffice: {ppt_path} -> {pdf_path}")
        
        # Method 1: Try using LibreOffice command line
        try:
            # Check if LibreOffice is available
            result = os.system("which libreoffice > /dev/null 2>&1")
            if result == 0:
                # Use LibreOffice to convert
                cmd = f"libreoffice --headless --convert-to pdf --outdir {os.path.dirname(pdf_path)} {ppt_path}"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    print(f"✅ PDF conversion successful using LibreOffice: {pdf_path}")
                    return pdf_path
                else:
                    print(f"⚠️ LibreOffice conversion failed: {stderr.decode()}")
            else:
                print("⚠️ LibreOffice not found")
        except Exception as e:
            print(f"⚠️ LibreOffice conversion error: {e}")
        
        # Method 2: Try using unoconv (alternative)
        try:
            result = os.system("which unoconv > /dev/null 2>&1")
            if result == 0:
                cmd = f"unoconv -f pdf {ppt_path}"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    print(f"✅ PDF conversion successful using unoconv: {pdf_path}")
                    return pdf_path
                else:
                    print(f"⚠️ unoconv conversion failed: {stderr.decode()}")
            else:
                print("⚠️ unoconv not found")
        except Exception as e:
            print(f"⚠️ unoconv conversion error: {e}")
        
        # Fallback: return the PPT path if conversion fails
        print("⚠️ No PDF conversion tool available, returning PPT file")
        return ppt_path
        
    except Exception as e:
        print(f"⚠️ PDF conversion failed: {e}")
        return ppt_path
    

async def convert_ppt_to_pdf_windows(ppt_path: str) -> str:
    """
    Convert PowerPoint to PDF on Windows using Microsoft Office
    """
    try:
        pdf_path = ppt_path.replace('.pptx', '.pdf')
        
        # If PDF already exists, return it
        if os.path.exists(pdf_path):
            print(f"✅ PDF already exists: {pdf_path}")
            return pdf_path
            
        print(f"🔄 Converting PPT to PDF on Windows: {ppt_path}")
        
        # Method 1: Microsoft PowerPoint
        try:
            import win32com.client
            
            # Initialize PowerPoint
            powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            # powerpoint.Visible = 0  # Run in background
            
            # Open the presentation
            presentation = powerpoint.Presentations.Open(os.path.abspath(ppt_path))
            
            # Save as PDF (32 = ppSaveAsPDF)
            presentation.SaveAs(os.path.abspath(pdf_path), 32)
            
            # Clean up
            presentation.Close()
            powerpoint.Quit()
            
            print(f"✅ PDF conversion successful: {pdf_path}")
            return pdf_path
            
        except ImportError:
            print("❌ pywin32 not installed. Run: pip install pywin32")
        except Exception as e:
            print(f"❌ PowerPoint conversion failed: {e}")
        
        # Method 2: Fallback - return original PPT
        print("⚠️ Returning original PPT file (no PDF conversion available)")
        return ppt_path
        
    except Exception as e:
        print(f"❌ PDF conversion error: {e}")
        return ppt_path

# # Additional endpoints (unchanged from your original for frontend compatibility)
# @app.get("/get_presentation")
# async def get_presentation(presentation_id: str, user_id: str):
#     """Get generated presentation file (PDF if available, else PPT)"""
#     try:
#         if not presentation_id or not user_id:
#             raise HTTPException(status_code=400, detail="presentation_id and user_id are required")
        
#         # Check if presentation exists
#         if presentation_id not in user_presentations:
#             raise HTTPException(status_code=404, detail="Presentation not found")
        
#         presentation_data = user_presentations[presentation_id]
        
#         # Verify ownership
#         if presentation_data["user_id"] != user_id:
#             raise HTTPException(status_code=403, detail="Presentation does not belong to this user")
        
#         # Try to return PDF first, fallback to PPT
#         file_path = presentation_data["pdf_path"]
#         media_type = 'application/pdf'
        
#         # If PDF doesn't exist or is actually the PPT file (fallback), return PPT
#         if not os.path.exists(file_path) or file_path.endswith('.pptx'):
#             file_path = presentation_data["presentation_path"]
#             media_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        
#         if not os.path.exists(file_path):
#             raise HTTPException(status_code=404, detail="Presentation file not found")
        
#         # Return the file
#         return FileResponse(
#             path=file_path,
#             filename=os.path.basename(file_path),
#             media_type=media_type
#         )
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error retrieving presentation: {str(e)}")

# @app.get("/get_presentation")
# async def get_presentation(presentation_id: str, user_id: str, file_type: str = "both"):
#     """Get generated presentation files (both PPT and PDF if available)"""
#     try:
#         if not presentation_id or not user_id:
#             raise HTTPException(status_code=400, detail="presentation_id and user_id are required")
        
#         # Check if presentation exists
#         if presentation_id not in user_presentations:
#             raise HTTPException(status_code=404, detail="Presentation not found")
        
#         presentation_data = user_presentations[presentation_id]
        
#         # Verify ownership
#         if presentation_data["user_id"] != user_id:
#             raise HTTPException(status_code=403, detail="Presentation does not belong to this user")
        
#         ppt_path = presentation_data["presentation_path"]
#         pdf_path = presentation_data["pdf_path"]
        
#         # Check which files exist
#         ppt_exists = os.path.exists(ppt_path) and ppt_path.endswith('.pptx')
#         pdf_exists = os.path.exists(pdf_path) and pdf_path.endswith('.pdf')
        
#         if not ppt_exists and not pdf_exists:
#             raise HTTPException(status_code=404, detail="No presentation files found")
        
#         # Handle different file type requests
#         if file_type == "ppt" and ppt_exists:
#             return FileResponse(
#                 path=ppt_path,
#                 filename=os.path.basename(ppt_path),
#                 media_type='application/vnd.openxmlformats-officedocument.presentationml.presentation'
#             )
        
#         elif file_type == "pdf" and pdf_exists:
#             return FileResponse(
#                 path=pdf_path,
#                 filename=os.path.basename(pdf_path),
#                 media_type='application/pdf'
#             )
        
#         elif file_type == "both":
#             # Return both files as a zip or provide download URLs
#             return {
#                 "status": "success",
#                 "user_id": user_id,
#                 "presentation_id": presentation_id,
#                 "files": {
#                     "ppt": {
#                         "filename": os.path.basename(ppt_path),
#                         "download_url": f"/get_presentation?presentation_id={presentation_id}&user_id={user_id}&file_type=ppt",
#                         "exists": ppt_exists,
#                         "size": os.path.getsize(ppt_path) if ppt_exists else 0
#                     },
#                     "pdf": {
#                         "filename": os.path.basename(pdf_path),
#                         "download_url": f"/get_presentation?presentation_id={presentation_id}&user_id={user_id}&file_type=pdf", 
#                         "exists": pdf_exists,
#                         "size": os.path.getsize(pdf_path) if pdf_exists else 0
#                     }
#                 },
#                 "message": "Use download_urls to get individual files"
#             }
        
#         else:
#             raise HTTPException(status_code=400, detail=f"Requested file type '{file_type}' not available")
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error retrieving presentation: {str(e)}")


@app.get("/get_presentation")
async def get_presentation(presentation_id: str, user_id: str, file_type: str = "pdf"):
    """Get generated presentation files - PDF or PPT"""
    try:
        if not presentation_id or not user_id:
            raise HTTPException(status_code=400, detail="presentation_id and user_id are required")
        
        # Check if presentation exists
        if presentation_id not in user_presentations:
            raise HTTPException(status_code=404, detail="Presentation not found")
        
        presentation_data = user_presentations[presentation_id]
        
        # Verify ownership
        if presentation_data["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Presentation does not belong to this user")
        
        # Handle file type selection
        if file_type == "ppt":
            file_path = presentation_data["presentation_path"]
            media_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            filename = os.path.basename(file_path)
        elif file_type == "pdf":
            file_path = presentation_data["pdf_path"]
            media_type = 'application/pdf'
            filename = os.path.basename(file_path)
        else:
            raise HTTPException(status_code=400, detail="file_type must be 'ppt' or 'pdf'")
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"{file_type.upper()} file not found")
        
        # Return the file
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving presentation: {str(e)}")

@app.get("/get_user_presentations")
async def get_user_presentations(user_id: str):
    """Get list of all presentations generated by a user"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        user_pres_list = []
        for pres_id, pres_data in user_presentations.items():
            if pres_data["user_id"] == user_id:
                ppt_size = 0
                pdf_size = 0
                if os.path.exists(pres_data["presentation_path"]):
                    ppt_size = os.path.getsize(pres_data["presentation_path"])
                if os.path.exists(pres_data["pdf_path"]) and pres_data["pdf_path"].endswith('.pdf'):
                    pdf_size = os.path.getsize(pres_data["pdf_path"])
                
                user_pres_list.append({
                    "presentation_id": pres_id,
                    "presentation_path": pres_data["presentation_path"],
                    "pdf_path": pres_data["pdf_path"],
                    "template_used": pres_data["template_used"],
                    "generated_at": pres_data["generated_at"],
                    "ppt_size": ppt_size,
                    "pdf_size": pdf_size,
                    "has_pdf": pdf_size > 0 and pres_data["pdf_path"].endswith('.pdf')
                })
        
        return {
            "user_id": user_id,
            "presentations": user_pres_list,
            "total_presentations": len(user_pres_list)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user presentations: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Presentation Generation API"}

@app.get("/user_info/{user_id}")
async def get_user_info(user_id: str):
    """Get user session information"""
    try:
        user_data = {
            "user_id": user_id,
            "has_uploaded_files": False,
            "available_modes": ["corpus_only"],
            "has_generated_outline": user_id in user_outlines,
            "total_presentations": 0
        }
        
        if user_id in user_sessions:
            session_info = user_sessions[user_id]
            user_data.update({
                "has_uploaded_files": session_info['is_file_uploaded_by_user'],
                "available_modes": session_info['available_modes'],
                "session_id": session_info['session_id'],
                "uploaded_files_count": session_info.get('files_processed', False)
            })
        
        # Count user presentations
        user_pres_count = sum(1 for pres_data in user_presentations.values() if pres_data["user_id"] == user_id)
        user_data["total_presentations"] = user_pres_count
        
        return user_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user info: {str(e)}")

@app.delete("/clear_user_session/{user_id}")
async def clear_user_session(user_id: str):
    """Clear user session, outlines, and presentations"""
    try:
        # Clear memory
        if user_id in user_sessions:
            storage = StorageManager(user_id)
            session_id = user_sessions[user_id].get('session_id')
            if session_id:
                storage.cleanup_temp_data(session_id)
            del user_sessions[user_id]
        
        if user_id in user_outlines:
            del user_outlines[user_id]
        
        # Clear user presentations
        presentations_to_remove = []
        for pres_id, pres_data in user_presentations.items():
            if pres_data["user_id"] == user_id:
                presentations_to_remove.append(pres_id)
        
        for pres_id in presentations_to_remove:
            del user_presentations[pres_id]
        
        print(f"✅ Cleared all session data for user: {user_id}")
        return {"message": f"Session, outlines and presentations cleared for user {user_id}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Enhanced Presentation Generation API...")
    print("📚 Available endpoints:")
    print("   POST /upload_file - Upload and process files (files optional)")
    print("   GET  /get_modes - Get available presentation modes")
    print("   POST /generate_outline - Generate presentation outline")
    print("   GET  /get_outline - Retrieve saved outline")
    print("   GET  /get_template_options - Get available templates")
    print("   POST /generate_default_template - Generate with default template")
    print("   POST /generate_custom_template - Generate with custom template")
    print("   GET  /get_presentation - Download presentation (PDF if available)")
    print("   GET  /get_user_presentations - List user presentations")
    print("   GET  /health - Health check")
    print("   GET  /user_info/{user_id} - Get user session info")
    print("   DELETE /clear_user_session/{user_id} - Clear user session")
    print("\n🔧 FIXES APPLIED:")
    print("   ✅ Fixed STEP 5 embedding call (removed vector_store_path parameter)")
    print("   ✅ Enhanced storage integration with your StorageManager")
    print("   ✅ Fixed image path resolution for all modes")
    print("   ✅ Added comprehensive step-by-step logging")
    print("   ✅ Proper temp→main corpus merge after presentation generation")
    print("   ✅ Immediate cleanup after successful generation")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)