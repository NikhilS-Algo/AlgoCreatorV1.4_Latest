import os
import shutil
import glob
from step5_four_vector_store_with_image_caption_and_text import MultiUserChromaDBManager
import os
import stat  # 🆕 ADD THIS IMPORT

class StorageManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.chroma_manager = MultiUserChromaDBManager()
        
        # Create directory structure with session support
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directory structure with session support"""
        directories = [
            f"images/{self.user_id}/main_corpus",
            f"images/{self.user_id}/temp_uploads", 
            f"processed_json/{self.user_id}",
            f"user_uploads/{self.user_id}",
            f"unified_output/{self.user_id}"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        print(f"✅ Created storage directories for user: {self.user_id}")

    def fix_chromadb_permissions(self):
        """Fix ChromaDB directory permissions to prevent readonly errors"""
        directories = [
            f"./chroma_db/{self.user_id}",
            f"./chroma_db/{self.user_id}/main_corpus", 
            f"./chroma_db/{self.user_id}/temp_uploads"
        ]
        
        for directory in directories:
            if os.path.exists(directory):
                try:
                    # Make directory writable (755 permissions)
                    os.chmod(directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
                    print(f"✅ Fixed permissions for: {directory}")
                except Exception as e:
                    print(f"⚠️ Could not fix permissions for {directory}: {e}")
            else:
                print(f"📁 Directory doesn't exist yet: {directory}")
    
    def get_session_image_dir(self, session_id: str) -> str:
        """Get session-specific image directory"""
        session_image_dir = f"images/{self.user_id}/temp_uploads/{session_id}"
        os.makedirs(session_image_dir, exist_ok=True)
        return session_image_dir
    
    def cleanup_temp_data(self, session_id: str = None):
        """Cleanup ALL temporary data including session-specific images - ENHANCED"""
        print("🧹 COMPREHENSIVE temp data cleanup...")
        
        # 1. Clear temp VectorDB
        self.chroma_manager.clear_temp_uploads(self.user_id)
        print("✅ Cleared temp VectorDB")
        
        # 2. Clear session-specific temp images
        if session_id:
            session_image_dir = f"images/{self.user_id}/temp_uploads/{session_id}"
            if os.path.exists(session_image_dir):
                try:
                    shutil.rmtree(session_image_dir)
                    print(f"✅ Cleared session images: {session_image_dir}")
                except Exception as e:
                    print(f"⚠️ Could not clear session images: {e}")
        
        # 3. Clear general temp images (fallback - any remaining temp files)
        temp_image_dir = f"images/{self.user_id}/temp_uploads"
        if os.path.exists(temp_image_dir):
            # Remove only session directories, keep the main temp_uploads dir
            for item in os.listdir(temp_image_dir):
                item_path = os.path.join(temp_image_dir, item)
                if os.path.isdir(item_path):
                    try:
                        shutil.rmtree(item_path)
                        print(f"✅ Cleared temp image dir: {item}")
                    except Exception as e:
                        print(f"⚠️ Could not clear {item_path}: {e}")
        
        # 4. Clear session-specific JSON files
        if session_id:
            json_files = glob.glob(f"processed_json/{self.user_id}/*{session_id}*.json")
            for json_file in json_files:
                try:
                    os.remove(json_file)
                    print(f"✅ Removed: {json_file}")
                except Exception as e:
                    print(f"⚠️ Could not remove {json_file}: {e}")
        
        # 5. Clear unified output for this session
        if session_id:
            unified_files = glob.glob(f"unified_output/{self.user_id}/*{session_id}*.json")
            for unified_file in unified_files:
                try:
                    os.remove(unified_file)
                    print(f"✅ Removed: {unified_file}")
                except Exception as e:
                    print(f"⚠️ Could not remove {unified_file}: {e}")
        
        # 6. Clear user uploads for this session
        if session_id:
            upload_dir = f"user_uploads/{self.user_id}/{session_id}"
            if os.path.exists(upload_dir):
                try:
                    shutil.rmtree(upload_dir)
                    print(f"✅ Cleared upload directory: {upload_dir}")
                except Exception as e:
                    print(f"⚠️ Could not clear upload directory: {e}")
        
        print("🎯 Comprehensive temp cleanup completed")

    def merge_temp_to_main(self, session_id: str) -> int:
        """
        ROBUST merge sequence with PROPER COUNTING
        """
        print("🔄 Starting ROBUST merge process...")
        
        merged_count = 0
        
        # STEP 1: First update VectorDB paths from temp to main
        print("📝 STEP 1: Updating VectorDB paths from temp→main...")
        updated_paths_count = self.chroma_manager.update_temp_paths_to_main(
            self.user_id, 
            session_id,
            "document_embeddings"
        )
        print(f"✅ Updated {updated_paths_count} VectorDB paths")
        
        # STEP 2: Move physical image files from temp_uploads to main_corpus
        print("📸 STEP 2: Moving physical image files from temp to main...")
        session_temp_dir = f"images/{self.user_id}/temp_uploads/{session_id}"
        main_corpus_dir = f"images/{self.user_id}/main_corpus"
        
        moved_images_count = 0
        if os.path.exists(session_temp_dir):
            image_files = [f for f in os.listdir(session_temp_dir) 
                        if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
            
            for image_file in image_files:
                src_path = os.path.join(session_temp_dir, image_file)
                dst_path = os.path.join(main_corpus_dir, image_file)
                
                # Only move if not already in main corpus (avoid duplicates)
                if not os.path.exists(dst_path):
                    try:
                        shutil.move(src_path, dst_path)
                        moved_images_count += 1
                        print(f"   📸 Moved: {image_file}")
                    except Exception as e:
                        print(f"⚠️ Could not move image {image_file}: {e}")
                else:
                    print(f"📝 Image already in main corpus: {image_file}")
                    # Remove from temp since it's already in main
                    os.remove(src_path)
            
            # Remove the now-empty session directory
            try:
                os.rmdir(session_temp_dir)
                print(f"🧹 Removed empty session directory: {session_temp_dir}")
            except:
                print(f"⚠️ Could not remove session directory: {session_temp_dir}")
        
        merged_count += moved_images_count
        print(f"✅ Moved {moved_images_count} images to main corpus")
        
        # STEP 3: Merge VectorDB collections WITH PROPER COUNTING
        print("🔄 STEP 3: Merging VectorDB collections...")
        vector_count = self.chroma_manager.merge_temp_to_main(
            self.user_id,
            "document_embeddings"
        )
        
        # STEP 4: Finally cleanup other temp data
        print("🧹 STEP 4: Cleaning up remaining temp data...")
        self._cleanup_temp_data_except_images(session_id)
        
        print(f"🎯 Total items merged: {merged_count + vector_count}")
        print(f"💡 ROBUST sequence: Paths updated → Files moved → Vectors merged → Temp cleaned")
        
        return merged_count + vector_count

    def _cleanup_temp_data_except_images(self, session_id: str):
        """Cleanup temp data except images (since they were already moved)"""
        print("🧹 Cleaning up temp data (except images)...")
        
        # 1. Clear temp VectorDB (already done in merge_temp_to_main)
        print("✅ Temp VectorDB already cleared")
        
        # 2. Clear session-specific JSON files
        json_files = glob.glob(f"processed_json/{self.user_id}/*{session_id}*.json")
        for json_file in json_files:
            try:
                os.remove(json_file)
                print(f"✅ Removed: {json_file}")
            except Exception as e:
                print(f"⚠️ Could not remove {json_file}: {e}")
        
        # 3. Clear unified output for this session
        unified_files = glob.glob(f"unified_output/{self.user_id}/*{session_id}*.json")
        for unified_file in unified_files:
            try:
                os.remove(unified_file)
                print(f"✅ Removed: {unified_file}")
            except Exception as e:
                print(f"⚠️ Could not remove {unified_file}: {e}")
        
        # 4. Clear user uploads for this session
        upload_dir = f"user_uploads/{self.user_id}/{session_id}"
        if os.path.exists(upload_dir):
            try:
                shutil.rmtree(upload_dir)
                print(f"✅ Cleared upload directory: {upload_dir}")
            except Exception as e:
                print(f"⚠️ Could not clear upload directory: {e}")
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics for user"""
        stats = {
            'user_id': self.user_id,
            'main_corpus_images': 0,
            'temp_uploads_images': 0,
            'json_files': 0,
            'session_dirs': []
        }
        
        # Count main corpus images
        main_img_dir = f"images/{self.user_id}/main_corpus"
        if os.path.exists(main_img_dir):
            stats['main_corpus_images'] = len([
                f for f in os.listdir(main_img_dir) 
                if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))
            ])
        
        # Count temp uploads images (across all sessions)
        temp_img_dir = f"images/{self.user_id}/temp_uploads"
        if os.path.exists(temp_img_dir):
            temp_images_count = 0
            # Count images in all session directories
            for item in os.listdir(temp_img_dir):
                item_path = os.path.join(temp_img_dir, item)
                if os.path.isdir(item_path):
                    stats['session_dirs'].append(item)
                    session_images = [
                        f for f in os.listdir(item_path) 
                        if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))
                    ]
                    temp_images_count += len(session_images)
            stats['temp_uploads_images'] = temp_images_count
        
        # Count JSON files
        json_dir = f"processed_json/{self.user_id}"
        if os.path.exists(json_dir):
            stats['json_files'] = len([f for f in os.listdir(json_dir) if f.endswith('.json')])
        
        return stats
    
    def ensure_image_directories(self):
        """Ensure all required image directories exist"""
        directories = [
            f"images/{self.user_id}/main_corpus",
            f"images/{self.user_id}/temp_uploads"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        print(f"✅ Ensured image directories for user: {self.user_id}")
    
    def ensure_corpus_has_data(self):
        """Ensure main_corpus has data - call this before corpus_only operations"""
        print("🔍 Ensuring corpus has data...")
        stats = self.chroma_manager.get_user_stats(self.user_id)
        
        if stats['main_corpus_documents'] == 0 and stats['temp_uploads_documents'] > 0:
            print("⚠️ Main corpus empty but temp has data - forcing sync...")
            self.chroma_manager.force_sync_corpus(self.user_id)
            print("✅ Corpus data ensured")
        else:
            print(f"✅ Corpus status: {stats['main_corpus_documents']} docs in main, {stats['temp_uploads_documents']} in temp")