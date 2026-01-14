
#step6_outlinegen_text_and_image.py
import hashlib  # 🆕 ADD THIS LINE

import json
import chromadb
from chromadb.config import Settings
import numpy as np
from typing import List, Dict, Any, Tuple
import os
from openai import OpenAI
import time
import re
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity

# Import the updated multi-user vector store
from step5_four_vector_store_with_image_caption_and_text import QueryRetriever, MultiUserChromaDBManager
from image_path_resolver import ImagePathResolver


from dotenv import load_dotenv
load_dotenv()

class ProfessionalPresentationGenerator:
    def __init__(self, user_id: str, mode: str = "uploaded_only", openai_api_key=None, chroma_db_path="./chroma_db", session_id: str = None):
        if not user_id:
            raise ValueError("user_id is required for presentation generator")
            
        self.user_id = user_id
        self.mode = mode
        self.session_id = session_id  # 🆕 STORE SESSION ID
        self.client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.retriever = QueryRetriever(user_id=user_id, mode=mode, openai_api_key=openai_api_key)
        self.chroma_manager = MultiUserChromaDBManager(chroma_db_path)
        self.presentation_templates = self._load_presentation_templates()
        self.used_image_ids = set()
        
    def _load_presentation_templates(self) -> Dict:
        """Load professional presentation templates"""
        return {
            "corporate": {
                "style": "professional corporate",
                "description": "Professional business presentations for internal meetings and client reviews"
            },
            "technical": {
                "style": "technical detailed", 
                "description": "Detailed technical presentations for engineering teams and technical reviews"
            },
            "executive": {
                "style": "executive summary",
                "description": "High-level summaries for executives and decision makers"
            },
            "sales": {
                "style": "sales and marketing",
                "description": "Persuasive presentations for sales pitches and marketing campaigns"
            }
        }
    
    def _get_fixed_outline_structure(self, num_slides: int, presentation_style: str, query: str) -> Dict:
        """Return fixed outline structure with predefined keys - DYNAMIC based on query"""
        
        # Generate a unique title based on the actual query
        title_templates = {
            "technical": f"Technical Deep Dive: {query}",
            "corporate": f"Strategic Overview: {query}",
            "executive": f"Executive Summary: {query}",
            "sales": f"{query} - Value Proposition and Benefits"
        }
        
        presentation_title = title_templates.get(presentation_style, f"Professional Overview: {query}")
        
        return {
            "presentation_title": presentation_title,
            "total_slides": num_slides,
            "presentation_style": presentation_style,
            "target_audience": "Business professionals and stakeholders",
            "key_objectives": [
                f"Provide comprehensive overview of {query}",
                "Highlight key features and business value", 
                "Explain implementation and practical applications"
            ],
            "slides": [],
            "content_richness": "medium",
            "sources_used": []
        }
    
    def expand_query(self, query: str) -> List[str]:
        """Expand the query to capture comprehensive context"""
        expanded_queries = [
            query,
            f"comprehensive overview of {query}",
            f"detailed information about {query}",
            f"key features and benefits of {query}",
            f"technical aspects of {query}",
            f"business value of {query}",
            f"implementation of {query}",
            f"use cases for {query}",
            f"advantages of {query}",
            f"capabilities of {query}",
            f"how {query} works",
            f"applications of {query}",
            f"{query} architecture",
            f"{query} features",
            f"{query} benefits"
        ]
        return expanded_queries
    
    def retrieve_comprehensive_content(self, query: str, num_slides: int) -> List[Dict]:
        """Retrieve comprehensive relevant content using SEPARATE QUERIES"""
        expanded_queries = self.expand_query(query)
        
        all_combined_results = []
        
        for expanded_query in expanded_queries:
            try:
                # Generate query embedding
                query_embedding = self.retriever.embedding_model.get_embeddings([expanded_query])[0]
                
                if not query_embedding:
                    continue
                    
                # Use separate query method instead of merged collection
                if self.mode == "uploaded_plus_corpus":
                    # Query both collections separately and combine
                    separate_results = self.retriever.chroma_manager.query_collections_separately(
                        self.user_id, query_embedding, n_results=20
                    )
                    combined_results = separate_results['combined']
                    
                elif self.mode == "uploaded_only":
                    # Query only temp_uploads - 🆕 ADD EMBEDDINGS
                    temp_client = chromadb.PersistentClient(
                        path=self.retriever.chroma_manager.get_user_directories(self.user_id)['temp_uploads']
                    )
                    temp_collection = temp_client.get_collection("document_embeddings")
                    temp_results = temp_collection.query(
                        query_embeddings=[query_embedding],
                        n_results=20,
                        include=["embeddings", "metadatas", "documents", "distances"]  # 🆕 ADD "embeddings"
                    )
                    combined_results = self.retriever._process_search_results(temp_results, expanded_query, include_images=False)
                    
                elif self.mode == "corpus_only":
                    # Query only main_corpus - 🆕 ADD EMBEDDINGS
                    main_client = chromadb.PersistentClient(
                        path=self.retriever.chroma_manager.get_user_directories(self.user_id)['main_corpus']
                    )
                    main_collection = main_client.get_collection("document_embeddings")
                    main_results = main_collection.query(
                        query_embeddings=[query_embedding],
                        n_results=20,
                        include=["embeddings", "metadatas", "documents", "distances"]  # 🆕 ADD "embeddings"
                    )
                    combined_results = self.retriever._process_search_results(main_results, expanded_query, include_images=False)
                
                if combined_results and combined_results['text_results']:
                    all_combined_results.extend(combined_results['text_results'])
                    
            except Exception as e:
                print(f"Error searching for '{expanded_query}': {e}")
                continue

            seen_content = set()
            unique_results = []
            for result in all_combined_results:
                content_preview = result['content'][:150].lower()
                content_hash = hashlib.md5(content_preview.encode()).hexdigest()
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_results.append(result)

            # Sort by similarity score (highest first)
            unique_results.sort(key=lambda x: x['similarity_score'], reverse=True)

            # 🆕 SEPARATE TEXT AND IMAGE RESULTS FOR DEDUPLICATION
            text_results = [r for r in unique_results if r['metadata']['type'] == 'text_chunk']
            image_results = [r for r in unique_results if r['metadata']['type'] == 'image_caption']

            print(f"📊 Before deduplication: {len(text_results)} text, {len(image_results)} images")

            # 🆕 APPLY SEMANTIC DEDUPLICATION
            text_results, image_results = self._deduplicate_retrieved_content(text_results, image_results)

            print(f"📊 After deduplication: {len(text_results)} text, {len(image_results)} images")

            # Combine back for relevance threshold filtering
            unique_results = text_results + image_results
            
            # Use appropriate relevance threshold
            relevance_threshold = 0.4
            relevant_results = [
                result for result in unique_results 
                if result['similarity_score'] >= relevance_threshold
            ]
            
            print(f"Retrieved {len(relevant_results)} relevant text chunks (threshold: {relevance_threshold})")
            print(f"Search mode: {self.mode}, User: {self.user_id}")
            
            # Show user stats
            user_stats = self.retriever.chroma_manager.get_user_stats(self.user_id)
            print(f"User vector store stats: {user_stats['main_corpus_documents']} main corpus, {user_stats['temp_uploads_documents']} temp uploads")
            
            # Show relevance distribution
            if relevant_results:
                scores = [r['similarity_score'] for r in relevant_results]
                print(f"Relevance scores: {min(scores):.3f} - {max(scores):.3f} (avg: {sum(scores)/len(scores):.3f})")
            
            return relevant_results
        
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response from LLM"""
        response = response.strip()
        
        # Remove markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        # Remove any extra text before or after JSON
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx != -1 and end_idx != 0:
            response = response[start_idx:end_idx]
        
        return response.strip()
    
    def generate_comprehensive_outline(self, query: str, num_slides: int, presentation_style: str = "corporate") -> Dict[str, Any]:
        """Generate professional presentation outline with user context"""
        print(f"🎯 Generating presentation for user: {self.user_id}")
        print(f"🔍 Search mode: {self.mode}")
        
        relevant_content = self.retrieve_comprehensive_content(query, num_slides)
        
        if not relevant_content:
            error_msg = f"No relevant content found for user {self.user_id} in mode: {self.mode}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
        
        # Prepare context for slide generation
        context_chunks = []
        for i, content in enumerate(relevant_content):
            context_chunks.append(f"CHUNK {i+1} [Source: {content['metadata']['original_doc_id']}, Relevance: {content['similarity_score']:.3f}]:\n{content['content']}")
        
        full_context = "\n\n".join(context_chunks)
        
        template = self.presentation_templates.get(presentation_style, self.presentation_templates["corporate"])
        
        # Create fixed structure WITH query
        fixed_structure = self._get_fixed_outline_structure(num_slides, presentation_style, query)
        
        system_prompt = f"""You are a professional presentation creator. Create a COMPLETE, INDUSTRY-READY presentation outline.

PRESENTATION STYLE: {template['style']}
STYLE DESCRIPTION: {template['description']}

CRITICAL INSTRUCTIONS:
1. Create a compelling presentation about: "{query}"
2. Create exactly {num_slides} slides total
3. Slide 1 must be a title slide (slide_type: "title")
4. Slides 2-{num_slides} must be content slides (slide_type: "content") 
5. Each content slide must have 3-6 professional bullet points
6. Use the retrieved content to create specific, detailed bullet points
7. Focus on business value, features, and practical applications
8. Return valid JSON with these exact keys:
   - "presentation_title" (string)
   - "total_slides" (integer) 
   - "presentation_style" (string)
   - "slides" (array of objects with "slide_number", "slide_title", "slide_type", "key_points")

DO NOT return empty values. Fill in all fields with professional content based on the research material."""

        user_prompt = f"""Create a professional presentation about: "{query}"

NUMBER OF SLIDES: {num_slides}
PRESENTATION STYLE: {presentation_style}
TARGET AUDIENCE: Business professionals and executives

RESEARCH CONTENT:
{full_context}

Create specific, detailed content using the research material above. Focus on creating valuable business content that would be useful for decision-makers.

OUTPUT REQUIREMENTS:
- Return valid JSON format
- Include {num_slides} slides total
- Slide 1: Title slide with compelling presentation title
- Slides 2-{num_slides}: Content slides with 3-6 detailed bullet points each
- Use professional business language
- Base all content on the research material provided"""

        print("   🤖 Generating presentation outline with OpenAI...")
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            response_content = response.choices[0].message.content
            print(f"   📄 Raw response received: {len(response_content)} characters")
            
            # Clean and parse JSON response
            response_content = self._clean_json_response(response_content)
            outline = json.loads(response_content)
            
            print(f"   ✅ Outline parsed successfully")
            print(f"   📋 Outline keys: {list(outline.keys())}")
            
            # Add required metadata
            outline["user_id"] = self.user_id
            outline["search_mode"] = self.mode
            outline["generation_timestamp"] = datetime.now().isoformat()
            
            # Validate required fields
            required_fields = ["presentation_title", "total_slides", "slides"]
            missing_fields = [field for field in required_fields if field not in outline]
            
            if missing_fields:
                error_msg = f"Outline missing required fields: {missing_fields}"
                print(f"❌ {error_msg}")
                print(f"📋 Available fields: {list(outline.keys())}")
                return {"error": error_msg, "available_fields": list(outline.keys())}
            
            # Standardize the outline structure
            outline = self._standardize_outline_structure(outline)
            outline = self._add_retrieved_chunks_metadata(outline, relevant_content)
            
            # Validate content richness and character count
            outline = self._validate_content_richness(outline)
            outline = self._validate_character_count(outline)
            
            print(f"   🎯 Outline generated successfully: {outline['presentation_title']}")
            return outline
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"📄 Response content: {response_content[:500]}...")
            return {"error": error_msg, "raw_response": response_content[:500]}
            
        except Exception as e:
            error_msg = f"Error generating outline: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return {"error": error_msg}
    
    def _standardize_outline_structure(self, outline: Dict) -> Dict:
        """Ensure outline uses standardized key names"""
        if "error" in outline:
            return outline
        
        standardized_slides = []
        
        for slide in outline.get("slides", []):
            # Convert any key variations to standardized keys
            standardized_slide = {
                "slide_number": slide.get("slide_number", 0),
                "slide_title": slide.get("slide_title") or slide.get("title", ""),
                "slide_type": slide.get("slide_type", "content"),
                "key_points": slide.get("key_points") or slide.get("content", []) or slide.get("bullet_points", [])
            }
            
            # Ensure slide 1 is always title slide
            if standardized_slide["slide_number"] == 1:
                standardized_slide["slide_type"] = "title"
                standardized_slide["key_points"] = []
            
            standardized_slides.append(standardized_slide)
        
        outline["slides"] = standardized_slides
        return outline
    
    def _validate_character_count(self, outline: Dict) -> Dict:
        """Validate that each slide has appropriate character count (200-400)"""
        if "error" in outline:
            return outline
        
        character_metrics = {}
        total_chars = 0
        slides_within_range = 0
        
        for slide in outline.get("slides", []):
            if slide.get("slide_type") == "content" and slide.get("key_points"):
                # Calculate total characters for this slide
                slide_chars = 0
                slide_chars += len(slide.get("slide_title", ""))
                
                # Add characters from key points
                for point in slide.get("key_points", []):
                    slide_chars += len(point)
                
                character_metrics[slide["slide_number"]] = {
                    "total_characters": slide_chars,
                    "within_range": 200 <= slide_chars <= 400,
                    "status": "GOOD" if 200 <= slide_chars <= 400 else "ADJUST NEEDED",
                    "bullet_points": len(slide.get("key_points", []))
                }
                
                total_chars += slide_chars
                if 200 <= slide_chars <= 400:
                    slides_within_range += 1
        
        # Add character metrics to outline
        if character_metrics:
            outline["character_metrics"] = character_metrics
            bullet_counts = [metrics["bullet_points"] for metrics in character_metrics.values()]
            outline["character_summary"] = {
                "slides_within_range": slides_within_range,
                "total_content_slides": len(character_metrics),
                "compliance_ratio": f"{(slides_within_range / len(character_metrics)) * 100:.1f}%",
                "average_characters_per_slide": total_chars // len(character_metrics) if character_metrics else 0,
                "bullet_point_variation": f"{min(bullet_counts)}-{max(bullet_counts)} points per slide",
                "variation_quality": "GOOD" if len(set(bullet_counts)) > 1 else "LOW VARIATION"
            }
        
        return outline
    
    def _validate_content_richness(self, outline: Dict) -> Dict:
        """Validate if outline has rich content for professional presentation"""
        if "error" in outline:
            return outline
        
        total_key_points = 0
        content_slides = 0
        slides_with_rich_content = 0
        
        for slide in outline.get("slides", []):
            if slide.get("slide_type") == "content" and slide.get("key_points"):
                content_slides += 1
                key_points = slide.get("key_points", [])
                total_key_points += len(key_points)
                
                # Consider a slide rich if it has appropriate points for its content
                if len(key_points) >= 3:
                    slides_with_rich_content += 1
        
        # Calculate content richness metrics
        if content_slides > 0:
            avg_points_per_slide = total_key_points / content_slides
            richness_ratio = slides_with_rich_content / content_slides
        else:
            avg_points_per_slide = 0
            richness_ratio = 0
        
        outline["content_richness_metrics"] = {
            "total_content_slides": content_slides,
            "total_key_points": total_key_points,
            "average_points_per_slide": round(avg_points_per_slide, 2),
            "slides_with_rich_content": slides_with_rich_content,
            "richness_ratio": round(richness_ratio, 2)
        }
        
        # Determine overall richness (adjusted for 3-6 range)
        if richness_ratio >= 0.8 and avg_points_per_slide >= 4:
            outline["content_richness"] = "high"
        elif richness_ratio >= 0.6 and avg_points_per_slide >= 3:
            outline["content_richness"] = "medium"
        else:
            outline["content_richness"] = "low"
            print("⚠️  Warning: Outline may have insufficient content richness")
        
        return outline

    def _add_retrieved_chunks_metadata(self, outline: Dict, relevant_content: List[Dict]) -> Dict:
        """Add metadata about retrieved chunks"""
        if "error" in outline:
            return outline
            
        retrieved_chunks_metadata = []
        for content in relevant_content:
            retrieved_chunks_metadata.append({
                "chunk_id": content['id'],
                "source_document": content['metadata']['original_doc_id'],
                "similarity_score": content['similarity_score'],
                "content_preview": content['content'][:200] + "..." if len(content['content']) > 200 else content['content'],
                "content_length": len(content['content']),
                "chunk_type": content['metadata']['type']
            })
        
        outline["retrieved_chunks_metadata"] = retrieved_chunks_metadata
        outline["total_retrieved_chunks"] = len(retrieved_chunks_metadata)
        
        return outline

    def outline_to_presentation(self, outline: Dict) -> Dict:
        """Convert outline to presentation format using standardized keys"""
        if "error" in outline:
            return outline
        
        print(f"🔍 Converting outline with {len(outline.get('slides', []))} slides to presentation format")
        
        presentation = {
            "presentation_title": outline.get("presentation_title", "Professional Presentation"),
            "total_slides": outline.get("total_slides", 0),
            "presentation_style": outline.get("presentation_style", "corporate"),
            "content_richness": outline.get("content_richness", "medium"),
            "executive_summary": f"Comprehensive overview of {outline.get('presentation_title', 'the topic')}",
            "key_value_propositions": [],
            "strategic_insights": [],
            "actionable_recommendations": [],
            "slides": []
        }
        
        # Extract key value propositions from the content
        all_key_points = []
        for slide in outline.get("slides", []):
            if slide.get("slide_type") == "content" and slide.get("key_points"):
                all_key_points.extend(slide.get("key_points", []))
        
        # Add top key points as value propositions
        if all_key_points:
            presentation["key_value_propositions"] = all_key_points[:3]
            presentation["strategic_insights"] = all_key_points[3:6] if len(all_key_points) > 3 else []
            presentation["actionable_recommendations"] = all_key_points[6:9] if len(all_key_points) > 6 else []
        
        # Process each slide using standardized keys
        for slide in outline.get("slides", []):
            slide_number = slide.get("slide_number", 0)
            slide_title = slide.get("slide_title", f"Slide {slide_number}")
            slide_type = slide.get("slide_type", "content")
            key_points = slide.get("key_points", [])
            
            presentation_slide = {
                "slide_number": slide_number,
                "slide_title": slide_title,
                "slide_type": slide_type
            }
            
            if slide_type == "content" and key_points:
                # Convert key_points to bullet-point formatted content
                content = "\n".join([f"• {point}" for point in key_points])
                
                presentation_slide.update({
                    "content": content,
                    "speaker_notes": f"Discuss: {', '.join(key_points[:3])}",
                    "visual_elements": ["professional diagram", "data visualization", "supporting graphic"],
                    "key_takeaway": f"Main insight: {slide_title}"
                })
            elif slide_type == "title":
                presentation_slide["content"] = slide_title
            else:
                # Handle slides without content
                presentation_slide.update({
                    "content": "• Content to be developed",
                    "speaker_notes": "Additional information required",
                    "visual_elements": ["placeholder graphic"],
                    "key_takeaway": f"Key information about {slide_title}"
                })
            
            presentation["slides"].append(presentation_slide)
        
        # Add professional metadata
        presentation["generated_date"] = datetime.now().isoformat()
        presentation["version"] = "1.0"
        presentation["content_approach"] = "industry_ready"
        presentation["estimated_duration"] = f"{len(presentation['slides']) * 2} minutes"
        
        # Copy metadata from outline with safe access
        metadata_keys = ["content_metrics", "source_documents", "total_source_chunks", 
                        "content_organization", "character_metrics", "character_summary",
                        "content_richness_metrics", "retrieved_chunks_metadata"]
        for key in metadata_keys:
            if key in outline:
                presentation[key] = outline[key]
        
        print(f"✅ Successfully converted outline to presentation with {len(presentation['slides'])} slides")
        return presentation

    # IMAGE MAPPING METHODS
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
    
    # def extract_all_image_captions(self) -> List[Dict]:
    #     """Extract image captions WITH EMBEDDINGS from ChromaDB - FIXED VERSION"""
    #     print(f"Extracting image captions from ChromaDB for user {self.user_id}...")
        
    #     all_images = []
        
    #     try:
    #         # Get session ID from class instance
    #         current_session_id = self.session_id
            
    #         if not current_session_id:
    #             print("⚠️ WARNING: No session_id available for image filtering!")
            
    #         # Query collections based on mode
    #         if self.mode == "uploaded_plus_corpus":
    #             # Get images from both sources separately
    #             query_embedding = [0] * 1536  # Dummy embedding to get all images
                
    #             separate_results = self.retriever.chroma_manager.query_collections_separately(
    #                 self.user_id, query_embedding, n_results=100
    #             )
                
    #             # Process main corpus images WITH EMBEDDINGS
    #             for img in separate_results['main_corpus']['image_results']:
    #                 # 🆕 FIX: Proper embedding check for NumPy arrays
    #                 if img.get('embedding') is not None and len(img['embedding']) > 0:
    #                     img['source'] = 'main_corpus'
    #                     all_images.append(img)
                
    #             # Process temp uploads images WITH SESSION FILTERING + EMBEDDINGS
    #             for img in separate_results['temp_uploads']['image_results']:
    #                 image_path = img.get('metadata', {}).get('image_path', '')
    #                 # 🆕 FIX: Proper embedding check for NumPy arrays
    #                 has_embedding = img.get('embedding') is not None and len(img['embedding']) > 0
                    
    #                 if current_session_id:
    #                     if f"_{current_session_id}_" in image_path and has_embedding:
    #                         img['source'] = 'temp_uploads'
    #                         all_images.append(img)
    #                         print(f"  ✅ INCLUDED (current session): {os.path.basename(image_path)}")
    #                     else:
    #                         print(f"  🚫 FILTERED OUT (wrong session/no embedding): {os.path.basename(image_path)}")
    #                 else:
    #                     # No session_id available, include all temp images with embeddings
    #                     if has_embedding:
    #                         img['source'] = 'temp_uploads'
    #                         all_images.append(img)
                
    #         elif self.mode == "uploaded_only":
    #             # Only get images from temp_uploads with session filtering - WITH EMBEDDINGS
    #             temp_client = chromadb.PersistentClient(
    #                 path=self.retriever.chroma_manager.get_user_directories(self.user_id)['temp_uploads']
    #             )
    #             temp_collection = temp_client.get_collection("document_embeddings")
                
    #             # 🆕 CRITICAL FIX: INCLUDE EMBEDDINGS in the query
    #             temp_results = temp_collection.get(include=['embeddings', 'metadatas', 'documents'])
                
    #             for i, (embedding, metadata, document) in enumerate(zip(
    #                 temp_results['embeddings'], 
    #                 temp_results['metadatas'], 
    #                 temp_results['documents']
    #             )):
    #                 if metadata.get('type') == 'image_caption':
    #                     image_path = metadata.get('image_path', '')
    #                     # 🆕 FIX: Proper embedding check for NumPy arrays
    #                     has_embedding = embedding is not None and len(embedding) > 0
                        
    #                     if current_session_id:
    #                         if f"_{current_session_id}_" in image_path:
    #                             all_images.append({
    #                                 'image_id': temp_results['ids'][i],
    #                                 'caption': metadata.get('caption', document),
    #                                 'embedding': embedding,  # 🆕 ADD EMBEDDING
    #                                 'metadata': metadata,
    #                                 'document_text': document,
    #                                 'stored_relative_path': image_path,
    #                                 'source': 'temp_uploads'
    #                             })
    #                             print(f"  ✅ INCLUDED (current session): {os.path.basename(image_path)}")
    #                         else:
    #                             print(f"  🚫 FILTERED OUT (wrong session): {os.path.basename(image_path)}")
    #                     else:
    #                         # No session_id available, include all temp images
    #                         all_images.append({
    #                             'image_id': temp_results['ids'][i],
    #                             'caption': metadata.get('caption', document),
    #                             'embedding': embedding,  # 🆕 ADD EMBEDDING
    #                             'metadata': metadata,
    #                             'document_text': document,
    #                             'stored_relative_path': image_path,
    #                             'source': 'temp_uploads'
    #                         })
                            
    #         elif self.mode == "corpus_only":
    #             # Only get images from main_corpus - WITH EMBEDDINGS
    #             main_client = chromadb.PersistentClient(
    #                 path=self.retriever.chroma_manager.get_user_directories(self.user_id)['main_corpus']
    #             )
    #             main_collection = main_client.get_collection("document_embeddings")
                
    #             # 🆕 CRITICAL FIX: INCLUDE EMBEDDINGS in the query
    #             main_results = main_collection.get(include=['embeddings', 'metadatas', 'documents'])
                
    #             for i, (embedding, metadata, document) in enumerate(zip(
    #                 main_results['embeddings'], 
    #                 main_results['metadatas'], 
    #                 main_results['documents']
    #             )):
    #                 if metadata.get('type') == 'image_caption':
    #                     # 🆕 FIX: Proper embedding check for NumPy arrays
    #                     has_embedding = embedding is not None and len(embedding) > 0
                        
    #                     if has_embedding:
    #                         all_images.append({
    #                             'image_id': main_results['ids'][i],
    #                             'caption': metadata.get('caption', document),
    #                             'embedding': embedding,  # 🆕 ADD EMBEDDING
    #                             'metadata': metadata,
    #                             'document_text': document,
    #                             'stored_relative_path': metadata.get('image_path', ''),
    #                             'source': 'main_corpus'
    #                         })
    #                         print(f"  ✅ INCLUDED (corpus image): {os.path.basename(metadata.get('image_path', ''))}")
    #                     else:
    #                         print(f"  🚫 SKIPPING (no embedding): {os.path.basename(metadata.get('image_path', ''))}")
            
    #         print(f"🎯 Initial image captions found: {len(all_images)}")
            
    #         # Count how many have embeddings
    #         images_with_embeddings = sum(1 for img in all_images if img.get('embedding') is not None and len(img['embedding']) > 0)
    #         print(f"📊 Images WITH embeddings: {images_with_embeddings}/{len(all_images)}")
            
    #         # 🆕 ENHANCED SAFETY: Verify physical file existence
    #         verified_images = []
    #         for img in all_images:
    #             stored_path = img.get('stored_relative_path', '')
    #             if not stored_path:
    #                 continue
                    
    #             # Resolve to absolute path
    #             resolved_path = ImagePathResolver.resolve_to_absolute_path(stored_path, self.user_id)
                
    #             if os.path.exists(resolved_path):
    #                 img['resolved_absolute_path'] = resolved_path
    #                 img['is_accessible'] = True
    #                 verified_images.append(img)
    #                 print(f"  ✅ ACCESSIBLE: {os.path.basename(stored_path)}")
    #             else:
    #                 print(f"  🚫 SKIPPING (file missing): {os.path.basename(stored_path)}")
            
    #         print(f"📊 VERIFIED accessible images: {len(verified_images)}/{len(all_images)}")
            
    #         return verified_images
            
    #     except Exception as e:
    #         print(f"❌ Error extracting images for user {self.user_id}: {e}")
    #         import traceback
    #         traceback.print_exc()  # 🆕 ADD THIS FOR DETAILED ERROR TRACEBACK
    #         return []











    def extract_all_image_captions(self) -> List[Dict]:
        """Extract image captions WITH EMBEDDINGS from ChromaDB - FIXED VERSION"""
        print(f"Extracting image captions from ChromaDB for user {self.user_id}...")
        
        all_images = []
        
        try:
            # Get session ID from class instance
            current_session_id = self.session_id
            
            if not current_session_id:
                print("⚠️ WARNING: No session_id available for image filtering!")
            
            # Query collections based on mode
            if self.mode == "uploaded_plus_corpus":
                # 🆕 FIX: Query both collections SEPARATELY and COMBINE manually
                print("  🔄 Processing uploaded_plus_corpus mode - querying collections separately...")
                
                # Get images from main_corpus (no session filtering needed)
                try:
                    main_client = chromadb.PersistentClient(
                        path=self.retriever.chroma_manager.get_user_directories(self.user_id)['main_corpus']
                    )
                    main_collection = main_client.get_collection("document_embeddings")
                    main_results = main_collection.get(include=['embeddings', 'metadatas', 'documents'])
                    
                    main_images_count = 0
                    for i, (embedding, metadata, document) in enumerate(zip(
                        main_results['embeddings'], 
                        main_results['metadatas'], 
                        main_results['documents']
                    )):
                        if metadata.get('type') == 'image_caption':
                            has_embedding = embedding is not None and len(embedding) > 0
                            if has_embedding:
                                all_images.append({
                                    'image_id': main_results['ids'][i],
                                    'caption': metadata.get('caption', document),
                                    'embedding': embedding,
                                    'metadata': metadata,
                                    'document_text': document,
                                    'stored_relative_path': metadata.get('image_path', ''),
                                    'source': 'main_corpus'
                                })
                                main_images_count += 1
                    print(f"  ✅ Found {main_images_count} images in main corpus")
                except Exception as e:
                    print(f"  ⚠️ Error getting main corpus images: {e}")
                
                # Get images from temp_uploads with session filtering
                try:
                    temp_client = chromadb.PersistentClient(
                        path=self.retriever.chroma_manager.get_user_directories(self.user_id)['temp_uploads']
                    )
                    temp_collection = temp_client.get_collection("document_embeddings")
                    temp_results = temp_collection.get(include=['embeddings', 'metadatas', 'documents'])
                    
                    temp_images_count = 0
                    filtered_temp_count = 0
                    for i, (embedding, metadata, document) in enumerate(zip(
                        temp_results['embeddings'], 
                        temp_results['metadatas'], 
                        temp_results['documents']
                    )):
                        if metadata.get('type') == 'image_caption':
                            image_path = metadata.get('image_path', '')
                            has_embedding = embedding is not None and len(embedding) > 0
                            
                            if current_session_id:
                                if f"_{current_session_id}_" in image_path and has_embedding:
                                    all_images.append({
                                        'image_id': temp_results['ids'][i],
                                        'caption': metadata.get('caption', document),
                                        'embedding': embedding,
                                        'metadata': metadata,
                                        'document_text': document,
                                        'stored_relative_path': image_path,
                                        'source': 'temp_uploads'
                                    })
                                    temp_images_count += 1
                                    print(f"  ✅ INCLUDED (current session): {os.path.basename(image_path)}")
                                else:
                                    filtered_temp_count += 1
                                    print(f"  🚫 FILTERED OUT (wrong session): {os.path.basename(image_path)}")
                            else:
                                # No session_id available, include all temp images with embeddings
                                if has_embedding:
                                    all_images.append({
                                        'image_id': temp_results['ids'][i],
                                        'caption': metadata.get('caption', document),
                                        'embedding': embedding,
                                        'metadata': metadata,
                                        'document_text': document,
                                        'stored_relative_path': image_path,
                                        'source': 'temp_uploads'
                                    })
                                    temp_images_count += 1
                    print(f"  ✅ Found {temp_images_count} images in temp uploads ({filtered_temp_count} filtered out)")
                except Exception as e:
                    print(f"  ⚠️ Error getting temp uploads images: {e}")
                
                print(f"  📊 Total images for uploaded_plus_corpus: {len(all_images)}")
                    
            elif self.mode == "uploaded_only":
                # Only get images from temp_uploads with session filtering - WITH EMBEDDINGS
                temp_client = chromadb.PersistentClient(
                    path=self.retriever.chroma_manager.get_user_directories(self.user_id)['temp_uploads']
                )
                temp_collection = temp_client.get_collection("document_embeddings")
                
                # 🆕 CRITICAL FIX: INCLUDE EMBEDDINGS in the query
                temp_results = temp_collection.get(include=['embeddings', 'metadatas', 'documents'])
                
                for i, (embedding, metadata, document) in enumerate(zip(
                    temp_results['embeddings'], 
                    temp_results['metadatas'], 
                    temp_results['documents']
                )):
                    if metadata.get('type') == 'image_caption':
                        image_path = metadata.get('image_path', '')
                        # 🆕 FIX: Proper embedding check for NumPy arrays
                        has_embedding = embedding is not None and len(embedding) > 0
                        
                        if current_session_id:
                            if f"_{current_session_id}_" in image_path:
                                all_images.append({
                                    'image_id': temp_results['ids'][i],
                                    'caption': metadata.get('caption', document),
                                    'embedding': embedding,  # 🆕 ADD EMBEDDING
                                    'metadata': metadata,
                                    'document_text': document,
                                    'stored_relative_path': image_path,
                                    'source': 'temp_uploads'
                                })
                                print(f"  ✅ INCLUDED (current session): {os.path.basename(image_path)}")
                            else:
                                print(f"  🚫 FILTERED OUT (wrong session): {os.path.basename(image_path)}")
                        else:
                            # No session_id available, include all temp images
                            all_images.append({
                                'image_id': temp_results['ids'][i],
                                'caption': metadata.get('caption', document),
                                'embedding': embedding,  # 🆕 ADD EMBEDDING
                                'metadata': metadata,
                                'document_text': document,
                                'stored_relative_path': image_path,
                                'source': 'temp_uploads'
                            })
                            
            elif self.mode == "corpus_only":
                # Only get images from main_corpus - WITH EMBEDDINGS
                main_client = chromadb.PersistentClient(
                    path=self.retriever.chroma_manager.get_user_directories(self.user_id)['main_corpus']
                )
                main_collection = main_client.get_collection("document_embeddings")
                
                # 🆕 CRITICAL FIX: INCLUDE EMBEDDINGS in the query
                main_results = main_collection.get(include=['embeddings', 'metadatas', 'documents'])
                
                for i, (embedding, metadata, document) in enumerate(zip(
                    main_results['embeddings'], 
                    main_results['metadatas'], 
                    main_results['documents']
                )):
                    if metadata.get('type') == 'image_caption':
                        # 🆕 FIX: Proper embedding check for NumPy arrays
                        has_embedding = embedding is not None and len(embedding) > 0
                        
                        if has_embedding:
                            all_images.append({
                                'image_id': main_results['ids'][i],
                                'caption': metadata.get('caption', document),
                                'embedding': embedding,  # 🆕 ADD EMBEDDING
                                'metadata': metadata,
                                'document_text': document,
                                'stored_relative_path': metadata.get('image_path', ''),
                                'source': 'main_corpus'
                            })
                            print(f"  ✅ INCLUDED (corpus image): {os.path.basename(metadata.get('image_path', ''))}")
                        else:
                            print(f"  🚫 SKIPPING (no embedding): {os.path.basename(metadata.get('image_path', ''))}")
            
            print(f"🎯 Initial image captions found: {len(all_images)}")
            
            # Count how many have embeddings
            images_with_embeddings = sum(1 for img in all_images if img.get('embedding') is not None and len(img['embedding']) > 0)
            print(f"📊 Images WITH embeddings: {images_with_embeddings}/{len(all_images)}")
            
            # # 🆕 ENHANCED SAFETY: Verify physical file existence
            # verified_images = []
            # for img in all_images:
            #     stored_path = img.get('stored_relative_path', '')
            #     if not stored_path:
            #         continue
                    
            #     # Resolve to absolute path
            #     resolved_path = ImagePathResolver.resolve_to_absolute_path(stored_path, self.user_id)
                
            #     if os.path.exists(resolved_path):
            #         img['resolved_absolute_path'] = resolved_path
            #         img['is_accessible'] = True
            #         verified_images.append(img)
            #         print(f"  ✅ ACCESSIBLE: {os.path.basename(stored_path)}")
            #     else:
            #         print(f"  🚫 SKIPPING (file missing): {os.path.basename(stored_path)}")
            
            # print(f"📊 VERIFIED accessible images: {len(verified_images)}/{len(all_images)}")
            
            # return verified_images


            # 🆕 ENHANCED SAFETY: Verify physical file existence
            # 🆕 ENHANCED SAFETY: Verify physical file existence
            verified_images = []
            for img in all_images:
                stored_path = img.get('stored_relative_path', '')
                if not stored_path:
                    continue
                    
                # Resolve to absolute path
                resolved_path = ImagePathResolver.resolve_to_absolute_path(stored_path, self.user_id)
                
                if os.path.exists(resolved_path):
                    img['resolved_absolute_path'] = resolved_path
                    img['is_accessible'] = True
                    verified_images.append(img)
                    print(f"  ✅ ACCESSIBLE: {os.path.basename(stored_path)}")
                else:
                    print(f"  🚫 SKIPPING (file missing): {os.path.basename(stored_path)}")

            print(f"📊 VERIFIED accessible images: {len(verified_images)}/{len(all_images)}")

            # 🆕 FINAL FIX: APPLY DEDUPLICATION TO ALL MODES
            if verified_images:
                print(f"🎯 APPLYING DEDUPLICATION for mode: {self.mode}")
                
                # For ALL modes: Remove EXACT file duplicates
                verified_images = self._deduplicate_images_by_content(verified_images)
                
                # For modes that might have semantic duplicates: Also remove similar caption duplicates
                if self.mode in ["uploaded_plus_corpus", "corpus_only"] and len(verified_images) > 1:
                    try:
                        verified_images = self._deduplicate_images_before_mapping(verified_images)
                    except Exception as e:
                        print(f"  ⚠️ Caption deduplication failed, using content-only: {e}")
                
                print(f"🎯 FINAL unique images for {self.mode}: {len(verified_images)}")

            return verified_images

            
        except Exception as e:
            print(f"❌ Error extracting images for user {self.user_id}: {e}")
            import traceback
            traceback.print_exc()  # 🆕 ADD THIS FOR DETAILED ERROR TRACEBACK
            return []
        


        
    # def find_best_images_for_slide(self, slide_embedding: List[float], all_images: List[Dict], slide_title: str) -> List[Dict]:
    #     """Find best images for slide using STRICT relevance threshold with SOURCE BALANCING"""
    #     if not slide_embedding or not all_images:
    #         print(f"  ❌ No slide embedding or no images available")
    #         return []
    def find_best_images_for_slide(self, slide_embedding: List[float], all_images: List[Dict], slide_title: str) -> List[Dict]:
        """Find best images for slide using STRICT relevance threshold with SOURCE BALANCING"""
        if not slide_embedding or not all_images:
            return []
        print("******************************************************")
        print("******************************************************")

        print(f"  Comparing with {len(all_images)} available images...")
        
        # 🆕 DEBUG: Check for image reuse
        reused_count = 0
        for image in all_images:
            if image['image_id'] in self.used_image_ids:
                reused_count += 1
                print(f"    ⚠️ IMAGE REUSE DETECTED: {image['image_id'][:8]} - {image['caption'][:50]}...")
        
        if reused_count > 0:
            print(f"    🚫 BLOCKED {reused_count} already-used images")



        
        print(f"  Comparing with {len(all_images)} available images...")
        
        # 🆕 DEBUG: Check if images have embeddings
        images_with_embeddings = []
        images_without_embeddings = []
        
        for image in all_images:
            # 🆕 FIX: Proper embedding check for NumPy arrays
            has_embedding = image.get('embedding') is not None and len(image['embedding']) > 0
            if not has_embedding:
                images_without_embeddings.append(image)
            else:
                images_with_embeddings.append(image)
        
        print(f"  🔍 DEBUG: {len(images_with_embeddings)} images WITH embeddings, {len(images_without_embeddings)} WITHOUT embeddings")
        
        if not images_with_embeddings:
            print(f"  ❌ CRITICAL: No images have embeddings! This is the problem.")
            return []
        
        # ✅ SEPARATE IMAGES BY SOURCE
        uploaded_images = []
        corpus_images = []
        
        for image in images_with_embeddings:  # Only use images with embeddings
            if image['image_id'] in self.used_image_ids:
                continue
                
            # Check if image is from current session (uploaded) or corpus
            image_path = image.get('stored_relative_path', '') or image.get('metadata', {}).get('image_path', '')
            if f"temp_uploads" in image_path:
                uploaded_images.append(image)
            else:
                corpus_images.append(image)
        
        print(f"  📊 Source breakdown: {len(uploaded_images)} uploaded, {len(corpus_images)} corpus")
        
        # Calculate similarities for ALL images
        def score_images(images_list):
            scored = []
            for image in images_list:
                try:
                    similarity = cosine_similarity([slide_embedding], [image['embedding']])[0][0]
                    scored.append({
                        **image,
                        'similarity_score': float(similarity)
                    })
                    print(f"    📊 Image {image['image_id'][:8]}: similarity = {similarity:.3f}")
                except Exception as e:
                    print(f"    ❌ Error calculating similarity for {image['image_id'][:8]}: {e}")
                    continue
            return sorted(scored, key=lambda x: x['similarity_score'], reverse=True)
        
        # Score images from both sources
        scored_uploaded = score_images(uploaded_images)
        scored_corpus = score_images(corpus_images)
        
        # Show top matches from each source for debugging
        if scored_uploaded:
            print(f"  📤 Top UPLOADED match: {scored_uploaded[0]['similarity_score']:.3f} - {scored_uploaded[0]['caption'][:50]}...")
        if scored_corpus:
            print(f"  📚 Top CORPUS match: {scored_corpus[0]['similarity_score']:.3f} - {scored_corpus[0]['caption'][:50]}...")
        
        # ✅ STRICT THRESHOLD + SOURCE BALANCING
        suitable_images = []
        
        # First, try to get the BEST image from UPLOADS (priority to user's files)
        if scored_uploaded and scored_uploaded[0]['similarity_score'] >= 0.4:
            suitable_images.append(scored_uploaded[0])
            print(f"  ✅ Selected UPLOADED image (score: {scored_uploaded[0]['similarity_score']:.3f})")
        
        # If no suitable uploaded image, try corpus
        if not suitable_images and scored_corpus and scored_corpus[0]['similarity_score'] >= 0.4:
            suitable_images.append(scored_corpus[0])  # ✅ FIXED TYPO: was 'scorpus_images'
            print(f"  ✅ Selected CORPUS image (score: {scored_corpus[0]['similarity_score']:.3f})")
        
        # If we still have no images but have decent options, be slightly more lenient for uploaded
        if not suitable_images and scored_uploaded and scored_uploaded[0]['similarity_score'] >= 0.35:
            suitable_images.append(scored_uploaded[0])
            print(f"  ⚡ Lenient selection: UPLOADED image (score: {scored_uploaded[0]['similarity_score']:.3f})")
        
        print(f"  Selected {len(suitable_images)} images for this slide")
        return suitable_images
        
    def map_images_to_presentation(self, presentation: Dict) -> Dict:
        """Map image captions to presentation slides using STRICT relevance threshold"""
        
        enhanced_presentation = presentation.copy()
        
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
        print(f"🎯 STRICT RELEVANCE: Only images with similarity ≥ 0.4 will be mapped")
        
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
            
            # Find best images for this slide (STRICT threshold - no fallbacks)
            best_images = self.find_best_images_for_slide(slide_embedding, all_images, slide_title)
            
            # Assign images to slide ONLY if they meet relevance threshold
            # Assign images to slide ONLY if they meet relevance threshold
            assigned_images = []
            for img in best_images:
                assigned_images.append({
                    'image_id': img['image_id'],
                    'caption': img['caption'],
                    'similarity_score': img['similarity_score'],
                    'source_document': img['metadata'].get('original_doc_id', 'unknown'),  # ✅ FIXED
                    'image_path': img['metadata'].get('image_path', ''),
                    'user_id': img.get('user_id', self.user_id),  # ✅ SAFE ACCESS
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
                print(f"  ❌ No relevant images found for slide {slide_number} (threshold: 0.4)")
        
        # 🚫 REMOVED: Strategic distribution fallback
        # No forcing irrelevant images onto slides
        
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
            'similarity_threshold_used': 0.4,
            'utilization_rate': f"{len(self.used_image_ids)}/{len(all_images)}",
            'coverage_ratio': f"{total_slides_with_images}/{content_slides}",
            'mapping_strategy': 'STRICT_RELEVANCE_ONLY'
        }
        
        print(f"\n=== STRICT RELEVANCE MAPPING COMPLETE for user {self.user_id} ===")
        print(f"📈 Total slides: {total_slides}")
        print(f"📊 Content slides (excluding intro): {content_slides}")
        print(f"✅ Content slides with RELEVANT images: {total_slides_with_images}/{content_slides}")
        print(f"🖼️  Relevant images used: {len(self.used_image_ids)}/{len(all_images)}")
        print(f"🔗 Total mappings: {total_images_mapped}")
        print(f"🎯 Strict threshold: 0.4 similarity")
        
        # Quality assessment
        coverage_percentage = (total_slides_with_images / content_slides * 100) if content_slides > 0 else 0
        if coverage_percentage >= 70:
            print(f"📊 Coverage: EXCELLENT ({coverage_percentage:.1f}% of content slides)")
        elif coverage_percentage >= 40:
            print(f"📊 Coverage: GOOD ({coverage_percentage:.1f}% of content slides)")
        else:
            print(f"📊 Coverage: LIMITED ({coverage_percentage:.1f}% of content slides) - Consider adding more relevant images to your knowledge base")
        
        return enhanced_presentation

    def save_presentation_package(self, outline: Dict, presentation: Dict, base_filename: str = None):
        """Save complete presentation package"""
        if not base_filename:
            title_slug = presentation["presentation_title"].lower().replace(" ", "_")[:50]
            base_filename = f"presentation_{title_slug}_{self.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save outline
        outline_file = f"{base_filename}_outline.json"
        with open(outline_file, 'w', encoding='utf-8') as f:
            json.dump(outline, f, indent=2, ensure_ascii=False)
        
        # Save presentation with images
        presentation_file = f"{base_filename}_with_images.json"
        with open(presentation_file, 'w', encoding='utf-8') as f:
            json.dump(presentation, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Presentation package saved:")
        print(f"   - Outline: {outline_file}")
        print(f"   - Presentation with images: {presentation_file}")
        
        return {
            "outline_file": outline_file,
            "presentation_file": presentation_file
        }
    
    def print_professional_summary(self, presentation: Dict):
        """Print professional presentation summary"""
        if "error" in presentation:
            print(f"Error: {presentation['error']}")
            return
        
        content_richness = presentation.get("content_richness", "medium")
        content_metrics = presentation.get("content_metrics", {})
        
        print(f"\n{'='*80}")
        print(f"🎯 PROFESSIONAL PRESENTATION: {presentation['presentation_title']}")
        print(f"{'='*80}")
        print(f"📊 Style: {presentation.get('presentation_style', 'corporate')}")
        print(f"📈 Total Slides: {presentation['total_slides']}")
        print(f"⏱️  Estimated Duration: {presentation.get('estimated_duration', 'N/A')}")
        print(f"⭐ Content Richness: {content_richness.upper()}")
        
        # Show image mapping metrics if available
        if "image_mapping_metrics" in presentation:
            metrics = presentation["image_mapping_metrics"]
            print(f"🖼️  Images Mapped: {metrics['slides_with_images']}/{metrics['content_slides']} content slides")
            print(f"📊 Image Utilization: {metrics['utilization_rate']}")
        
        if content_metrics:
            print(f"📊 Average Points/Slide: {content_metrics.get('average_points_per_slide', 'N/A')}")
            print(f"🔗 Rich Content Slides: {content_metrics.get('slides_with_rich_content', 'N/A')}/{content_metrics.get('total_content_slides', 'N/A')}")
        
        if 'executive_summary' in presentation:
            print(f"\n📋 EXECUTIVE SUMMARY:")
            print(f"   {presentation['executive_summary']}")
        
        if 'key_value_propositions' in presentation:
            print(f"\n💎 KEY VALUE PROPOSITIONS:")
            for prop in presentation['key_value_propositions'][:3]:
                print(f"   • {prop}")
        
        print(f"\n📑 SLIDE OVERVIEW (Professional Content with Images):")
        for slide in presentation['slides']:
            if slide.get("slide_type") == "content":
                bullet_count = len([line for line in slide.get('content', '').split('\n') if line.strip().startswith('•')])
                image_count = len(slide.get('images', []))
                
                print(f"\n   Slide {slide['slide_number']}: {slide['slide_title']}")
                print(f"     📊 Content: {bullet_count} professional points")
                print(f"     🖼️  Images: {image_count} relevant images")
                
                # Show first image caption if available
                if slide.get('images'):
                    print(f"     📷 Top image: {slide['images'][0]['caption'][:80]}...")
                
                # Show first 2 bullet points to demonstrate quality
                content_lines = [line for line in slide.get('content', '').split('\n') if line.strip().startswith('•')]
                for line in content_lines[:2]:
                    if line.strip():
                        print(f"     {line}")
    def _deduplicate_retrieved_content(self, text_results: List[Dict], image_results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Remove duplicate text chunks and image captions keeping first occurrence"""
        
        def _deduplicate_by_similarity(items, similarity_threshold=0.95, content_key='content'):
            """Remove duplicates keeping first occurrence (highest ranked)"""
            if not items:
                return items
                
            unique_items = []
            seen_embeddings = []
            
            print(f"  🔍 Deduplicating {len(items)} items (threshold: {similarity_threshold})...")
            
            for item in items:
                is_duplicate = False
                current_embedding = item['embedding']
                
                # Compare with all previously kept items
                for seen_embedding in seen_embeddings:
                    similarity = cosine_similarity([current_embedding], [seen_embedding])[0][0]
                    if similarity > similarity_threshold:
                        is_duplicate = True
                        print(f"    🚫 REMOVED duplicate: {item[content_key][:80]}... (similarity: {similarity:.3f})")
                        break
                
                if not is_duplicate:
                    unique_items.append(item)
                    seen_embeddings.append(current_embedding)
            
            print(f"    ✅ Kept {len(unique_items)} unique items")
            return unique_items
        
        # Deduplicate text chunks
        unique_texts = _deduplicate_by_similarity(
            text_results, 
            similarity_threshold=0.95,
            content_key='content'
        )
        
        # Deduplicate image captions
        unique_images = _deduplicate_by_similarity(
            image_results,
            similarity_threshold=0.90,
            content_key='caption'
        )
        
        return unique_texts, unique_images

    def _deduplicate_images_before_mapping(self, all_images: List[Dict]) -> List[Dict]:
        """Remove duplicate images using caption embedding similarity - FIXED VERSION"""
        if not all_images:
            return all_images
            
        print(f"🖼️  CAPTION-BASED deduplication for {len(all_images)} images...")
        
        unique_images = []
        seen_embeddings = []
        removed_count = 0
        
        for image in all_images:
            # 🆕 FIX: Proper embedding check for NumPy arrays
            has_embedding = (image.get('embedding') is not None and 
                            len(image['embedding']) > 0)
            
            if not has_embedding:
                # Skip images without embeddings
                unique_images.append(image)
                continue
                
            is_duplicate = False
            current_embedding = image['embedding']
            
            # Compare with all previously kept images
            for seen_embedding in seen_embeddings:
                similarity = cosine_similarity([current_embedding], [seen_embedding])[0][0]
                if similarity > 0.90:  # Same threshold as before
                    is_duplicate = True
                    removed_count += 1
                    print(f"  🚫 REMOVED caption duplicate: {image.get('caption', '')[:80]}... (similarity: {similarity:.3f})")
                    break
            
            if not is_duplicate:
                unique_images.append(image)
                seen_embeddings.append(current_embedding)
        
        print(f"  📊 CAPTION DEDUP: Kept {len(unique_images)} unique, removed {removed_count} duplicates")
        return unique_images

    def _deduplicate_images_by_content(self, all_images: List[Dict]) -> List[Dict]:
        """Remove duplicate images by comparing actual image file content - FINAL FIX"""
        if not all_images:
            return all_images
            
        print(f"🖼️  CONTENT-BASED deduplication for {len(all_images)} images...")
        
        unique_images = []
        seen_hashes = set()
        removed_count = 0
        
        for image in all_images:
            # Get the actual image file path
            image_path = image.get('resolved_absolute_path', '')
            if not image_path:
                # Fallback to relative path
                image_path = ImagePathResolver.resolve_to_absolute_path(
                    image.get('stored_relative_path', ''), 
                    self.user_id
                )
            
            if not image_path or not os.path.exists(image_path):
                # Skip if we can't access the file
                unique_images.append(image)
                continue
                
            try:
                # Generate content hash of the actual image file
                with open(image_path, 'rb') as f:
                    file_content = f.read()
                    file_hash = hashlib.md5(file_content).hexdigest()
                
                if file_hash not in seen_hashes:
                    seen_hashes.add(file_hash)
                    unique_images.append(image)
                    print(f"  ✅ KEPT unique: {os.path.basename(image_path)}")
                else:
                    removed_count += 1
                    print(f"  🚫 REMOVED content duplicate: {os.path.basename(image_path)}")
                    
            except Exception as e:
                print(f"  ⚠️ Could not hash image {image_path}: {e}")
                unique_images.append(image)
        
        print(f"  📊 CONTENT DEDUP: Kept {len(unique_images)} unique, removed {removed_count} duplicates")
        return unique_images

    def _deduplicate_images_before_mapping(self, all_images: List[Dict]) -> List[Dict]:
        """Remove duplicate images using caption embedding similarity"""
        if not all_images:
            return all_images
            
        print(f"🖼️  CAPTION-BASED deduplication for {len(all_images)} images...")
        
        unique_images = []
        seen_embeddings = []
        removed_count = 0
        
        for image in all_images:
            if 'embedding' not in image or not image['embedding']:
                # Skip images without embeddings
                unique_images.append(image)
                continue
                
            is_duplicate = False
            current_embedding = image['embedding']
            
            # Compare with all previously kept images
            for seen_embedding in seen_embeddings:
                similarity = cosine_similarity([current_embedding], [seen_embedding])[0][0]
                if similarity > 0.90:  # Same threshold as before
                    is_duplicate = True
                    removed_count += 1
                    print(f"  🚫 REMOVED caption duplicate: {image.get('caption', '')[:80]}... (similarity: {similarity:.3f})")
                    break
            
            if not is_duplicate:
                unique_images.append(image)
                seen_embeddings.append(current_embedding)
        
        print(f"  📊 CAPTION DEDUP: Kept {len(unique_images)} unique, removed {removed_count} duplicates")
        return unique_images



# INTEGRATED PIPELINE FUNCTION
def create_complete_presentation_pipeline(
    query: str, 
    user_id: str,
    is_file_uploaded_by_user: bool = False,
    mode: str = "corpus_only",
    num_slides: int = 8, 
    presentation_style: str = "corporate",
    openai_api_key: str = None,
    save_package: bool = True,
    merge_after_success: bool = True,
    session_id: str = None
) -> Dict[str, Any]:
    
    print("🚀 STARTING COMPLETE PRESENTATION PIPELINE")
    print("=" * 60)
    print(f"👤 User: {user_id}")
    print(f"🔍 Session ID: {session_id}")  # 🆕 DEBUG
    print(f"📁 User uploaded files: {'YES' if is_file_uploaded_by_user else 'NO'}")
    print(f"🔍 Mode: {mode}")
    
    # Validate mode based on file upload status
    if not is_file_uploaded_by_user and mode != "corpus_only":
        error_msg = f"❌ Cannot use mode '{mode}'. No files uploaded by user. Please use 'corpus_only' mode."
        print(error_msg)
        return {"error": error_msg}
    
    # Initialize generator with user context
    generator = ProfessionalPresentationGenerator(
        user_id=user_id, 
        mode=mode, 
        openai_api_key=openai_api_key,
        session_id=session_id
    )
    
    # 🆕 DEBUG: Verify session ID reached the generator
    print(f"🔍 DEBUG: Generator session_id = {generator.session_id}")
    
    # STEP 1: Generate presentation outline
    print(f"\n📝 STEP 1: GENERATING PROFESSIONAL PRESENTATION for '{query}'")
    outline = generator.generate_comprehensive_outline(query, num_slides, presentation_style)
    
    if "error" in outline:
        print(f"❌ Presentation generation failed: {outline['error']}")
        return {"error": outline["error"]}
    
    print(f"   ✅ Professional presentation generated: {outline['presentation_title']}")
    
    # STEP 2: Convert outline to presentation format
    print(f"\n🔄 STEP 2: CONVERTING TO PRESENTATION FORMAT")
    presentation = generator.outline_to_presentation(outline)
    
    if "error" in presentation:
        print(f"❌ Presentation conversion failed: {presentation['error']}")
        return {"error": presentation["error"]}
    
    # STEP 3: Map images to presentation
    print(f"\n🖼️  STEP 3: MAPPING IMAGES TO PRESENTATION")
    presentation_with_images = generator.map_images_to_presentation(presentation)
    
    # STEP 4: Save package
    files = None
    if save_package:
        print(f"\n💾 STEP 4: SAVING PRESENTATION PACKAGE")
        try:
            files = generator.save_presentation_package(outline, presentation_with_images)
            print(f"   ✅ Package saved successfully")
        except Exception as e:
            print(f"   ❌ Failed to save package: {e}")
    
    # STEP 5: Merge temp to main corpus if requested and successful
    if merge_after_success and "error" not in outline:
        print(f"\n🔄 STEP 5: MERGING TEMP UPLOADS TO MAIN CORPUS")
        try:
            from step5_four_vector_store_with_image_caption_and_text import merge_user_data
            merged_count = merge_user_data(user_id)
            if merged_count > 0:
                print(f"✅ Successfully merged {merged_count} documents to main corpus")
            else:
                print("⚠️  No documents to merge")
        except Exception as e:
            print(f"⚠️  Failed to merge documents: {e}")
    
    # Display summary
    print(f"\n📋 FINAL PRESENTATION SUMMARY")
    generator.print_professional_summary(presentation_with_images)
    
    return {
        "outline": outline,
        "presentation": presentation_with_images,  # This includes images
        "files": files if save_package else None,
        "user_id": user_id,
        "search_mode": mode
    }


# Usage example
if __name__ == "__main__":
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not OPENAI_API_KEY:
        print("❌ Please set OPENAI_API_KEY environment variable")
        exit(1)
    
    # Run complete pipeline
    result = create_complete_presentation_pipeline(
        query="Introduction to Aksha AI Surveillance System",
        user_id="user_123",
        is_file_uploaded_by_user=False,
        mode="corpus_only",
        num_slides=8,
        presentation_style="technical",
        openai_api_key=OPENAI_API_KEY,
        save_package=True,
        merge_after_success=True
    )
