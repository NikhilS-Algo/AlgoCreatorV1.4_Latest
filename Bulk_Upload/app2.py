# app.py for Bulk Upload Service (running on separate port)
import os
import json
import time
import shutil
import zipfile
import uuid
import threading
import gc
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
# Add these imports if not already present
import chromadb
from chromadb.config import Settings

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import required components
from unified_ppt_parser_optimized import OptimizedPPTXParser
from Step2_Processing_unified_document_json_file_for_vector_store import JSONPreprocessor
from step3_Image_caption_generator_Openai import ImageCaptionProcessor
from step4_deduplicate_chunks_and_images import DocumentDeduplicator
from step5_four_vector_store_with_image_caption_and_text import DocumentProcessor, MultiUserChromaDBManager

# Initialize FastAPI app
app = FastAPI(title="Bulk Upload Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for progress tracking
bulk_upload_progress = {}
bulk_upload_lock = threading.Lock()
bulk_upload_tasks = {}


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
        
        overall_progress = 0
        if current_step == self.Step.COMPLETE:
            overall_progress = 100
        elif current_step == self.Step.FAILED:
            overall_progress = 0
        else:
            completed_weight = 0
            total_weight = sum(self.STEP_WEIGHTS.values())
            
            for step, weight in self.STEP_WEIGHTS.items():
                if step.value == current_step.value:
                    completed_weight += (step_progress / 100) * weight
                    break
                else:
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


def process_bulk_upload_background(user_id: str, zip_file_path: str, tracker: BulkUploadProgressTracker, task_id: str):
    """Process bulk upload in background with progress tracking"""
    print(f"🔄 Starting background processing for task: {task_id}")
    
    with bulk_upload_lock:
        if task_id not in bulk_upload_progress:
            print(f"⚠️ Task {task_id} not found, might have been cleaned up")
            return
    
    temp_dir = None
    temp_save_dir = os.path.dirname(zip_file_path)
    try:
        # STEP 1: Extract ZIP file
        tracker.update_step(tracker.Step.EXTRACTING, 0, "Extracting ZIP file...")
        
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


def process_bulk_pptx_files_with_progress(user_id: str, input_folder: str, pptx_files: List[str], tracker: BulkUploadProgressTracker):
    """Process multiple PPTX files with progress tracking"""
    
    print(f"🔄 Processing {len(pptx_files)} PPTX files for user: {user_id}")
    
    class BulkCorpusBuilderWithProgress:
        def __init__(self, user_id: str, tracker: BulkUploadProgressTracker):
            self.user_id = user_id
            self.tracker = tracker
            self.session_id = f"bulk_{uuid.uuid4().hex[:8]}"
            
            # 🚨 Clean up any OLD data before starting
            self._cleanup_old_data_before_start()
            
            # Dynamic paths
            self.output_vector_db = f"chroma_db/{self.user_id}/main_corpus"
            self.output_images = f"images/{self.user_id}/main_corpus"
            
            # Create directories
            self._create_directories()

        def _cleanup_old_bulk_data(self):
            """Clean up old Bulk_Upload data before starting new processing"""
            print(f"🧹 Cleaning old Bulk_Upload data for user: {self.user_id}")
            
            paths_to_clean = [
                f"chroma_db/{self.user_id}/main_corpus",
                f"images/{self.user_id}/main_corpus",
                f"processed_json/{self.user_id}",
                f"unified_output/{self.user_id}",
                f"user_uploads/{self.user_id}",
            ]
            
            for path in paths_to_clean:
                if os.path.exists(path):
                    try:
                        shutil.rmtree(path)
                        print(f"   ✅ Cleaned: {path}")
                    except Exception as e:
                        print(f"   ⚠️ Could not clean {path}: {e}")
        
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

        def _close_chromadb_connections(self, db_path: str):
            """Forcefully close any open ChromaDB connections to release file locks"""
            print(f"🔒 Attempting to close ChromaDB connections for: {db_path}")
            
            # Method 1: Try to close ChromaDB clients gracefully
            try:
                # Check if there's a chroma.sqlite3 file
                sqlite_path = os.path.join(db_path, "chroma.sqlite3")
                if os.path.exists(sqlite_path):
                    print(f"   Found SQLite database: {sqlite_path}")
                    
                    # Try to close any open SQLite connections
                    try:
                        # Force close any open SQLite connections
                        sqlite3.connect(sqlite_path).close()
                        print("   ✅ Closed SQLite connection")
                    except Exception as e:
                        print(f"   ⚠️ Could not close SQLite: {e}")
            except Exception as e:
                print(f"   ⚠️ Error checking SQLite: {e}")
            
            # Method 2: Force garbage collection to release any dangling references
            gc.collect()
            
            # Method 3: Try to delete the directory with retries
            if os.path.exists(db_path):
                for attempt in range(3):
                    try:
                        if attempt > 0:
                            print(f"   Retry {attempt + 1}/3...")
                            time.sleep(1)
                        
                        # Try to remove individual files first
                        for root, dirs, files in os.walk(db_path, topdown=False):
                            for name in files:
                                try:
                                    os.unlink(os.path.join(root, name))
                                except:
                                    pass
                        
                        # Now remove directories
                        for root, dirs, files in os.walk(db_path, topdown=False):
                            for name in dirs:
                                try:
                                    os.rmdir(os.path.join(root, name))
                                except:
                                    pass
                        
                        # Finally remove the main directory
                        shutil.rmtree(db_path, ignore_errors=True)
                        print(f"   ✅ Successfully cleaned ChromaDB directory")
                        break
                        
                    except Exception as e:
                        if attempt == 2:
                            print(f"   ❌ Failed to clean ChromaDB after 3 attempts")
                        else:
                            print(f"   ⚠️ Attempt {attempt + 1} failed: {e}")
        
        def build_corpus(self, input_folder: str) -> Dict[str, Any]:
            """Process all files with progress tracking - DIRECT TO GENERATION"""
            try:
                # STEP 1: Parsing PPTX files
                self.tracker.update_step(self.tracker.Step.PARSING, 20, "Parsing PPTX files...")
                unified_json_path = self._step1_parse_pptx(input_folder)
                
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
                
                # STEP 5: Create embeddings DIRECTLY in generation
                self.tracker.update_step(self.tracker.Step.EMBEDDING, 0, "Creating vector embeddings...")
                documents_added = self._step5_create_embeddings(step4_output_path)  # ✅ This now returns count
                self.tracker.update_step(self.tracker.Step.EMBEDDING, 100, "Embeddings created")
                
                # STEP 6: Copy images DIRECTLY to generation
                self.tracker.update_step(self.tracker.Step.FINALIZING, 0, "Copying images...")
                images_copied = self._copy_images_to_generation()
                
                # 🚨 STEP 7: CLEANUP - NO CHROMADB APPENDING NEEDED
                self.tracker.update_step(self.tracker.Step.FINALIZING, 80, "Cleaning up temporary files...")
                cleanup_count = self._cleanup_bulk_folder()
                
                # STEP 8: Get statistics
                final_stats = self._step6_get_statistics()
                
                # ✅ FIXED: Remove chroma_appended reference
                final_stats.update({
                    "images_copied": images_copied,
                    "documents_added": documents_added,  # ✅ Use documents_added instead
                    "cleanup_deleted": cleanup_count,
                    "generation_folder": "../generation",
                    "status": "complete"
                })
                
                self.tracker.update_step(self.tracker.Step.FINALIZING, 100, "All files processed, merged, and cleaned!")
                
                return final_stats
                
            except Exception as e:
                print(f"❌ Corpus building failed: {e}")
                import traceback
                traceback.print_exc()
                raise
        
        def _step1_parse_pptx(self, input_folder: str) -> str:
            """Parse all PPTX files"""
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
            """Create embeddings directly in generation folder - APPEND if exists"""
            self.tracker.update_step(self.tracker.Step.EMBEDDING, 20, "Preparing for embedding...")
            
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                print("❌ OPENAI_API_KEY not found - SKIPPING EMBEDDINGS")
                return
            
            if not os.path.exists(step4_input_path):
                print(f"❌ Input file not found - SKIPPING EMBEDDINGS")
                return
            
            self.tracker.update_step(self.tracker.Step.EMBEDDING, 40, "Processing documents for embedding...")
            
            try:
                # Use step5 for processing but NOT for storage
                from step5_four_vector_store_with_image_caption_and_text import DocumentProcessor
                
                processor = DocumentProcessor(openai_api_key=openai_api_key)
                
                self.tracker.update_step(self.tracker.Step.EMBEDDING, 60, "Generating embeddings...")
                documents = processor.process_json_file(
                    json_file_path=step4_input_path,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                
                if not documents:
                    print("⚠️ No documents to embed")
                    return
                
                print(f"🔍 Processing {len(documents)} documents...")
                
                # Generate unique IDs for bulk upload
                import uuid
                for i, doc in enumerate(documents):
                    doc['id'] = f"bulk_{self.session_id}_{uuid.uuid4().hex[:8]}_{i}"
                
                self.tracker.update_step(self.tracker.Step.EMBEDDING, 80, "Storing embeddings...")
                
                # 🚨 Create/Connect to ChromaDB in generation folder
                generation_path = f"../generation/chroma_db/{self.user_id}/main_corpus"
                os.makedirs(generation_path, exist_ok=True)
                
                client = chromadb.PersistentClient(path=generation_path)
                
                try:
                    # Try to get existing collection
                    collection = client.get_collection("document_embeddings")
                    current_count = collection.count()
                    print(f"📁 Found existing generation collection with {current_count} documents")
                    
                    # 🚨 CHECK FOR DUPLICATES BEFORE ADDING
                    existing_ids = set()
                    try:
                        # Get existing IDs to avoid duplicates
                        existing_data = collection.get()
                        existing_ids = set(existing_data['ids'])
                        print(f"📊 Checking against {len(existing_ids)} existing document IDs")
                    except Exception as e:
                        print(f"⚠️ Could not get existing IDs: {e}")
                    
                    # Filter out documents that might already exist
                    filtered_documents = []
                    for doc in documents:
                        # Check if similar content already exists
                        if doc['id'] not in existing_ids:
                            filtered_documents.append(doc)
                        else:
                            print(f"   ⏭️ Skipping duplicate ID: {doc['id']}")
                    
                    if not filtered_documents:
                        print("⚠️ All documents already exist in generation collection")
                        return 0
                    
                    documents = filtered_documents
                    print(f"📊 Will add {len(documents)} new documents (filtered from {len(documents)})")
                    
                except:
                    # Collection doesn't exist, create it
                    collection = client.create_collection(
                        name="document_embeddings",
                        metadata={"description": f"Bulk upload corpus for user {self.user_id}"}
                    )
                    current_count = 0
                    print(f"📁 Created new generation collection")
                
                # Prepare data
                ids = [doc['id'] for doc in documents]
                embeddings = [doc['embedding'] for doc in documents if 'embedding' in doc]
                metadatas = [doc.get('metadata', {}) for doc in documents]
                texts = [doc.get('text', '') for doc in documents]
                
                # Validate embeddings
                valid_indices = []
                for i, emb in enumerate(embeddings):
                    if emb and isinstance(emb, list) and len(emb) > 0:
                        valid_indices.append(i)
                    else:
                        print(f"   ⚠️ Skipping document {i} with invalid embedding")
                
                if not valid_indices:
                    print("❌ No valid embeddings to store")
                    return 0
                
                # Filter for valid embeddings only
                valid_ids = [ids[i] for i in valid_indices]
                valid_embeddings = [embeddings[i] for i in valid_indices]
                valid_metadatas = [metadatas[i] for i in valid_indices]
                valid_texts = [texts[i] for i in valid_indices]
                
                # Store (APPEND to existing collection)
                collection.add(
                    ids=valid_ids,
                    embeddings=valid_embeddings,
                    metadatas=valid_metadatas,
                    documents=valid_texts
                )
                
                new_count = collection.count()
                added_count = new_count - current_count
                
                print(f"✅ Successfully added {added_count} new documents to generation folder")
                print(f"📊 Total in generation: {new_count} documents")
                
                return added_count
                
            except Exception as e:
                print(f"❌ Direct embedding failed: {e}")
                import traceback
                traceback.print_exc()
                return 0
        
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
        
        def _cleanup_bulk_folder(self):
            """Delete ALL temporary files from Bulk_Upload folder after successful merge"""
            print("🧹 Cleaning up ALL Bulk_Upload temporary files...")
            
            # These are the folders YOUR bulk processing creates
            paths_to_delete = [
                f"chroma_db/{self.user_id}/main_corpus",    # Your ChromaDB
                f"images/{self.user_id}/main_corpus",       # Your images
                f"processed_json/{self.user_id}",           # Your processed JSON
                f"unified_output/{self.user_id}",           # Your unified output
                f"user_uploads/{self.user_id}",             # Your uploads
            ]
            
            deleted_count = 0
            for path in paths_to_delete:
                if os.path.exists(path):
                    try:
                        # First close any ChromaDB connections if this is a ChromaDB path
                        if path.startswith("chroma_db"):
                            self._close_chromadb_connections(path)
                        else:
                            # Delete the folder
                            shutil.rmtree(path, ignore_errors=True)
                            print(f"   ✅ Deleted: {path}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ⚠️ Could not delete {path}: {e}")
            
            print(f"📊 Total directories cleaned: {deleted_count}")
            return deleted_count

        def _count_vector_documents(self) -> int:
            """Count documents in vector database"""
            try:
                chroma_manager = MultiUserChromaDBManager()
                vector_stats = chroma_manager.get_user_stats(self.user_id)
                return vector_stats.get('main_corpus_documents', 0)
            except:
                return 0
        
        def _cleanup_temp_data(self):
            """Cleanup temporary processing data - FIXED variable shadowing"""
            print(f"\n🧹 Cleaning up temporary data for user: {self.user_id}...")
            
            # Define directories to clean
            temp_dirs = [
                f"processed_json/{self.user_id}",
                f"unified_output/{self.user_id}",
                f"user_uploads/{self.user_id}",
                f"chroma_db/{self.user_id}/temp_uploads",
            ]
            
            # First, explicitly close any ChromaDB connections
            for temp_dir in temp_dirs:
                if temp_dir.startswith("chroma_db") and os.path.exists(temp_dir):
                    print(f"  🔄 Closing ChromaDB connections for: {temp_dir}")
                    self._close_chromadb_connections(temp_dir)
            
            # Now delete all directories with retries - FIXED: Don't shadow 'shutil'
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    print(f"  🗑️ Removing: {temp_dir}")
                    deleted = False
                    retries = 3
                    
                    for attempt in range(retries):
                        try:
                            if attempt > 0:
                                print(f"    Retry {attempt + 1}/{retries}...")
                                time.sleep(1)  # Wait before retry
                            
                            # Use the imported shutil module - NOT redefining it
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            
                            # Double-check deletion
                            if not os.path.exists(temp_dir):
                                print(f"    ✅ Successfully removed: {temp_dir}")
                                deleted = True
                                break
                            else:
                                print(f"    ⚠️ Directory still exists after removal attempt")
                                
                        except PermissionError as e:
                            print(f"    ⚠️ Permission error (attempt {attempt + 1}): {e}")
                            
                            # On Windows, try to use rmtree with ignore_errors
                            if attempt == retries - 1:
                                print(f"    💡 Using forced removal with ignore_errors")
                                shutil.rmtree(temp_dir, ignore_errors=True)
                                if not os.path.exists(temp_dir):
                                    deleted = True
                                else:
                                    print(f"    ❌ Still cannot remove: {temp_dir}")
                            
                        except Exception as e:
                            print(f"    ⚠️ Error removing {temp_dir}: {e}")
                            if attempt == retries - 1:
                                print(f"    ❌ Giving up on: {temp_dir}")
                    
                    if deleted:
                        print(f"  ✅ Successfully cleaned: {temp_dir}")
            
            # Force garbage collection to release any remaining file handles
            gc.collect()
            
            print(f"✅ Cleanup completed for user: {self.user_id}")

        def _cleanup_old_data_before_start(self):
            """Clean up any leftover files from previous runs - WITH CHROMADB CLOSURE"""
            print(f"🧹 Pre-cleaning for user: {self.user_id}")
            
            # Just clean the same directories we create
            paths_to_clean = [
                f"chroma_db/{self.user_id}/main_corpus",
                f"images/{self.user_id}/main_corpus",
                f"processed_json/{self.user_id}",
                f"unified_output/{self.user_id}",
                f"user_uploads/{self.user_id}",
            ]
            
            for path in paths_to_clean:
                if os.path.exists(path):
                    print(f"   Found leftover: {path}")
                    
                    # Close ChromaDB connections if it's a ChromaDB path
                    if path.startswith("chroma_db"):
                        self._close_chromadb_connections(path)
                    else:
                        try:
                            shutil.rmtree(path, ignore_errors=True)
                            print(f"   ✅ Cleaned: {path}")
                        except Exception as e:
                            print(f"   ⚠️ Could not clean {path}: {e}")

        def _copy_images_to_generation(self):
            """Copy images from Bulk_Upload to generation folder"""
            print(f"📸 Copying images to generation folder for user: {self.user_id}")
            
            # Source: Bulk_Upload/images/{user_id}/main_corpus/
            source_dir = f"images/{self.user_id}/main_corpus"
            
            # Destination: generation/images/{user_id}/main_corpus/
            dest_dir = f"../generation/images/{self.user_id}/main_corpus"
            
            if not os.path.exists(source_dir):
                print(f"⚠️ No images to copy from: {source_dir}")
                return 0
            
            # Create destination directory
            os.makedirs(dest_dir, exist_ok=True)
            
            copied_count = 0
            for filename in os.listdir(source_dir):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                    src_path = os.path.join(source_dir, filename)
                    dst_path = os.path.join(dest_dir, filename)
                    
                    # Skip if already exists (avoid duplicates)
                    if not os.path.exists(dst_path):
                        shutil.copy2(src_path, dst_path)
                        copied_count += 1
                        print(f"   ✅ Copied: {filename}")
                    else:
                        print(f"   ⏭️ Skipped (exists): {filename}")
            
            print(f"📊 Total images copied: {copied_count}")
            return copied_count

        def _append_chromadb_to_generation(self):
            """Process the step4 deduplicated JSON file directly for generation folder"""
            print(f"📚 Processing deduplicated JSON for generation folder for user: {self.user_id}")
            
            # Find the step4 deduplicated JSON file
            step4_pattern = f"processed_json/{self.user_id}/step4_deduplicated_{self.user_id}_{self.session_id}.json"
            
            if not os.path.exists(step4_pattern):
                print(f"⚠️ Step4 JSON not found: {step4_pattern}")
                
                # Try to find any step4 file for this session
                processed_json_dir = f"processed_json/{self.user_id}"
                if os.path.exists(processed_json_dir):
                    for filename in os.listdir(processed_json_dir):
                        if filename.startswith(f"step4_deduplicated_{self.user_id}_{self.session_id}"):
                            step4_pattern = os.path.join(processed_json_dir, filename)
                            print(f"🔍 Found alternative step4 file: {step4_pattern}")
                            break
                
                if not os.path.exists(step4_pattern):
                    print(f"❌ Could not find step4 JSON for session {self.session_id}")
                    return 0
            
            print(f"📄 Using deduplicated JSON: {step4_pattern}")
            
            try:
                # Load the step4 JSON data
                with open(step4_pattern, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"📊 JSON data type: {type(data)}")
                
                # Count documents in the step4 file
                if isinstance(data, dict):
                    # Check if it's the unified format
                    if 'documents' in data:
                        doc_count = len(data['documents'])
                        print(f"📊 Found {doc_count} documents in unified format")
                    elif 'chunks' in data:
                        doc_count = len(data['chunks'])
                        print(f"📊 Found {doc_count} chunks in chunks format")
                    else:
                        print(f"⚠️ Unexpected JSON structure: {list(data.keys())}")
                        return 0
                elif isinstance(data, list):
                    doc_count = len(data)
                    print(f"📊 Found {doc_count} items in list format")
                else:
                    print(f"❌ Unexpected data type: {type(data)}")
                    return 0
                
                # Get OpenAI API key
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    print("❌ OPENAI_API_KEY not found - SKIPPING EMBEDDINGS")
                    return 0
                
                # Process directly using DocumentProcessor (like your original working code)
                from step5_four_vector_store_with_image_caption_and_text import DocumentProcessor
                
                processor = DocumentProcessor(openai_api_key=openai_api_key)
                
                # Process the JSON file - this method knows how to handle step4 format
                documents = processor.process_json_file(
                    json_file_path=step4_pattern,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                
                if not documents:
                    print("⚠️ No documents generated from JSON")
                    return 0
                
                print(f"✅ Generated {len(documents)} embeddable documents")
                
                # Generate FRESH unique IDs for generation folder to avoid any conflicts
                import uuid
                for i, doc in enumerate(documents):
                    doc['id'] = f"gen_{self.session_id}_{uuid.uuid4().hex[:8]}_{i}"
                    print(f"   📝 Document {i}: {doc.get('metadata', {}).get('title', 'No title')[:50]}...")
                
                # Path to generation ChromaDB
                gen_chroma_path = f"../generation/chroma_db/{self.user_id}/main_corpus"
                os.makedirs(os.path.dirname(gen_chroma_path), exist_ok=True)
                
                print(f"💾 Storing in generation ChromaDB: {gen_chroma_path}")
                
                # Create/connect to generation ChromaDB
                gen_client = chromadb.PersistentClient(path=gen_chroma_path)
                
                try:
                    gen_collection = gen_client.get_collection("document_embeddings")
                    current_count = gen_collection.count()
                    print(f"📊 Generation ChromaDB already has {current_count} documents")
                except:
                    gen_collection = gen_client.create_collection(
                        name="document_embeddings",
                        metadata={"description": f"Main corpus for user {self.user_id}"}
                    )
                    current_count = 0
                    print(f"📊 Created new collection in generation ChromaDB")
                
                # Prepare documents for ChromaDB
                ids = []
                embeddings = []
                metadatas = []
                texts = []
                
                for doc in documents:
                    if 'embedding' in doc and doc['embedding']:
                        ids.append(doc['id'])
                        embeddings.append(doc['embedding'])
                        metadatas.append(doc.get('metadata', {}))
                        texts.append(doc.get('text', ''))
                    else:
                        print(f"⚠️ Skipping document without embedding: {doc['id']}")
                
                if not ids:
                    print("❌ No valid documents with embeddings")
                    return 0
                
                print(f"📤 Adding {len(ids)} documents to generation ChromaDB...")
                
                # Add to generation ChromaDB
                gen_collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=texts
                )
                
                new_total = gen_collection.count()
                added_count = new_total - current_count
                
                print(f"✅ Successfully added {added_count} fresh documents to generation ChromaDB")
                print(f"📊 Total documents in generation: {new_total}")
                
                # Clean up
                del gen_collection
                del gen_client
                gc.collect()
                
                return added_count
                
            except Exception as e:
                print(f"❌ Error processing step4 JSON for generation: {e}")
                import traceback
                traceback.print_exc()
                return 0
    
    # Create builder and process files
    builder = BulkCorpusBuilderWithProgress(user_id, tracker)
    result = builder.build_corpus(input_folder)
    
    return result


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
        file_content = await zip_file.read()
        
        with open(zip_file_path, "wb") as buffer:
            buffer.write(file_content)
        
        print(f"✅ File saved: {zip_file_path} ({len(file_content)} bytes)")
        
        # Initialize progress tracker
        tracker = BulkUploadProgressTracker(user_id, task_id)
        
        # Store tracker
        with bulk_upload_lock:
            bulk_upload_progress[task_id] = tracker
        
        # Start processing in background thread
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


@app.get("/bulk_upload_progress/{task_id}")
async def get_bulk_upload_progress(task_id: str):
    """
    Get progress of bulk upload processing
    UI can poll this endpoint every 2-5 seconds
    """
    try:
        with bulk_upload_lock:
            print(f"📊 Checking progress for task: {task_id}")
            print(f"📊 Available tasks: {list(bulk_upload_progress.keys())}")
            
            if task_id not in bulk_upload_progress:
                raise HTTPException(status_code=404, detail="Task not found or has expired")
            
            tracker = bulk_upload_progress[task_id]
            progress_data = tracker.get_progress()
        
        print(f"📊 Progress request for task {task_id}: {progress_data['overall_progress']}% - {progress_data['message']}")
        
        return progress_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting progress for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting progress: {str(e)}")


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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Bulk Upload Service"}


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("temp_uploads", exist_ok=True)
    os.makedirs("images", exist_ok=True)
    os.makedirs("chroma_db", exist_ok=True)
    os.makedirs("processed_json", exist_ok=True)
    os.makedirs("unified_output", exist_ok=True)
    os.makedirs("user_uploads", exist_ok=True)
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_stale_tasks, daemon=True)
    cleanup_thread.start()
    print("✅ Started stale task cleanup thread")
    
    print("🚀 Starting Bulk Upload Service...")
    print("📚 Available endpoints:")
    print("   POST /bulk_upload - Upload and process zip files")
    print("   GET  /bulk_upload_progress/{task_id} - Get progress")
    print("   GET  /bulk_upload_tasks/{user_id} - List user tasks")
    print("   DELETE /bulk_upload_task/{task_id} - Cancel task")
    print("   GET  /health - Health check")
    print("\n🔧 Service is isolated and runs independently")
    print("🔒 CHROMADB CONNECTION CLOSURE ENABLED - Will properly close file handles")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Different port than main app