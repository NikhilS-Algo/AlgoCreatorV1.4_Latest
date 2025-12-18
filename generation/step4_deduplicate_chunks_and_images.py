#step4_deduplicate_chunks_and_images.py

import json
import hashlib
from typing import List, Dict, Any, Set, Tuple
import os
from collections import defaultdict
import re


from dotenv import load_dotenv
load_dotenv()

class DocumentDeduplicator:
    def __init__(self, similarity_threshold: float = 0.9, min_text_length: int = 10):
        """
        Initialize deduplicator
        
        Args:
            similarity_threshold: Threshold for considering text as duplicate (0.0 to 1.0)
            min_text_length: Minimum text length to consider for deduplication
        """
        self.similarity_threshold = similarity_threshold
        self.min_text_length = min_text_length
        
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for comparison"""
        # Convert to lowercase
        text = text.lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove punctuation and special characters
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using Jaccard similarity
        """
        if not text1 or not text2:
            return 0.0
            
        # Clean texts
        text1_clean = self._clean_text(text1)
        text2_clean = self._clean_text(text2)
        
        # Create word sets
        words1 = set(text1_clean.split())
        words2 = set(text2_clean.split())
        
        if not words1 or not words2:
            return 0.0
            
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_text_hash(self, text: str) -> str:
        """Generate hash for text content"""
        clean_text = self._clean_text(text)
        return hashlib.md5(clean_text.encode()).hexdigest()
    
    def _generate_image_caption_hash(self, caption: str) -> str:
        """Generate hash for image caption"""
        clean_caption = self._clean_text(caption)
        return hashlib.md5(clean_caption.encode()).hexdigest()
    
    def find_duplicate_text_chunks(self, chunks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Find and remove duplicate text chunks
        
        Returns:
            Tuple of (unique_chunks, duplicate_chunks)
        """
        unique_chunks = []
        duplicate_chunks = []
        seen_hashes = set()
        seen_similar = set()
        
        print("🔍 Analyzing text chunks for duplicates...")
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '')
            
            # Skip chunks that are too short
            if len(chunk_text.strip()) < self.min_text_length:
                unique_chunks.append(chunk)
                continue
            
            # Generate hash for exact matching
            text_hash = self._generate_text_hash(chunk_text)
            
            # Check for exact duplicates
            if text_hash in seen_hashes:
                duplicate_chunks.append(chunk)
                print(f"   🗑️  Exact duplicate removed: {chunk_text[:50]}...")
                continue
            
            # Check for similar content
            is_duplicate = False
            for unique_chunk in unique_chunks:
                unique_text = unique_chunk.get('text', '')
                similarity = self._calculate_text_similarity(chunk_text, unique_text)
                
                if similarity >= self.similarity_threshold:
                    duplicate_chunks.append(chunk)
                    print(f"   🗑️  Similar content removed (similarity: {similarity:.2f}): {chunk_text[:50]}...")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_chunks.append(chunk)
                seen_hashes.add(text_hash)
        
        print(f"📊 Text chunks: {len(chunks)} → {len(unique_chunks)} unique, {len(duplicate_chunks)} duplicates")
        return unique_chunks, duplicate_chunks
    
    def find_duplicate_images(self, chunks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Find and remove chunks with duplicate image captions
        
        Returns:
            Tuple of (unique_chunks, duplicate_chunks)
        """
        unique_chunks = []
        duplicate_chunks = []
        seen_caption_hashes = set()
        seen_image_paths = set()
        
        print("🔍 Analyzing image captions for duplicates...")
        
        for chunk in chunks:
            images_with_captions = chunk['metadata'].get('images_with_captions', [])
            
            # Skip chunks without images
            if not images_with_captions:
                unique_chunks.append(chunk)
                continue
            
            # Check for duplicate image paths
            image_paths = [img['path'] for img in images_with_captions if img.get('path')]
            has_duplicate_path = any(path in seen_image_paths for path in image_paths)
            
            # Check for duplicate captions
            has_duplicate_caption = False
            for img_data in images_with_captions:
                caption = img_data.get('caption', '')
                if caption and not caption.startswith('Error:'):
                    caption_hash = self._generate_image_caption_hash(caption)
                    if caption_hash in seen_caption_hashes:
                        has_duplicate_caption = True
                        break
            
            if has_duplicate_path or has_duplicate_caption:
                duplicate_chunks.append(chunk)
                if has_duplicate_path:
                    print(f"   🗑️  Duplicate image path: {image_paths[0] if image_paths else 'Unknown'}")
                if has_duplicate_caption:
                    print(f"   🗑️  Duplicate image caption: {caption[:50]}...")
            else:
                unique_chunks.append(chunk)
                # Add to seen sets
                for path in image_paths:
                    seen_image_paths.add(path)
                for img_data in images_with_captions:
                    caption = img_data.get('caption', '')
                    if caption and not caption.startswith('Error:'):
                        caption_hash = self._generate_image_caption_hash(caption)
                        seen_caption_hashes.add(caption_hash)
        
        print(f"📊 Image chunks: {len(chunks)} → {len(unique_chunks)} unique, {len(duplicate_chunks)} duplicates")
        return unique_chunks, duplicate_chunks
    
    def merge_chunk_metadata(self, chunks: List[Dict]) -> List[Dict]:
        """
        Merge metadata from duplicate chunks into unique chunks
        """
        # Group chunks by their cleaned text content
        chunks_by_content = defaultdict(list)
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '')
            if len(chunk_text.strip()) >= self.min_text_length:
                content_hash = self._generate_text_hash(chunk_text)
                chunks_by_content[content_hash].append(chunk)
            else:
                # For short chunks, keep them as is
                chunks_by_content[hashlib.md5(chunk_text.encode()).hexdigest()].append(chunk)
        
        merged_chunks = []
        
        for content_hash, similar_chunks in chunks_by_content.items():
            if len(similar_chunks) == 1:
                merged_chunks.append(similar_chunks[0])
            else:
                # Merge similar chunks
                base_chunk = similar_chunks[0].copy()
                
                # Collect all unique images from similar chunks
                all_images = []
                seen_image_paths = set()
                
                for chunk in similar_chunks:
                    images = chunk['metadata'].get('images_with_captions', [])
                    for img in images:
                        if img.get('path') and img['path'] not in seen_image_paths:
                            all_images.append(img)
                            seen_image_paths.add(img['path'])
                
                # Update metadata with merged images
                base_chunk['metadata']['images_with_captions'] = all_images
                base_chunk['metadata']['merged_from'] = len(similar_chunks)
                base_chunk['metadata']['original_chunk_ids'] = [
                    chunk['chunk_id'] for chunk in similar_chunks
                ]
                
                merged_chunks.append(base_chunk)
                print(f"   🔄 Merged {len(similar_chunks)} similar chunks into one")
        
        return merged_chunks
    

    def deduplicate_documents(self, input_file: str, user_id: str, session_id: str, output_file: str = None) -> Dict[str, Any]:
        """
        Main deduplication function
        """
        if not output_file:
            # Generate session-based output filename
            output_file = f"processed_json/{user_id}/step4_deduplicated_{user_id}_{session_id}.json"
        
        print(f"🚀 Starting deduplication process")
        print(f"👤 User: {user_id}, Session: {session_id}")
        print(f"📥 Input file: {input_file}")
        print(f"📤 Output file: {output_file}")
        
        # Load data - MOVE THIS TO THE TOP AND HANDLE ERRORS PROPERLY
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ Loaded JSON file: {input_file}")
        except Exception as e:
            print(f"❌ Error loading JSON file: {e}")
            return {
                'success': False,
                'error': f"Failed to load input file: {e}",
                'output_file': output_file
            }
        
        original_chunks = data.get('processed_chunks', [])
        print(f"📝 Original chunks: {len(original_chunks)}")
        
        if not original_chunks:
            print("⚠️  No chunks to process!")
            return {
                'success': False,
                'error': "No chunks found in input file",
                'output_file': output_file
            }
        
        # Step 1: Remove duplicate text chunks
        unique_text_chunks, text_duplicates = self.find_duplicate_text_chunks(original_chunks)
        
        # Step 2: Remove chunks with duplicate images
        final_chunks, image_duplicates = self.find_duplicate_images(unique_text_chunks)
        
        # Step 3: Merge similar chunks and their metadata
        merged_chunks = self.merge_chunk_metadata(final_chunks)
        
        # Update data
        data['processed_chunks'] = merged_chunks
        data['deduplication_stats'] = {
            'user_id': user_id,
            'session_id': session_id,
            'original_chunks': len(original_chunks),
            'after_text_deduplication': len(unique_text_chunks),
            'after_image_deduplication': len(final_chunks),
            'after_merging': len(merged_chunks),
            'text_duplicates_removed': len(text_duplicates),
            'image_duplicates_removed': len(image_duplicates),
            'similarity_threshold': self.similarity_threshold,
            'min_text_length': self.min_text_length
        }
        
        # Save deduplicated data with session-based name
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved deduplicated data to: {output_file}")
        except Exception as e:
            print(f"❌ Error saving output file: {e}")
            return {
                'success': False,
                'error': f"Failed to save output file: {e}",
                'output_file': output_file
            }
        
        # Print summary
        self._print_summary(data['deduplication_stats'])
        
        return {
            'success': True,
            'output_file': output_file,
            'stats': data['deduplication_stats'],
            'remaining_chunks': len(merged_chunks)
        }

    def _print_summary(self, stats: Dict):
        """Print deduplication summary"""
        print(f"\n🎯 DEDUPLICATION SUMMARY")
        print(f"=" * 50)
        print(f"📊 Original chunks: {stats['original_chunks']}")
        print(f"📝 After text deduplication: {stats['after_text_deduplication']}")
        print(f"🖼️  After image deduplication: {stats['after_image_deduplication']}")
        print(f"🔄 After merging: {stats['after_merging']}")
        print(f"🗑️  Text duplicates removed: {stats['text_duplicates_removed']}")
        print(f"🗑️  Image duplicates removed: {stats['image_duplicates_removed']}")
        print(f"📈 Reduction: {stats['original_chunks'] - stats['after_merging']} chunks ({((stats['original_chunks'] - stats['after_merging']) / stats['original_chunks'] * 100):.1f}%)")

def main():
    """Main function to run deduplication"""
    # Configuration
    USER_ID = "user_123"  # Change this to your user ID
    INPUT_FILE = f"step3_processed_documents_with_gpt4o_captions_{USER_ID}.json"
    
    print("🧹 Step 4: Document Deduplication")
    print("=" * 50)
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        print("Please run Step 3 first to generate the image captions file")
        return
    
    # Initialize deduplicator
    deduplicator = DocumentDeduplicator(
        similarity_threshold=0.85,  # Adjust based on your needs
        min_text_length=20
    )
    
    # Run deduplication
    try:
        result = deduplicator.deduplicate_documents(INPUT_FILE)
        
        if result['success']:
            print(f"\n✅ Deduplication completed successfully!")
            print(f"📁 Output file: {result['output_file']}")
        else:
            print(f"❌ Deduplication failed")
            
    except Exception as e:
        print(f"❌ Deduplication error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()