# check_vectordb_images.py

import os
import chromadb

def check_vectordb_images(user_id: str):
    """Check all image names and their mapped paths in VectorDB"""
    print(f"🔍 Checking VectorDB images for user: {user_id}")
    
    # Check temp_uploads (where your data currently is)
    temp_dir = f"chroma_db/{user_id}/temp_uploads"
    
    if not os.path.exists(temp_dir):
        print(f"❌ Temp uploads directory not found: {temp_dir}")
        return
    
    try:
        client = chromadb.PersistentClient(path=temp_dir)
        collection = client.get_collection("document_embeddings")
        
        print(f"✅ Found collection with {collection.count()} total documents")
        
        # Get ALL documents
        results = collection.get()
        
        image_entries = []
        
        for i, (doc_id, metadata, document) in enumerate(zip(results['ids'], results['metadatas'], results['documents'])):
            # Only look at image caption entries
            if metadata and metadata.get('type') == 'image_caption':
                image_path = metadata.get('image_path', '')
                image_filename = os.path.basename(image_path)
                
                image_entries.append({
                    'vector_id': doc_id,
                    'image_filename': image_filename,
                    'image_path': image_path,
                    'caption': document,
                    'session_id': metadata.get('session_id', 'unknown'),
                    'source_doc': metadata.get('original_doc_id', 'unknown')
                })
        
        print(f"\n🖼️  FOUND {len(image_entries)} IMAGE CAPTION ENTRIES:")
        print("=" * 80)
        
        for i, entry in enumerate(image_entries, 1):
            print(f"{i:2d}. 📷 {entry['image_filename']}")
            print(f"    🗺️  Path: {entry['image_path']}")
            print(f"    📝 Caption: {entry['caption'][:80]}...")
            print(f"    👤 Session: {entry['session_id']}")
            print(f"    📄 Source: {entry['source_doc']}")
            print()
        
        # Summary
        print("=" * 80)
        print("📊 SUMMARY:")
        print(f"   - Total image entries: {len(image_entries)}")
        
        # Check path types
        temp_paths = sum(1 for entry in image_entries if "temp_uploads" in entry['image_path'])
        main_paths = sum(1 for entry in image_entries if "main_corpus" in entry['image_path'])
        other_paths = len(image_entries) - temp_paths - main_paths
        
        print(f"   - Temp uploads paths: {temp_paths}")
        print(f"   - Main corpus paths: {main_paths}")
        print(f"   - Other paths: {other_paths}")
        
        # List unique image filenames
        unique_filenames = set(entry['image_filename'] for entry in image_entries)
        print(f"   - Unique image files: {len(unique_filenames)}")
        
        return image_entries
        
    except Exception as e:
        print(f"❌ Error checking VectorDB: {e}")
        return []

def check_physical_vs_vectordb(user_id: str):
    """Compare physical images vs VectorDB entries"""
    print(f"\n🔍 COMPARING PHYSICAL vs VECTORDB for user: {user_id}")
    
    # Get physical images
    main_corpus_dir = f"images/{user_id}/main_corpus"
    physical_images = []
    
    if os.path.exists(main_corpus_dir):
        for filename in os.listdir(main_corpus_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                physical_images.append(filename)
    
    print(f"📸 Physical images in main_corpus: {len(physical_images)}")
    
    # Get VectorDB images
    vectordb_entries = check_vectordb_images(user_id)
    vectordb_filenames = [entry['image_filename'] for entry in vectordb_entries]
    
    print(f"\n🔄 COMPARISON RESULTS:")
    print(f"   - Physical images: {len(physical_images)}")
    print(f"   - VectorDB entries: {len(vectordb_filenames)}")
    
    # Find matches and mismatches
    physical_set = set(physical_images)
    vectordb_set = set(vectordb_filenames)
    
    matched = physical_set & vectordb_set
    physical_only = physical_set - vectordb_set
    vectordb_only = vectordb_set - physical_set
    
    print(f"   - Matched: {len(matched)}")
    print(f"   - Physical only (no VectorDB): {len(physical_only)}")
    print(f"   - VectorDB only (no physical): {len(vectordb_only)}")
    
    if physical_only:
        print(f"\n⚠️  PHYSICAL IMAGES WITHOUT VECTORDB ENTRIES:")
        for img in sorted(list(physical_only))[:10]:  # Show first 10
            print(f"   - {img}")
    
    if vectordb_only:
        print(f"\n⚠️  VECTORDB ENTRIES WITHOUT PHYSICAL IMAGES:")
        for img in sorted(list(vectordb_only))[:10]:  # Show first 10
            print(f"   - {img}")

if __name__ == "__main__":
    user_id = "test2"  # Replace with your user ID
    
    # Option 1: Just check VectorDB images
    print("OPTION 1: Check VectorDB images only")
    image_entries = check_vectordb_images(user_id)
    
    # Option 2: Compare physical vs VectorDB
    print("\n" + "="*100)
    print("OPTION 2: Compare physical images vs VectorDB entries")
    check_physical_vs_vectordb(user_id)