#step5_four_vector_store_with_image_caption_and_text.py

import json
import chromadb
from chromadb.config import Settings
import numpy as np
from typing import List, Dict, Any, Tuple
import os
from openai import OpenAI
import time
import shutil
import glob



from dotenv import load_dotenv
load_dotenv()

import json
import chromadb
from chromadb.config import Settings
import numpy as np
from typing import List, Dict, Any, Tuple
import os
from openai import OpenAI
import time
import shutil
import glob
from dotenv import load_dotenv
import hashlib  # 🆕 ADD THIS LINE
import uuid  # 🆕 ADD THIS TOO for the unique IDs


load_dotenv()

class MultiUserChromaDBManager:
    def __init__(self, base_persist_directory="./chroma_db"):
        self.base_persist_directory = base_persist_directory
        os.makedirs(base_persist_directory, exist_ok=True)
        print(f"Multi-user ChromaDB initialized at: {base_persist_directory}")

    def get_collection_name(self, user_id: str, collection_type: str = "main") -> str:
        """Generate unique collection names per user"""
        # Remove special characters from user_id for valid collection names
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ['-', '_']).lower()
        return f"doc_embeddings_{safe_user_id}_{collection_type}"
    
    def get_user_directories(self, user_id: str) -> Dict[str, str]:
        """Get directory paths for a specific user"""
        user_base_dir = os.path.join(self.base_persist_directory, user_id)
        directories = {
            'main_corpus': os.path.join(user_base_dir, "main_corpus"),
            'temp_uploads': os.path.join(user_base_dir, "temp_uploads"),
            'user_base': user_base_dir
        }
        
        # Create directories if they don't exist
        for dir_path in directories.values():
            os.makedirs(dir_path, exist_ok=True)
        
        return directories
    
    def user_exists(self, user_id: str) -> bool:
        """Check if a user has existing data"""
        directories = self.get_user_directories(user_id)
        return (os.path.exists(directories['main_corpus']) and 
                len(os.listdir(directories['main_corpus'])) > 0)
    
    def get_collection_for_mode(self, user_id: str, mode: str, collection_name: str = None):
        """Get collection based on mode with PROPER user-specific naming"""
        
        # ✅ CONSISTENT NAMING STRATEGY
        if collection_name is None:
            if mode == "uploaded_only":
                collection_name = f"doc_embeddings_{user_id}_temp"
            elif mode == "uploaded_plus_corpus":
                collection_name = f"doc_embeddings_{user_id}_merged"
            elif mode == "corpus_only":
                collection_name = f"doc_embeddings_{user_id}_main"
        
        print(f"🔍 Mode: {mode} - Using collection: {collection_name}")
        
        directories = self.get_user_directories(user_id)
        
        if mode == "uploaded_only":
            # Use only temp_uploads
            client = chromadb.PersistentClient(path=directories['temp_uploads'])
            print(f"   📁 Using temp_uploads directory")
            
        elif mode == "uploaded_plus_corpus":
            # Create a temporary merged collection
            merged_path = os.path.join(directories['user_base'], "temp_merged")
            if os.path.exists(merged_path):
                shutil.rmtree(merged_path)
            
            client = chromadb.PersistentClient(path=merged_path)
            print(f"   📁 Creating merged collection")
            
            # Merge collections - PASS USER_ID EXPLICITLY
            self._merge_collections(client, directories, collection_name, user_id)
            
        elif mode == "corpus_only":
            # Use only main_corpus
            client = chromadb.PersistentClient(path=directories['main_corpus'])
            print(f"   📁 Using main_corpus directory")
            
        else:
            raise ValueError(f"Invalid mode: {mode}")
        
        try:
            collection = client.get_collection(collection_name)
            print(f"✅ Loaded collection '{collection_name}' with {collection.count()} documents")
        except Exception as e:
            print(f"❌ Error loading collection: {e}")
            print(f"🆕 Creating new collection: {collection_name}")
            collection = client.create_collection(
                name=collection_name,
                metadata={"description": f"Document embeddings for user {user_id} - mode: {mode}"}
            )
        
        return collection, client
    

    def _merge_collections(self, target_client, directories: Dict, collection_name: str, user_id: str):
        """Merge main_corpus and temp_uploads into target collection - FIXED"""
        print(f"🔄 Starting collection merge for user: {user_id}")
        
        # ✅ TRY BOTH NAMING STRATEGIES (old and new)
        possible_main_names = [
            f"doc_embeddings_{user_id}_main",  # New naming
            "document_embeddings"              # Old naming (backward compatibility)
        ]
        
        possible_temp_names = [
            f"doc_embeddings_{user_id}_temp",  # New naming  
            "document_embeddings"              # Old naming (backward compatibility)
        ]
        
        main_data = None
        temp_data = None
        
        print("🔍 Looking for main corpus collections...")
        # Try to load main_corpus collection with different names
        for main_name in possible_main_names:
            try:
                main_client = chromadb.PersistentClient(path=directories['main_corpus'])
                main_collection = main_client.get_collection(main_name)
                main_data = main_collection.get(include=['embeddings', 'metadatas', 'documents'])
                print(f"✅ Found main corpus: '{main_name}' with {len(main_data['ids'])} documents")
                break
            except Exception as e:
                print(f"   ❌ Not found: {main_name} - {e}")
                continue
        
        print("🔍 Looking for temp uploads collections...")
        # Try to load temp_uploads collection with different names  
        for temp_name in possible_temp_names:
            try:
                temp_client = chromadb.PersistentClient(path=directories['temp_uploads'])
                temp_collection = temp_client.get_collection(temp_name)
                temp_data = temp_collection.get(include=['embeddings', 'metadatas', 'documents'])
                print(f"✅ Found temp uploads: '{temp_name}' with {len(temp_data['ids'])} documents")
                break
            except Exception as e:
                print(f"   ❌ Not found: {temp_name} - {e}")
                continue
        
        # Create target collection
        target_collection = target_client.create_collection(
            name=collection_name,
            metadata={"description": f"Merged collection for user {user_id}"}
        )
        
        total_added = 0
        
        # Add main_corpus data
        if main_data and main_data['ids']:
            target_collection.add(
                ids=main_data['ids'],
                embeddings=main_data['embeddings'],
                metadatas=main_data['metadatas'],
                documents=main_data['documents']
            )
            print(f"  ✅ Added {len(main_data['ids'])} documents from main_corpus")
            total_added += len(main_data['ids'])
        
        # Add temp_uploads data
        if temp_data and temp_data['ids']:
            target_collection.add(
                ids=temp_data['ids'],
                embeddings=temp_data['embeddings'],
                metadatas=temp_data['metadatas'],
                documents=temp_data['documents']
            )
            print(f"  ✅ Added {len(temp_data['ids'])} documents from temp_uploads")
            total_added += len(temp_data['ids'])
        
        print(f"🎯 Merged collection total: {target_collection.count()} documents")
        
        if total_added == 0:
            print("⚠️ WARNING: No documents were merged! Check collection names above.")
    
    def get_user_collection(self, user_id: str, collection_name: str = None):
        """Get user's main corpus collection"""
        if collection_name is None:
            collection_name = self.get_collection_name(user_id, "main")  # ✅ ADD THIS
        
        directories = self.get_user_directories(user_id)
        client = chromadb.PersistentClient(path=directories['main_corpus'])
        try:
            return client.get_collection(collection_name)
        except:
            return client.create_collection(
                name=collection_name,  # ✅ USE VARIABLE
                metadata={"description": f"Main corpus for user {user_id}"}
            )
    
    def get_user_temp_collection(self, user_id: str, collection_name: str = None):
        """Get user's temp uploads collection"""
        if collection_name is None:
            collection_name = self.get_collection_name(user_id, "temp")  # ✅ ADD THIS
        
        directories = self.get_user_directories(user_id)
        client = chromadb.PersistentClient(path=directories['temp_uploads'])
        try:
            return client.get_collection(collection_name)
        except:
            return client.create_collection(
                name=collection_name,  # ✅ USE VARIABLE
                metadata={"description": f"Temp uploads for user {user_id}"}
            )
    
    def update_temp_paths_to_main(self, user_id: str, session_id: str, collection_name: str = "document_embeddings") -> int:
        """
        Update VectorDB document paths from temp to main_corpus before file movement
        This prevents broken references after image files are moved
        """
        print(f"🔄 Updating VectorDB paths for user {user_id}, session {session_id}...")
        
        updated_count = 0
        
        try:
            # Get temp collection for this user
            temp_collection = self.get_user_temp_collection(user_id, collection_name)
            
            # Get all documents from temp collection
            results = temp_collection.get()
            documents = results.get('documents', [])
            metadatas = results.get('metadatas', [])
            ids = results.get('ids', [])
            
            if not documents:
                print("ℹ️ No documents in temp collection to update")
                return 0
            
            # Update paths in metadata from temp to main_corpus
            updated_metadatas = []
            for metadata in metadatas:
                if metadata and 'image_path' in metadata:
                    old_path = metadata['image_path']
                    # Convert temp path to main corpus path
                    if f"temp_uploads/{session_id}" in old_path:
                        # Extract just the filename
                        filename = os.path.basename(old_path)
                        new_path = f"images/{user_id}/main_corpus/{filename}"
                        metadata['image_path'] = new_path
                        updated_count += 1
                        print(f"   🔄 {filename}")
                
                updated_metadatas.append(metadata)
            
            # Update the collection with corrected paths
            if updated_count > 0:
                temp_collection.update(
                    ids=ids,
                    metadatas=updated_metadatas
                )
                print(f"✅ Updated {updated_count} VectorDB paths from temp→main")
            else:
                print("ℹ️ No paths needed updating (already correct)")
            
            return updated_count
            
        except Exception as e:
            print(f"❌ Error updating VectorDB paths: {e}")
            return 0
    
    def merge_temp_to_main(self, user_id: str, collection_name: str = "document_embeddings") -> int:
        """Merge temp_uploads into main_corpus - FIXED APPEND LOGIC"""
        print(f"🔄 Merging temp→main for user: {user_id}")
        
        directories = self.get_user_directories(user_id)
        
        try:
            # Load temp_uploads data
            temp_client = chromadb.PersistentClient(path=directories['temp_uploads'])
            temp_collection = temp_client.get_collection(collection_name)
            temp_data = temp_collection.get(include=['embeddings', 'metadatas', 'documents'])
            
            if not temp_data['ids']:
                print(f"⚠️ No documents in temp_uploads for user {user_id}")
                return 0
            
            print(f"📊 Found {len(temp_data['ids'])} documents in temp_uploads")
            
            # Load main_corpus collection
            main_client = chromadb.PersistentClient(path=directories['main_corpus'])
            try:
                main_collection = main_client.get_collection(collection_name)
                current_main_count = main_collection.count()
                print(f"📁 Adding to existing main corpus ({current_main_count} docs)")
            except:
                main_collection = main_client.create_collection(
                    name=collection_name,
                    metadata={"description": f"Main corpus for user {user_id}"}
                )
                current_main_count = 0
                print("📁 Created new main corpus collection")
            
            # 🆕 CRITICAL FIX: Generate unique IDs to avoid overwriting
            import uuid
            unique_ids = [f"temp_{id}_{uuid.uuid4().hex[:8]}" for id in temp_data['ids']]
            
            # Add temp data to main corpus
            main_collection.add(
                ids=unique_ids,  # Use unique IDs
                embeddings=temp_data['embeddings'],
                metadatas=temp_data['metadatas'],
                documents=temp_data['documents']
            )
            
            new_total = main_collection.count()
            added_count = new_total - current_main_count
            
            print(f"✅ Successfully added {added_count} documents to main corpus")
            print(f"📊 New total in main corpus: {new_total}")
            
            # Clear temp_uploads after successful merge
            self.clear_temp_uploads(user_id, collection_name)
            
            return added_count
            
        except Exception as e:
            print(f"❌ Error merging collections for user {user_id}: {e}")
            return 0
    
    def clear_temp_uploads(self, user_id: str, collection_name: str = "document_embeddings"):
        """Clear temporary uploads for a user"""
        directories = self.get_user_directories(user_id)
        
        try:
            temp_client = chromadb.PersistentClient(path=directories['temp_uploads'])
            temp_client.delete_collection(collection_name)
            # Recreate empty collection
            temp_client.create_collection(collection_name)
            print(f"✅ Cleared temp_uploads for user {user_id}")
        except Exception as e:
            print(f"⚠️ Could not clear temp_uploads for user {user_id}: {e}")
    
    def get_user_stats(self, user_id: str, collection_name: str = "document_embeddings") -> Dict:
        """Get statistics for a user's vector stores"""
        directories = self.get_user_directories(user_id)
        stats = {'user_id': user_id}
        
        try:
            # Main corpus stats
            main_client = chromadb.PersistentClient(path=directories['main_corpus'])
            main_collection = main_client.get_collection(collection_name)
            stats['main_corpus_documents'] = main_collection.count()
        except:
            stats['main_corpus_documents'] = 0
        
        try:
            # Temp uploads stats
            temp_client = chromadb.PersistentClient(path=directories['temp_uploads'])
            temp_collection = temp_client.get_collection(collection_name)
            stats['temp_uploads_documents'] = temp_collection.count()
        except:
            stats['temp_uploads_documents'] = 0
        
        stats['total_documents'] = stats['main_corpus_documents'] + stats['temp_uploads_documents']
        return stats
    
    def force_sync_corpus(self, user_id: str, collection_name: str = "document_embeddings") -> int:
        """
        Force sync temp_uploads to main_corpus - use this if merge fails
        This ensures corpus_only mode always has data
        """
        print(f"🔄 Force syncing corpus for user: {user_id}")
        
        directories = self.get_user_directories(user_id)
        
        try:
            # Check if temp_uploads has data
            temp_client = chromadb.PersistentClient(path=directories['temp_uploads'])
            temp_collection = temp_client.get_collection(collection_name)
            temp_data = temp_collection.get()
            
            if not temp_data['ids']:
                print(f"⚠️ No data in temp_uploads to sync for user {user_id}")
                return 0
            
            # Copy entire temp_uploads directory to main_corpus
            if os.path.exists(directories['main_corpus']):
                shutil.rmtree(directories['main_corpus'])
            
            shutil.copytree(directories['temp_uploads'], directories['main_corpus'])
            
            # Verify
            main_client = chromadb.PersistentClient(path=directories['main_corpus'])
            main_collection = main_client.get_collection(collection_name)
            
            print(f"✅ Force sync completed: {main_collection.count()} documents in main_corpus")
            return main_collection.count()
            
        except Exception as e:
            print(f"❌ Force sync failed: {e}")
            return 0
        
    def query_collections_separately(self, user_id: str, query_embedding: List[float], n_results: int = 20):
        """Query main_corpus and temp_uploads separately and return combined results"""
        print(f"🔍 Querying collections separately for user: {user_id}")
        
        directories = self.get_user_directories(user_id)
        all_results = {
            'main_corpus': {'text_results': [], 'image_results': []},
            'temp_uploads': {'text_results': [], 'image_results': []},
            'combined': {'text_results': [], 'image_results': []}
        }
        
        try:
            # Query main_corpus - 🆕 INCLUDE EMBEDDINGS
            main_client = chromadb.PersistentClient(path=directories['main_corpus'])
            try:
                main_collection = main_client.get_collection("document_embeddings")
                main_results = main_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    include=["embeddings", "metadatas", "documents", "distances"]  # 🆕 ADD "embeddings"
                )
                all_results['main_corpus'] = self._process_query_results(main_results, "main_corpus")
                print(f"✅ Main corpus: {len(all_results['main_corpus']['text_results'])} text, {len(all_results['main_corpus']['image_results'])} images")
            except Exception as e:
                print(f"⚠️ No main corpus found: {e}")
            
            # Query temp_uploads - 🆕 INCLUDE EMBEDDINGS
            temp_client = chromadb.PersistentClient(path=directories['temp_uploads'])
            try:
                temp_collection = temp_client.get_collection("document_embeddings")
                temp_results = temp_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    include=["embeddings", "metadatas", "documents", "distances"]  # 🆕 ADD "embeddings"
                )
                all_results['temp_uploads'] = self._process_query_results(temp_results, "temp_uploads")
                print(f"✅ Temp uploads: {len(all_results['temp_uploads']['text_results'])} text, {len(all_results['temp_uploads']['image_results'])} images")
            except Exception as e:
                print(f"⚠️ No temp uploads found: {e}")
            
            # Combine with 70% temp / 30% main weighting
            all_results['combined'] = self._combine_weighted_results(
                all_results['main_corpus'], 
                all_results['temp_uploads'],
                temp_weight=0.7,
                main_weight=0.3
            )
            
            print(f"🎯 Combined: {len(all_results['combined']['text_results'])} text, {len(all_results['combined']['image_results'])} images")
            return all_results
            
        except Exception as e:
            print(f"❌ Error querying collections: {e}")
            return all_results

    def _process_query_results(self, results, source: str):
        """Process query results into standardized format"""
        if not results['ids'] or not results['ids'][0]:
            return {'text_results': [], 'image_results': []}
        
        text_results = []
        image_results = []
        
        # 🆕 ADD EMBEDDING TO THE LOOP
        for i, (doc_id, embedding, metadata, document, distance) in enumerate(zip(
            results['ids'][0], 
            results['embeddings'][0],  # 🆕 ADD THIS
            results['metadatas'][0], 
            results['documents'][0],
            results['distances'][0]
        )):
            similarity_score = 1 - (distance / 2)
            
            result_item = {
                'id': doc_id,
                'content': document,
                'similarity_score': round(similarity_score, 4),
                'metadata': metadata,
                'source': source,
                'embedding': embedding  # ✅ NOW THIS WILL WORK
            }
            
            if metadata['type'] == 'text_chunk':
                text_results.append(result_item)
            elif metadata['type'] == 'image_caption':
                image_results.append(result_item)
        
        # Sort by similarity score
        text_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        image_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return {
            'text_results': text_results,
            'image_results': image_results
        }

    def _combine_weighted_results(self, main_results: Dict, temp_results: Dict, temp_weight: float = 0.7, main_weight: float = 0.3):
        """Combine results with weighted distribution and deduplication"""
        print(f"🔄 Combining results with weights: temp={temp_weight}, main={main_weight}")
        
        # Calculate number of results to take from each source
        total_text_slots = 15  # Adjust based on your needs
        total_image_slots = 10
        
        temp_text_count = int(total_text_slots * temp_weight)
        main_text_count = total_text_slots - temp_text_count
        
        temp_image_count = int(total_image_slots * temp_weight)
        main_image_count = total_image_slots - temp_image_count
        
        # Take top results from each source
        temp_text = temp_results['text_results'][:temp_text_count]
        main_text = main_results['text_results'][:main_text_count]
        temp_images = temp_results['image_results'][:temp_image_count]
        main_images = main_results['image_results'][:main_image_count]
        
        # Remove duplicates based on content hash
        def deduplicate_results(results_list):
            seen_hashes = set()
            unique_results = []
            for result in results_list:
                content_hash = hashlib.md5(result['content'].encode()).hexdigest()
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    unique_results.append(result)
            return unique_results
        
        # Combine and deduplicate
        combined_text = deduplicate_results(temp_text + main_text)
        combined_images = deduplicate_results(temp_images + main_images)
        
        # Sort by similarity score
        combined_text.sort(key=lambda x: x['similarity_score'], reverse=True)
        combined_images.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        print(f"📊 Final combined: {len(combined_text)} text, {len(combined_images)} images (after deduplication)")
        
        return {
            'text_results': combined_text,
            'image_results': combined_images
        }


class OpenAITextEmbeddingModel:
    def __init__(self, model_name="text-embedding-3-small", api_key=None):
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        if not self.client.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        print(f"Loaded OpenAI embedding model: {model_name}")
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts using OpenAI API"""
        embeddings = []
        
        # Process in batches to avoid rate limits
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=batch_texts
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
                # Add small delay to avoid rate limits
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error generating embeddings for batch {i//batch_size}: {e}")
                embeddings.extend([[] for _ in batch_texts])
        
        return embeddings

class DocumentProcessor:
    def __init__(self, openai_api_key=None):
        self.embedding_model = OpenAITextEmbeddingModel(api_key=openai_api_key)
        self.chroma_manager = MultiUserChromaDBManager()
    
    # def process_json_file(self, json_file_path: str, user_id: str, session_id: str):
    #     """Process JSON file and create embeddings for both text and image captions with session context"""
    #     # Load JSON data
    #     with open(json_file_path, 'r', encoding='utf-8') as f:
    #         data = json.load(f)
        
    #     print(f"Processing {len(data['processed_chunks'])} chunks for user {user_id}, session {session_id}")
        
    #     # Prepare documents for embedding
    #     documents_to_embed = []
        
    #     for chunk in data['processed_chunks']:
    #         original_chunk_id = chunk['chunk_id']
    #         chunk_text = chunk['text']
    #         metadata = chunk['metadata']
            
    #         # Create session-aware chunk ID for text
    #         session_chunk_id = f"text_{original_chunk_id}"
            
    #         documents_to_embed.append({
    #             'id': session_chunk_id,
    #             'text': chunk_text,
    #             'embedding': None,
    #             'metadata': {
    #                 'type': 'text_chunk',
    #                 'chunk_id': session_chunk_id,
    #                 'original_doc_type': metadata['original_doc_type'],
    #                 'original_doc_id': metadata['original_doc_id'],
    #                 'user_id': user_id,
    #                 'session_id': session_id,  # Add session context
    #                 'word_count': metadata.get('word_count', 0),
    #                 'has_images': len(metadata.get('images_with_captions', [])) > 0
    #             }
    #         })
            
    #         # Create documents for image captions with session context
    #         images_with_captions = metadata.get('images_with_captions', [])
    #         for img_idx, img_data in enumerate(images_with_captions):
    #             caption = img_data['caption']
    #             if caption and not caption.startswith("Error:"):
    #                 image_chunk_id = f"image_{original_chunk_id}_img{img_idx}"
                    
    #                 documents_to_embed.append({
    #                     'id': image_chunk_id,
    #                     'text': caption,
    #                     'embedding': None,
    #                     'metadata': {
    #                         'type': 'image_caption',
    #                         'chunk_id': image_chunk_id,
    #                         'image_path': img_data['path'],
    #                         'caption': caption,
    #                         'original_doc_type': metadata['original_doc_type'],
    #                         'original_doc_id': metadata['original_doc_id'],
    #                         'user_id': user_id,
    #                         'session_id': session_id  # Add session context
    #                     }
    #                 })
        
    #     print(f"Total documents to embed for user {user_id}, session {session_id}: {len(documents_to_embed)}")
        
    #     # Generate embeddings using OpenAI
    #     texts_to_embed = [doc['text'] for doc in documents_to_embed]
    #     print("Generating embeddings with OpenAI...")
    #     embeddings = self.embedding_model.get_embeddings(texts_to_embed)
        
    #     # Assign embeddings back to documents
    #     for i, doc in enumerate(documents_to_embed):
    #         doc['embedding'] = embeddings[i]
        
    #     return documents_to_embed

    def _sanitize_chunk_id(self, chunk_id: str) -> str:
        """Remove problematic characters from chunk IDs for OpenAI embedding"""
        # Replace hyphens with underscores (the main problem!)
        safe_id = chunk_id.replace('-', '_')
        
        # Remove any other problematic characters but keep underscores
        import re
        safe_id = re.sub(r'[^\w_]', '', safe_id)  # Keep only word chars and underscore
        
        return safe_id

    def process_json_file(self, json_file_path: str, user_id: str, session_id: str):
        """Process JSON file and create embeddings for both text and image captions with session context"""
        # Load JSON data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Processing {len(data['processed_chunks'])} chunks for user {user_id}, session {session_id}")
        
        # Prepare documents for embedding
        documents_to_embed = []
        
        text_count = 0
        image_count = 0
        
        for chunk in data['processed_chunks']:
            original_chunk_id = chunk['chunk_id']
            chunk_text = chunk['text']
            metadata = chunk['metadata']
            
            # Create session-aware chunk ID for text
            # session_chunk_id = f"text_{original_chunk_id}"
            session_chunk_id = f"text_{self._sanitize_chunk_id(original_chunk_id)}"

            
            documents_to_embed.append({
                'id': session_chunk_id,
                'text': chunk_text,
                'embedding': None,
                'metadata': {
                    'type': 'text_chunk',
                    'chunk_id': session_chunk_id,
                    'original_doc_type': metadata['original_doc_type'],
                    'original_doc_id': metadata['original_doc_id'],
                    'user_id': user_id,
                    'session_id': session_id,
                    'word_count': metadata.get('word_count', 0),
                    'has_images': len(metadata.get('images_with_captions', [])) > 0
                }
            })
            text_count += 1
            
            # Create documents for image captions with session context
            images_with_captions = metadata.get('images_with_captions', [])
            for img_idx, img_data in enumerate(images_with_captions):
                caption = img_data['caption']
                if caption and not caption.startswith("Error:"):
                    # image_chunk_id = f"image_{original_chunk_id}_img{img_idx}"
                    image_chunk_id = f"image_{self._sanitize_chunk_id(original_chunk_id)}_img{img_idx}"

                    
                    documents_to_embed.append({
                        'id': image_chunk_id,
                        'text': caption,
                        'embedding': None,
                        'metadata': {
                            'type': 'image_caption',
                            'chunk_id': image_chunk_id,
                            'image_path': img_data['path'],
                            'caption': caption,
                            'original_doc_type': metadata['original_doc_type'],
                            'original_doc_id': metadata['original_doc_id'],
                            'user_id': user_id,
                            'session_id': session_id
                        }
                    })
                    image_count += 1
                    print(f"  📸 Added image caption: {caption[:50]}...")
        
        print(f"📊 Total documents to embed: {len(documents_to_embed)}")
        print(f"   - Text chunks: {text_count}")
        print(f"   - Image captions: {image_count}")
        
        # Generate embeddings using OpenAI
        texts_to_embed = [doc['text'] for doc in documents_to_embed]
        print("Generating embeddings with OpenAI...")
        embeddings = self.embedding_model.get_embeddings(texts_to_embed)
        
        # Assign embeddings back to documents
        successful_embeddings = 0
        for i, doc in enumerate(documents_to_embed):
            if i < len(embeddings) and embeddings[i]:
                doc['embedding'] = embeddings[i]
                successful_embeddings += 1
            else:
                print(f"  ❌ Failed to get embedding for: {doc['id']}")
        
        print(f"✅ Successfully generated {successful_embeddings}/{len(documents_to_embed)} embeddings")
        
        return documents_to_embed
    
    def store_in_chromadb(self, documents: List[Dict], user_id: str, storage_mode: str = "temp_uploads", collection_name: str = "document_embeddings"):
        """Store documents in ChromaDB with user isolation"""
        if storage_mode not in ["temp_uploads", "main_corpus"]:
            raise ValueError("storage_mode must be 'temp_uploads' or 'main_corpus'")
        
        directories = self.chroma_manager.get_user_directories(user_id)
        client_path = directories[storage_mode]
        
        client = chromadb.PersistentClient(path=client_path)
        
        try:
            collection = client.get_collection(collection_name)
            print(f"📁 Adding to existing {storage_mode} collection for user {user_id}")
        except:
            collection = client.create_collection(
                name=collection_name,
                metadata={"description": f"Document embeddings for user {user_id} - {storage_mode}"}
            )
            print(f"📁 Created new {storage_mode} collection for user {user_id}")
        
        # Prepare data for ChromaDB
        ids = []
        texts = []
        embeddings = []
        metadatas = []
        
        for doc in documents:
            ids.append(doc['id'])
            texts.append(doc['text'])
            embeddings.append(doc['embedding'])
            metadatas.append(doc['metadata'])
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        
        print(f"✅ Added {len(ids)} documents to {storage_mode} for user {user_id}")
        return collection

class QueryRetriever:
    def __init__(self, user_id: str, mode: str = "uploaded_only", openai_api_key=None):
        self.user_id = user_id
        self.mode = mode
        self.chroma_manager = MultiUserChromaDBManager()
        self.embedding_model = OpenAITextEmbeddingModel(api_key=openai_api_key)
        self.collection = None
        self.client = None
        self.load_collection()
    
    def load_collection(self, collection_name: str = "document_embeddings"):
        """Load the collection from ChromaDB based on mode"""
        try:
            self.collection, self.client = self.chroma_manager.get_collection_for_mode(
                self.user_id, self.mode, collection_name
            )
            print(f"Collection loaded for user {self.user_id} with {self.collection.count()} documents")
        except Exception as e:
            print(f"Error loading collection for user {self.user_id}: {e}")
            self.collection = None
    
    def search(self, query: str, n_results: int = 10, include_images: bool = True):
        if not self.collection:
            print("Collection not loaded!")
            return None
        
        # Generate query embedding using OpenAI
        query_embedding = self.embedding_model.get_embeddings([query])[0]
        
        # Search in ChromaDB - 🆕 INCLUDE EMBEDDINGS
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 2,
            include=["embeddings", "metadatas", "documents", "distances"]  # ✅ ADD EMBEDDINGS
        )
        
        # Process results
        processed_results = self._process_search_results(results, query, include_images)
        return processed_results
    
    def _process_search_results(self, results, query: str, include_images: bool):
        """Process and format search results"""
        if not results['ids'] or not results['ids'][0]:
            return {"text_results": [], "image_results": [], "query": query}
        
        text_results = []
        image_results = []
        
        # 🆕 ADD EMBEDDING TO THE LOOP
        for i, (doc_id, embedding, metadata, document, distance) in enumerate(zip(
            results['ids'][0], 
            results['embeddings'][0],  # 🆕 ADD THIS
            results['metadatas'][0], 
            results['documents'][0],
            results['distances'][0]
        )):
            # Convert distance to similarity score (0-1)
            similarity_score = 1 - (distance / 2)
            
            result_item = {
                'id': doc_id,
                'content': document,
                'similarity_score': round(similarity_score, 4),
                'metadata': metadata,
                'embedding': embedding  # ✅ ADD EMBEDDING
            }
            
            if metadata['type'] == 'text_chunk':
                text_results.append(result_item)
            elif metadata['type'] == 'image_caption' and include_images:
                image_results.append(result_item)
        
        # Sort by similarity score and limit results
        text_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        image_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return {
            "query": query,
            "text_results": text_results[:10],
            "image_results": image_results[:5],
            "total_text_matches": len(text_results),
            "total_image_matches": len(image_results),
            "search_mode": self.mode,
            "user_id": self.user_id
        }
    
    def print_results(self, results: Dict):
        """Print formatted search results"""
        print(f"\n🔍 Search Results for: '{results['query']}'")
        print(f"👤 User: {results['user_id']}")
        print(f"📊 Mode: {results['search_mode']}")
        print(f"📄 Found {results['total_text_matches']} text matches")
        print(f"🖼️  Found {results['total_image_matches']} image matches")
        
        # Print text results
        if results['text_results']:
            print(f"\n📖 TOP TEXT RESULTS:")
            for i, result in enumerate(results['text_results'][:5], 1):
                print(f"{i}. [Score: {result['similarity_score']}]")
                print(f"   Doc: {result['metadata']['original_doc_id']}")
                print(f"   Type: {result['metadata']['original_doc_type']}")
                print(f"   Session: {result['metadata'].get('session_id', 'unknown')}")
                print(f"   Content: {result['content'][:150]}...")
                print()
        
        # Print image results
        if results['image_results']:
            print(f"\n🖼️  RELEVANT IMAGES:")
            for i, result in enumerate(results['image_results'][:3], 1):
                print(f"{i}. [Score: {result['similarity_score']}]")
                print(f"   Image: {os.path.basename(result['metadata']['image_path'])}")
                print(f"   Caption: {result['metadata']['caption']}")
                print(f"   Source: {result['metadata']['original_doc_id']}")
                print(f"   Session: {result['metadata'].get('session_id', 'unknown')}")
                print()

def main_embedding_pipeline(openai_api_key=None, user_id: str = None, session_id: str = None):
    """Main function to process JSON and create embeddings for specific user and session"""
    if not user_id or not session_id:
        raise ValueError("user_id and session_id are required for embedding pipeline")
    
    json_file_path = f"processed_json/{user_id}/step4_deduplicated_{user_id}_{session_id}.json"
    
    print(f"Starting embedding pipeline for user {user_id}, session {session_id}...")
    
    # Process documents and create embeddings
    processor = DocumentProcessor(openai_api_key=openai_api_key)
    documents = processor.process_json_file(json_file_path, user_id, session_id)
    
    # Store in ChromaDB temp_uploads
    processor.store_in_chromadb(documents, user_id, storage_mode="temp_uploads")
    
    print(f"✅ Embedding pipeline completed for user {user_id}, session {session_id}!")
    return processor

def interactive_search(openai_api_key=None, user_id: str = None):
    """Interactive search interface"""
    if not user_id:
        raise ValueError("user_id is required for search")
    
    print(f"🚀 Interactive Search Interface for User: {user_id}")
    print("Available modes:")
    print("1. uploaded_only - Only current uploads")
    print("2. uploaded_plus_corpus - Current uploads + corpus")
    print("3. corpus_only - Only corpus (no current uploads)")
    
    mode_choice = input("Choose mode (1/2/3, default 1): ").strip()
    mode_map = {"1": "uploaded_only", "2": "uploaded_plus_corpus", "3": "corpus_only"}
    mode = mode_map.get(mode_choice, "uploaded_only")
    
    retriever = QueryRetriever(user_id=user_id, mode=mode, openai_api_key=openai_api_key)
    
    print(f"Type 'quit' to exit, 'mode' to change mode\n")
    
    while True:
        query = input("🔍 Enter your search query: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if query.lower() == 'mode':
            mode_choice = input("Choose mode (1/2/3): ").strip()
            mode = mode_map.get(mode_choice, "uploaded_only")
            retriever = QueryRetriever(user_id=user_id, mode=mode, openai_api_key=openai_api_key)
            continue
        
        if not query:
            continue
        
        print("Searching...")
        results = retriever.search(query, n_results=15, include_images=True)
        
        if results:
            retriever.print_results(results)
        else:
            print("No results found or error in search.")
        
        print("-" * 80)

# Alternative: One-time search function
def search_query(query: str, user_id: str, mode: str = "uploaded_only", n_results: int = 10, openai_api_key=None):
    """Search for a specific query"""
    retriever = QueryRetriever(user_id=user_id, mode=mode, openai_api_key=openai_api_key)
    results = retriever.search(query, n_results=n_results, include_images=True)
    
    if results:
        retriever.print_results(results)
        return results
    else:
        print("No results found.")
        return None

# Utility function to merge temp to main corpus
def merge_user_data(user_id: str):
    """Merge temp_uploads to main_corpus for a user"""
    chroma_manager = MultiUserChromaDBManager()
    count = chroma_manager.merge_temp_to_main(user_id)
    
    if count > 0:
        print(f"✅ Successfully merged {count} documents for user {user_id}")
    else:
        print(f"⚠️  No documents to merge for user {user_id}")
    
    return count

# Utility function to get user statistics
def get_user_stats(user_id: str):
    """Get statistics for a user's vector stores"""
    chroma_manager = MultiUserChromaDBManager()
    return chroma_manager.get_user_stats(user_id)










def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
    """Generate embeddings with OpenAI API - WITH TEXT VALIDATION"""
    if not texts:
        return []
    
    print(f"📊 Generating embeddings for {len(texts)} texts...")
    
    # FILTER OUT INVALID TEXTS FIRST
    valid_texts = []
    invalid_indices = []
    
    for i, text in enumerate(texts):
        # Check if text is valid for OpenAI
        if self._is_valid_text_for_embedding(text):
            valid_texts.append(text)
        else:
            invalid_indices.append(i)
            print(f"  ⚠️ Skipping invalid text at index {i}: '{text[:50]}...'")
    
    print(f"📊 Valid texts: {len(valid_texts)}/{len(texts)}")
    
    if not valid_texts:
        return [[] for _ in range(len(texts))]
    
    # Process in batches
    all_embeddings = [[] for _ in range(len(texts))]  # Placeholder for all
    BATCH_SIZE = 50
    
    for i in range(0, len(valid_texts), BATCH_SIZE):
        batch = valid_texts[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            
            # Map back to original indices
            valid_index = 0
            for j in range(len(texts)):
                if j not in invalid_indices:
                    if valid_index < len(response.data):
                        all_embeddings[j] = response.data[valid_index].embedding
                        valid_index += 1
        
        except Exception as e:
            print(f"❌ Batch {batch_num} failed: {e}")
    
    return all_embeddings

def _is_valid_text_for_embedding(self, text: str) -> bool:
    """Validate text before sending to OpenAI"""
    if not text or not isinstance(text, str):
        return False
    
    # Check for empty or whitespace-only
    if not text.strip():
        return False
    
    # Check for extremely long text (chars)
    if len(text) > 30000:  # ~7500 tokens
        print(f"  ⚠️ Text too long: {len(text)} chars")
        return False
    
    # Check for invalid characters that might break OpenAI
    if '\x00' in text or '\ufffd' in text:  # Null char or replacement char
        return False
    
    # Check if it's just special characters
    import re
    if re.sub(r'[^\w\s]', '', text).strip() == '':
        return False
    
    return True


if __name__ == "__main__":
    # Example usage
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    USER_ID = "user_123"
    SESSION_ID = "upload_1"
    
    if not OPENAI_API_KEY:
        print("❌ Please set OPENAI_API_KEY environment variable")
        exit(1)
    
    # Process documents for a user and session
    main_embedding_pipeline(openai_api_key=OPENAI_API_KEY, user_id=USER_ID, session_id=SESSION_ID)
    
    # Search in different modes
    search_query("AI surveillance", user_id=USER_ID, mode="uploaded_only", openai_api_key=OPENAI_API_KEY)
    
    # Get user stats
    stats = get_user_stats(USER_ID)
    print(f"User {USER_ID} stats: {stats}")
    
    # Merge after successful generation
    merge_user_data(USER_ID)