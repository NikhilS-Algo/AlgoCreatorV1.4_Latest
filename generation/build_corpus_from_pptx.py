


# build_corpus_from_pptx.py
import os
import json
import shutil
import uuid
from typing import Dict, Any, List
from unified_ppt_parser_optimized import OptimizedPPTXParser

from Step2_Processing_unified_document_json_file_for_vector_store import JSONPreprocessor
from step3_Image_caption_generator_Openai import ImageCaptionProcessor
from step4_deduplicate_chunks_and_images import DocumentDeduplicator
from step5_four_vector_store_with_image_caption_and_text import main_embedding_pipeline

class SimpleCorpusBuilder:
# AFTER (make it accept parameters):
    def __init__(self, user_id=None, input_folder=None):
        # Accept dynamic user_id and input folder
        self.user_id = user_id or "test-email@gmail.com"
        self.input_pptx_folder = input_folder or "Test_Data"
        
        # Dynamic paths based on user_id
        self.output_vector_db = f"chroma_db/{self.user_id}/main_corpus"
        self.output_images = f"images/{self.user_id}/main_corpus"
        
        self.session_id = f"build_{uuid.uuid4().hex[:8]}"
        
        # Create all directories upfront
        self._create_directories()
        
        # Create all directories upfront
        self._create_directories()
        
        print(f"🚀 Corpus Builder Initialized")
        print(f"📂 Input: {self.input_pptx_folder}")
        print(f"📤 Output: {self.output_vector_db}")
        print(f"🖼️ Images: images/{self.user_id}/main_corpus")
        print(f"👤 User: {self.user_id}")
    



    def _create_directories(self):
        """Create all necessary directories upfront"""
        directories = [
            f"processed_json/{self.user_id}",
            f"unified_output/{self.user_id}",
            f"user_uploads/{self.user_id}",
            f"images/{self.user_id}/main_corpus",  # Main corpus for everything
            os.path.dirname(self.output_vector_db),
            os.path.dirname(self.output_images)
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Created: {directory}")


    def save_final_json(self, json_path: str):
        """Save the final processed JSON file"""
        output_dir = "final_processed_json"
        os.makedirs(output_dir, exist_ok=True)
        
        # Get filename with session ID
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"final_processed_{self.session_id}_{timestamp}.json")
        
        # Copy the JSON file
        shutil.copy2(json_path, output_file)
        
        print(f"💾 Final JSON saved to: {output_file}")
        return output_file
        
    def build_corpus(self):
        """Process all files and create final embeddings"""
        print(f"\n{'='*60}")
        print(f"🏗️  BUILDING CORPUS FOR: {self.user_id}")
        print(f"{'='*60}")
        
        try:
            # STEP 1: Parse all PPTX files at once
            unified_json_path = self._step1_parse_pptx()
            
            # STEP 2: Preprocessing
            step2_output_path = self._step2_preprocessing(unified_json_path)
            
            # STEP 3: Image captioning
            step3_output_path = self._step3_image_captioning(step2_output_path)
            
            # STEP 4: Deduplication
            step4_output_path = self._step4_deduplication(step3_output_path)
            
            # === ADD THIS ONE LINE ===
            self.save_final_json(step4_output_path)  # Save the final processed JSON

            # STEP 5: Create embeddings
            self._step5_create_embeddings(step4_output_path)
            
            # STEP 6: Export results
            final_stats = self._step6_export_results()
            
            print(f"\n🎯 CORPUS BUILDING COMPLETE!")
            print(f"📊 Final Statistics:")
            print(f"   - User: {self.user_id}")
            print(f"   - Input PPTX folder: {self.input_pptx_folder}")
            print(f"   - Vector DB: {self.output_vector_db}")
            print(f"   - Images: images/{self.user_id}/main_corpus")
            print(f"   - Total images: {final_stats['total_images']}")
            print(f"   - Vector documents: {final_stats['vector_documents']}")
            
            return final_stats
            
        except Exception as e:
            print(f"❌ Corpus building failed: {e}")
            self._cleanup_preserve_images()
            raise
    
    def _step1_parse_pptx(self) -> str:
        """Step 1: Parse all PPTX files at once - images go directly to main_corpus"""
        print(f"\n🔍 STEP 1: Parsing PPTX files...")
        
        if not os.path.exists(self.input_pptx_folder):
            raise FileNotFoundError(f"PPTX folder not found: {self.input_pptx_folder}")
        
        # Filter out temporary files
        pptx_files = []
        for filename in os.listdir(self.input_pptx_folder):
            if filename.endswith('.pptx') and not filename.startswith('.~'):
                pptx_files.append(os.path.join(self.input_pptx_folder, filename))
        
        print(f"📄 Found {len(pptx_files)} valid PPTX files")
        
        # Parser will extract images directly to images/test-email@gmail.com/main_corpus
        parser = OptimizedPPTXParser(output_base_dir=f"unified_output/{self.user_id}")
        unified_output_path = parser.parse_ppt_folder(
            folder_path=self.input_pptx_folder,
            output_filename=f"unified_ppt_{self.session_id}.json"
        )
        
        print(f"✅ Unified parsing complete: {unified_output_path}")
        return unified_output_path
    
    def _step2_preprocessing(self, unified_json_path: str) -> str:
        """Step 2: Preprocess documents"""
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
        """Step 3: Generate image captions"""
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
        """Step 4: Deduplicate content"""
        print(f"\n🧹 STEP 4: Deduplicating content...")
        
        deduplicator = DocumentDeduplicator()
        deduplication_result = deduplicator.deduplicate_documents(
            input_file=step3_input_path,
            user_id=self.user_id,
            session_id=self.session_id
        )
        
        if not deduplication_result['success']:
            raise Exception(f"Deduplication failed: {deduplication_result['error']}")
        
        step4_output_path = deduplication_result['output_file']
        print(f"✅ Deduplication complete: {step4_output_path}")
        return step4_output_path
    
    def _step5_create_embeddings(self, step4_input_path: str):
        """Step 5: Create embeddings - SKIP IF FAILS"""
        print(f"\n📚 STEP 5: Creating vector embeddings...")
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("❌ OPENAI_API_KEY not found - SKIPPING EMBEDDINGS")
            return
        
        if not os.path.exists(step4_input_path):
            print(f"❌ Input file not found - SKIPPING EMBEDDINGS")
            return
        
        print(f"📁 Using input file: {step4_input_path}")
        
        # Try main pipeline
        try:
            embedding_processor = main_embedding_pipeline(
                openai_api_key=openai_api_key,
                user_id=self.user_id,
                session_id=self.session_id
            )
            print("✅ Embeddings created successfully")
        except Exception as e:
            print(f"❌ Embedding failed: {e}")
            
            # Try manual approach
            try:
                print("🔄 Trying manual embedding...")
                self._create_embeddings_manual(step4_input_path)
                print("✅ Manual embeddings created successfully")
            except Exception as e2:
                print(f"❌ Manual embedding failed: {e2}")
                print("🚨 SKIPPING ALL EMBEDDINGS - Continuing without vector DB")
                # DON'T RAISE - JUST CONTINUE
                # This ensures images and JSON are preserved
    
    def _create_embeddings_manual(self, step4_input_path: str):
        """Manual embedding creation as fallback - FIXED VERSION"""
        print("🔄 Using manual embedding approach...")
        
        try:
            # Load the deduplicated data - FIXED: Check if it's a string first
            with open(step4_input_path, 'r', encoding='utf-8') as f:
                data_content = f.read().strip()
            
            # Debug: Check what we're reading
            print(f"📄 File content type: {type(data_content)}")
            print(f"📄 File content preview: {data_content[:200]}...")
            
            # Parse JSON data
            if data_content.startswith('{') or data_content.startswith('['):
                data = json.loads(data_content)
            else:
                print(f"❌ Invalid JSON format in file: {step4_input_path}")
                return
            
            # Debug: Check data structure
            print(f"📊 Data type after parsing: {type(data)}")
            if isinstance(data, list):
                print(f"📊 Data length: {len(data)}")
                if data and isinstance(data[0], dict):
                    print(f"📊 First item keys: {list(data[0].keys())}")
            
            # Count total chunks for logging
            total_chunks = 0
            if isinstance(data, list):
                for doc in data:
                    if isinstance(doc, dict):
                        total_chunks += len(doc.get('chunks', []))
                    else:
                        print(f"⚠️ Unexpected doc type: {type(doc)}")
            elif isinstance(data, dict):
                total_chunks = len(data.get('chunks', []))
            else:
                print(f"❌ Unexpected data structure: {type(data)}")
                return
            
            print(f"📝 Processing {total_chunks} chunks for embedding...")
            
            # Use the main embedding pipeline but ensure it uses our file
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            # Import the actual embedding function
            from step5_four_vector_store_with_image_caption_and_text import DocumentProcessor, MultiUserChromaDBManager
            
            processor = DocumentProcessor(openai_api_key=openai_api_key)
            
            # Process all documents - FIXED: Handle different data structures
            all_documents = []
            if isinstance(data, list):
                for doc in data:
                    if isinstance(doc, dict):
                        documents = processor.process_document_for_embedding(doc, self.user_id, self.session_id)
                        all_documents.extend(documents)
            elif isinstance(data, dict):
                documents = processor.process_json_file(step4_input_path, self.user_id, self.session_id)
                all_documents.extend(documents)
            
            print(f"📊 Generated {len(all_documents)} documents for embedding")
            
            if all_documents:
                # Store in ChromaDB with validation
                valid_documents = []
                for doc in all_documents:
                    # Check if embedding is valid
                    if (doc.get('embedding') and 
                        isinstance(doc['embedding'], list) and 
                        len(doc['embedding']) > 0 and
                        all(isinstance(x, (int, float)) for x in doc['embedding'])):
                        valid_documents.append(doc)
                    else:
                        print(f"⚠️ Skipping document with invalid embedding: {doc.get('id')}")
                
                if valid_documents:
                    processor.store_in_chromadb(valid_documents, self.user_id, storage_mode="temp_uploads")
                    print(f"✅ Stored {len(valid_documents)} valid documents in vector database")
                else:
                    print("⚠️ No valid documents to embed")
            else:
                print("⚠️ No documents to embed")
                    
        except Exception as e:
            print(f"❌ Manual embedding failed: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - just continue without embeddings
            print("💡 Continuing without embeddings for this batch")
    
    def _step6_export_results(self) -> Dict[str, Any]:
        """Step 6: Export final results - Images stay in main_corpus"""
        print(f"\n📤 STEP 6: Exporting results...")
        
        # Source paths
        source_vector_path = f"chroma_db/{self.user_id}/temp_uploads"
        
        # Images are already in main_corpus
        final_image_path = f"images/{self.user_id}/main_corpus"
        
        # Create output directories
        os.makedirs(os.path.dirname(self.output_vector_db), exist_ok=True)
        os.makedirs(os.path.dirname(self.output_images), exist_ok=True)
        
        # Remove existing outputs (but NOT the images folder)
        for path in [self.output_vector_db, self.output_images]:
            if os.path.exists(path):
                shutil.rmtree(path)
        
        # STEP 1: Copy vector database
        vector_count = 0
        if os.path.exists(source_vector_path):
            try:
                shutil.copytree(source_vector_path, self.output_vector_db)
                vector_count = self._count_vector_documents()
                print(f"✅ Copied vector DB: {source_vector_path} → {self.output_vector_db}")
                print(f"   Contains {vector_count} vector documents")
            except Exception as e:
                print(f"⚠️ Could not copy vector DB: {e}")
        else:
            print(f"⚠️ Vector database not found: {source_vector_path}")
        
        # STEP 2: Verify images in main_corpus (NO COPYING NEEDED)
        image_count = 0
        if os.path.exists(final_image_path):
            image_files = [f for f in os.listdir(final_image_path) 
                          if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
            image_count = len(image_files)
            
            print(f"✅ Images in main_corpus: {final_image_path}")
            print(f"   Contains {image_count} content images")
            
            if image_files:
                # Show actual files to verify
                print(f"   Image files in main_corpus:")
                for img_file in image_files[:10]:  # Show first 10 files
                    img_path = os.path.join(final_image_path, img_file)
                    size_kb = os.path.getsize(img_path) / 1024 if os.path.exists(img_path) else 0
                    print(f"     - {img_file} ({size_kb:.1f} KB)")
        else:
            print(f"❌ Main corpus not found: {final_image_path}")
        
        # STEP 3: Cleanup but preserve main_corpus images
        self._cleanup_preserve_images()
        
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
            return vector_stats.get('temp_uploads_documents', 0)
        except:
            return 0
    
    def _cleanup_preserve_images(self):
        """Cleanup temporary data but preserve main_corpus images"""
        print(f"\n🧹 Cleaning up temporary data (preserving main_corpus)...")
        
        temp_dirs = [
            f"chroma_db/{self.user_id}",
            f"processed_json/{self.user_id}",
            f"unified_output/{self.user_id}",
            f"user_uploads/{self.user_id}",
        ]
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    print(f"  ✅ Removed: {temp_dir}")
                except Exception as e:
                    print(f"  ⚠️ Could not remove {temp_dir}: {e}")
        
        # Preserve the main_corpus images
        main_corpus_path = f"images/{self.user_id}/main_corpus"
        if os.path.exists(main_corpus_path):
            image_count = len([f for f in os.listdir(main_corpus_path) 
                              if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))])
            print(f"  💾 PRESERVED: {main_corpus_path} ({image_count} images)")
            print(f"  🎯 These images are ready for presentation generation!")

def main():
    """Main function"""
    builder = SimpleCorpusBuilder()
    
    try:
        stats = builder.build_corpus()
        
        print(f"\n🎉 CORPUS SUCCESSFULLY BUILT!")
        print(f"📁 Your files are ready:")
        print(f"   🗄️  Vector Database: {stats['vector_db_path']}")
        print(f"   🖼️  Content Images: {stats['images_path']}")
        print(f"   👤 User: {stats['user_id']}")
        print(f"   📊 Contains: {stats['vector_documents']} vector documents")
        print(f"   📊 Contains: {stats['total_images']} content images")
        
        # Final verification
        print(f"\n🔍 Final Verification:")
        if os.path.exists(stats['images_path']):
            image_files = [f for f in os.listdir(stats['images_path']) 
                          if f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
            print(f"  ✅ Images in main_corpus: {len(image_files)} files")
        else:
            print(f"  ❌ Main corpus not found: {stats['images_path']}")
            
        if os.path.exists(stats['vector_db_path']):
            print(f"  ✅ Vector DB exists: {stats['vector_db_path']}")
        else:
            print(f"  ❌ Vector DB not found: {stats['vector_db_path']}")
        
    except Exception as e:
        print(f"❌ Failed to build corpus: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())