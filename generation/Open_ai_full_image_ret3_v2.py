import json
import os
from typing import List, Dict, Any
import numpy as np
from openai import OpenAI
from datetime import datetime

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


# Import the updated multi-user vector store
from step5_four_vector_store_with_image_caption_and_text import QueryRetriever, MultiUserChromaDBManager





class OptimizedImageMapper:
    def __init__(self, user_id: str, mode: str = "uploaded_plus_corpus", similarity_threshold: float = 0.4, openai_api_key=None):
        if not user_id:
            raise ValueError("user_id is required for image mapper")
            
        self.user_id = user_id
        self.mode = mode
        self.retriever = QueryRetriever(user_id=user_id, mode=mode, openai_api_key=openai_api_key)
        self.similarity_threshold = similarity_threshold
        self.used_image_ids = set()
    
    def summarize_slide_content(self, slide: Dict) -> str:
        """Create slide summary for better image matching"""
        summary_parts = []
        
        if slide.get('slide_title'):
            summary_parts.append(slide['slide_title'])
        
        if slide.get('key_takeaway'):
            summary_parts.append(slide['key_takeaway'])
        
        if slide.get('content'):
            content = slide['content'][:250]
            summary_parts.append(content)
        
        # Add context for AI surveillance
        summary_parts.append("AI surveillance security camera monitoring system technology")
        
        return " ".join(summary_parts)
    
    def extract_all_image_captions(self) -> List[Dict]:
        """Extract ALL image captions from ChromaDB using the correct metadata type"""
        print(f"Extracting image captions from ChromaDB for user {self.user_id}...")
        
        all_images = []
        
        try:
            # Get ALL documents from ChromaDB to find image captions
            all_docs = self.retriever.collection.get(
                include=['metadatas', 'documents', 'embeddings']
            )
            
            print(f"Total documents in DB for user {self.user_id}: {len(all_docs['ids'])}")
            
            image_count = 0
            for i, (doc_id, metadata, document, embedding) in enumerate(zip(
                all_docs['ids'], 
                all_docs['metadatas'], 
                all_docs['documents'], 
                all_docs['embeddings']
            )):
                # CORRECT: Look for 'image_caption' type in metadata
                if metadata.get('type') == 'image_caption':
                    image_count += 1
                    
                    # Use the image path or create unique ID
                    image_id = metadata.get('image_path', f"img_{doc_id}")
                    caption = metadata.get('caption', document)
                    
                    all_images.append({
                        'image_id': image_id,
                        'caption': caption,
                        'embedding': embedding,
                        'metadata': metadata,
                        'document_text': document,
                        'source_document': metadata.get('original_doc_id', 'unknown'),
                        'doc_id': doc_id,
                        'user_id': metadata.get('user_id', 'unknown')
                    })
            
            print(f"🎯 Total image captions found for user {self.user_id}: {image_count}")
            
            if image_count == 0:
                print("❌ No image captions found! Checking what types exist...")
                type_count = {}
                for metadata in all_docs['metadatas']:
                    doc_type = metadata.get('type', 'unknown')
                    type_count[doc_type] = type_count.get(doc_type, 0) + 1
                print(f"Document types in DB: {type_count}")
            
            return all_images
            
        except Exception as e:
            print(f"Error extracting images for user {self.user_id}: {e}")
            return []
    
    def find_best_images_for_slide(self, slide_embedding: List[float], all_images: List[Dict], slide_title: str) -> List[Dict]:
        """Find best images for slide from available image captions"""
        if not slide_embedding or not all_images:
            return []
        
        print(f"  Comparing with {len(all_images)} available images...")
        
        # Calculate similarities for all images
        scored_images = []
        for image in all_images:
            if image['image_id'] in self.used_image_ids:
                continue
                
            try:
                similarity = cosine_similarity([slide_embedding], [image['embedding']])[0][0]
                scored_images.append({
                    **image,
                    'similarity_score': float(similarity)
                })
            except Exception as e:
                print(f"  Error calculating similarity: {e}")
                continue
        
        # Sort by similarity
        scored_images.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # Show top 3 matches for debugging
        if scored_images:
            print(f"  Top 3 image matches:")
            for i, img in enumerate(scored_images[:3]):
                print(f"    {i+1}. Score: {img['similarity_score']:.3f} - {img['caption'][:60]}...")
        
        # Apply threshold
        suitable_images = [img for img in scored_images if img['similarity_score'] >= self.similarity_threshold]
        
        # If no images meet threshold, take only the top 1 anyway
        if not suitable_images and scored_images:
            print(f"  No images above threshold {self.similarity_threshold}, taking top 1 anyway")
            suitable_images = scored_images[:1]
        
        print(f"  Selected {len(suitable_images)} images for this slide")
        return suitable_images[:1]  # Max 1 per slide
    
    def map_images_to_slides(self, presentation_data: Dict) -> Dict:
        """Map image captions to slides using correct metadata detection"""
        
        enhanced_presentation = presentation_data.copy()
        
        # First, extract ALL image captions from database
        all_images = self.extract_all_image_captions()
        
        if not all_images:
            print("❌ NO IMAGE CAPTIONS FOUND IN DATABASE!")
            # Add empty images array to all slides
            for slide in enhanced_presentation.get('slides', []):
                slide['images'] = []
            return enhanced_presentation
        
        print(f"\n=== Starting Image Mapping for user {self.user_id} ===")
        print(f"📊 Available image captions: {len(all_images)}")
        print(f"🔍 Search mode: {self.mode}")
        
        total_slides_with_images = 0
        total_images_mapped = 0
        
        # Reset used images
        self.used_image_ids.clear()
        
        # Process each slide
        for slide_index, slide in enumerate(enhanced_presentation.get('slides', [])):
            slide_number = slide.get('slide_number', slide_index + 1)
            slide_title = slide.get('slide_title', 'No Title')
            
            # Skip first slide (introduction)
            if slide_index == 0:
                print(f"\n⏭️  Skipping introduction slide: {slide_title}")
                slide['images'] = []
                continue
            
            print(f"\n📊 Processing slide {slide_number}: {slide_title}")
            
            # Generate slide summary and embedding
            slide_summary = self.summarize_slide_content(slide)
            slide_embeddings = self.retriever.embedding_model.get_embeddings([slide_summary])
            
            if not slide_embeddings:
                slide['images'] = []
                continue
            
            slide_embedding = slide_embeddings[0]
            
            # Find best images for this slide
            best_images = self.find_best_images_for_slide(slide_embedding, all_images, slide_title)
            
            # Assign images to slide
            assigned_images = []
            for img in best_images:
                assigned_images.append({
                    'image_id': img['image_id'],
                    'caption': img['caption'],
                    'similarity_score': img['similarity_score'],
                    'source_document': img['source_document'],
                    'image_path': img['metadata'].get('image_path', ''),
                    'user_id': img['user_id'],
                    'relevance_rank': len(assigned_images) + 1
                })
                self.used_image_ids.add(img['image_id'])
                total_images_mapped += 1
            
            slide['images'] = assigned_images
            
            if assigned_images:
                total_slides_with_images += 1
                print(f"  ✅ Assigned {len(assigned_images)} images to slide {slide_number}")
                for img in assigned_images:
                    print(f"     - {img['caption'][:50]}... (score: {img['similarity_score']:.3f})")
            else:
                print(f"  ❌ No images assigned to slide {slide_number}")
        
        # Strategic distribution: If we have unused images, assign them to the most relevant slides
        unused_images = [img for img in all_images if img['image_id'] not in self.used_image_ids]
        if unused_images and total_slides_with_images < len(enhanced_presentation.get('slides', [])) - 1:
            print(f"\n🔄 Distributing {len(unused_images)} unused images...")
            
            # Find slides without images (excluding intro slide)
            slides_without_images = [(i, s) for i, s in enumerate(enhanced_presentation.get('slides', [])) 
                                   if i > 0 and not s.get('images')]
            
            for img_index, image in enumerate(unused_images):
                if img_index < len(slides_without_images):
                    slide_index, slide = slides_without_images[img_index]
                    slide['images'] = [{
                        'image_id': image['image_id'],
                        'caption': image['caption'],
                        'similarity_score': 0.2,
                        'source_document': image['source_document'],
                        'image_path': image['metadata'].get('image_path', ''),
                        'user_id': image['user_id'],
                        'relevance_rank': 1,
                        'strategic_assignment': True
                    }]
                    self.used_image_ids.add(image['image_id'])
                    total_images_mapped += 1
                    total_slides_with_images += 1
                    print(f"  Strategically assigned to slide {slide.get('slide_number', slide_index + 1)}")
        
        # Add statistics
        total_slides = len(enhanced_presentation.get('slides', []))
        content_slides = total_slides - 1  # Exclude intro slide
        
        enhanced_presentation['image_mapping_metrics'] = {
            'user_id': self.user_id,
            'search_mode': self.mode,
            'total_slides': total_slides,
            'content_slides': content_slides,
            'slides_with_images': total_slides_with_images,
            'total_images_mapped': total_images_mapped,
            'total_available_images': len(all_images),
            'images_used': len(self.used_image_ids),
            'similarity_threshold_used': self.similarity_threshold,
            'utilization_rate': f"{len(self.used_image_ids)}/{len(all_images)}"
        }
        
        print(f"\n=== MAPPING COMPLETE for user {self.user_id} ===")
        print(f"📈 Total slides: {total_slides}")
        print(f"📊 Content slides (excluding intro): {content_slides}")
        print(f"✅ Content slides with images: {total_slides_with_images}/{content_slides}")
        print(f"🖼️  Images used: {len(self.used_image_ids)}/{len(all_images)}")
        print(f"🔗 Total mappings: {total_images_mapped}")
        
        return enhanced_presentation

# Main function
# In Open_ai_full_image_ret3_v2.py - update the main function:

def enhance_presentation_optimized(presentation_json: Dict, user_id: str, is_file_uploaded_by_user: bool = False, mode: str = "corpus_only", openai_api_key: str = None) -> Dict:
    """Optimized version with user context"""
    
    if not user_id:
        raise ValueError("user_id is required for image enhancement")
    
    # NEW: Validate mode based on file upload status
    if not is_file_uploaded_by_user and mode != "corpus_only":
        error_msg = f"❌ Cannot use mode '{mode}'. No files uploaded by user. Please use 'corpus_only' mode."
        print(error_msg)
        return {"error": error_msg}
    
    print(f"🚀 Starting image enhancement for user: {user_id}")
    print(f"📁 User uploaded files: {'YES' if is_file_uploaded_by_user else 'NO'}")
    print(f"🔍 Mode: {mode}")
    
    image_mapper = OptimizedImageMapper(
        user_id=user_id, 
        mode=mode, 
        similarity_threshold=0.4,
        openai_api_key=openai_api_key
    )
    
    enhanced_presentation = image_mapper.map_images_to_slides(presentation_json)
    
    # Update metadata
    enhanced_presentation['generated_date'] = datetime.now().isoformat()
    enhanced_presentation['version'] = enhanced_presentation.get('version', '1.0') + "+images_multi_user"
    enhanced_presentation['user_id'] = user_id
    enhanced_presentation['image_retrieval_mode'] = mode
    enhanced_presentation['user_uploaded_files'] = is_file_uploaded_by_user
    
    return enhanced_presentation

# Also update the if __name__ == "__main__" section to include the new parameter:
if __name__ == "__main__":
    # Load your presentation JSON
    with open('presentation_introduction_to_aksha_ai_surveillance_system_final_simple_user_123.json', 'r') as f:
        presentation_data = json.load(f)
    
    # Enhance with images (optimized version with user context)
    enhanced_presentation = enhance_presentation_optimized(
        presentation_data, 
        user_id="user_123",
        is_file_uploaded_by_user=False,  # NEW: Add this parameter
        mode="corpus_only",  # Changed to corpus_only since no files uploaded
        openai_api_key="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"
    )
    
    # Check for error in response
    if "error" in enhanced_presentation:
        print(f"❌ Image enhancement failed: {enhanced_presentation['error']}")
    else:
        # Save enhanced presentation
        with open('presentation_with_images_multi_user_123.json', 'w') as f:
            json.dump(enhanced_presentation, f, indent=2)
        
        print("\n=== FINAL RESULT ===")
        metrics = enhanced_presentation['image_mapping_metrics']
        print(f"👤 User: {metrics['user_id']}")
        print(f"🔍 Mode: {metrics['search_mode']}")
        print(f"✅ Success: {metrics['slides_with_images']}/{metrics['content_slides']} content slides have images")
        print(f"📊 Utilization: {metrics['utilization_rate']} images used")