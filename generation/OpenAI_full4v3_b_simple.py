# import json
# import chromadb
# from chromadb.config import Settings
# import numpy as np
# from typing import List, Dict, Any, Tuple
# import os
# from openai import OpenAI
# import time
# import re
# from datetime import datetime

# # Import the updated multi-user vector store
# from step5_four_vector_store_with_image_caption_and_text import QueryRetriever, MultiUserChromaDBManager

# class ProfessionalPresentationGenerator:
#     def __init__(self, user_id: str, mode: str = "uploaded_only", openai_api_key=None, chroma_db_path="./chroma_db"):
#         if not user_id:
#             raise ValueError("user_id is required for presentation generator")
            
#         self.user_id = user_id
#         self.mode = mode
#         self.client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
#         self.retriever = QueryRetriever(user_id=user_id, mode=mode, openai_api_key=openai_api_key)
#         self.chroma_manager = MultiUserChromaDBManager(chroma_db_path)
#         self.presentation_templates = self._load_presentation_templates()
        
#     def _load_presentation_templates(self) -> Dict:
#         """Load professional presentation templates"""
#         return {
#             "corporate": {
#                 "style": "professional corporate",
#                 "description": "Professional business presentations for internal meetings and client reviews"
#             },
#             "technical": {
#                 "style": "technical detailed", 
#                 "description": "Detailed technical presentations for engineering teams and technical reviews"
#             },
#             "executive": {
#                 "style": "executive summary",
#                 "description": "High-level summaries for executives and decision makers"
#             },
#             "sales": {
#                 "style": "sales and marketing",
#                 "description": "Persuasive presentations for sales pitches and marketing campaigns"
#             }
#         }
    
#     def _get_fixed_outline_structure(self, num_slides: int, presentation_style: str) -> Dict:
#         """Return fixed outline structure with predefined keys"""
#         return {
#             "presentation_title": query,
#             "total_slides": num_slides,
#             "presentation_style": presentation_style,
#             "target_audience": "",
#             "key_objectives": [],
#             "slides": [],
#             "content_richness": "medium",
#             "sources_used": [],
#             "user_id": self.user_id,
#             "search_mode": self.mode
#         }
    
#     def expand_query(self, query: str) -> List[str]:
#         """Expand the query to capture comprehensive context"""
#         expanded_queries = [
#             query,
#             f"comprehensive overview of {query}",
#             f"detailed information about {query}",
#             f"key features and benefits of {query}",
#         ]
#         return expanded_queries
    
#     def retrieve_comprehensive_content(self, query: str, num_slides: int) -> List[Dict]:
#         """Retrieve comprehensive relevant content from vector DB"""
#         expanded_queries = self.expand_query(query)
        
#         all_results = []
#         for expanded_query in expanded_queries:
#             try:
#                 # Get more results for comprehensive coverage
#                 results = self.retriever.search(
#                     query=expanded_query, 
#                     n_results=20,
#                     include_images=False
#                 )
#                 if results and results['text_results']:
#                     all_results.extend(results['text_results'])
#             except Exception as e:
#                 print(f"Error searching for '{expanded_query}': {e}")
#                 continue
        
#         # Remove duplicates while preserving order
#         seen_content = set()
#         unique_results = []
#         for result in all_results:
#             content_preview = result['content'][:150].lower()
#             content_hash = hash(content_preview)
#             if content_hash not in seen_content:
#                 seen_content.add(content_hash)
#                 unique_results.append(result)
        
#         # Sort by similarity score but be more inclusive
#         unique_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
#         # Use a more lenient relevance threshold to get more content
#         relevance_threshold = 0.4
#         relevant_results = [
#             result for result in unique_results 
#             if result['similarity_score'] >= relevance_threshold
#         ]
        
#         # If we still don't have enough content, include even more
#         if len(relevant_results) < num_slides * 3:
#             relevance_threshold = 0.3
#             relevant_results = [
#                 result for result in unique_results 
#                 if result['similarity_score'] >= relevance_threshold
#             ]
        
#         print(f"Retrieved {len(relevant_results)} relevant text chunks (threshold: {relevance_threshold})")
#         print(f"Search mode: {self.mode}, User: {self.user_id}")
        
#         # Show user stats
#         user_stats = self.chroma_manager.get_user_stats(self.user_id)
#         print(f"User vector store stats: {user_stats['main_corpus_documents']} main corpus, {user_stats['temp_uploads_documents']} temp uploads")
        
#         # Show relevance distribution
#         if relevant_results:
#             scores = [r['similarity_score'] for r in relevant_results]
#             print(f"Relevance scores: {min(scores):.3f} - {max(scores):.3f} (avg: {sum(scores)/len(scores):.3f})")
        
#         return relevant_results
    
#     # ... [rest of the methods remain the same as previous version, just ensure user_id is required]
    
#     def generate_comprehensive_outline(self, query: str, num_slides: int, presentation_style: str = "corporate") -> Dict[str, Any]:
#         """Generate professional presentation outline with user context"""
#         print(f"🎯 Generating presentation for user: {self.user_id}")
#         print(f"🔍 Search mode: {self.mode}")
        
#         relevant_content = self.retrieve_comprehensive_content(query, num_slides)
        
#         if not relevant_content:
#             return {"error": f"No relevant content found for user {self.user_id} in mode: {self.mode}"}
        
#         # ... [rest of the method implementation remains the same]
        
#         outline = {
#             # ... existing outline structure
#             "user_id": self.user_id,
#             "search_mode": self.mode,
#             "generation_timestamp": datetime.now().isoformat()
#         }
        
#         return outline

#     # ... [All other methods remain the same]

# # def create_content_rich_presentation_pipeline(
# #     query: str, 
# #     user_id: str,  # Required parameter
# #     mode: str = "uploaded_only",
# #     num_slides: int = 8, 
# #     presentation_style: str = "corporate",
# #     openai_api_key: str = None,
# #     save_package: bool = True,
# #     merge_after_success: bool = True
# # ) -> Dict[str, Any]:
# #     """Complete pipeline for content-rich professional presentation generation with user isolation"""
    
# #     if not user_id:
# #         raise ValueError("user_id is required for presentation pipeline")
    
# #     print("🚀 STARTING PROFESSIONAL PRESENTATION PIPELINE")
# #     print("=" * 60)
# #     print(f"👤 User: {user_id}")
# #     print(f"🔍 Mode: {mode}")
# #     print(f"🎯 Style: {presentation_style}")
# #     print(f"📊 Slides: {num_slides}")
    
# #     # Initialize generator with user context
# #     generator = ProfessionalPresentationGenerator(
# #         user_id=user_id, 
# #         mode=mode, 
# #         openai_api_key=openai_api_key
# #     )
    
# #     # Generate presentation
# #     print(f"\n📝 GENERATING PROFESSIONAL PRESENTATION for '{query}'")
# #     outline = generator.generate_comprehensive_outline(query, num_slides, presentation_style)
    
# #     if "error" in outline:
# #         print(f"❌ Presentation generation failed: {outline['error']}")
# #         return {"error": outline["error"]}
    
# #     print(f"   ✅ Professional presentation generated: {outline['presentation_title']}")
    
# #     # Convert outline to presentation format
# #     print(f"\n🔄 CONVERTING TO PRESENTATION FORMAT")
# #     presentation = generator.outline_to_presentation(outline)
    
# #     # Generate PPT structure
# #     print(f"\n🏗️  GENERATING POWERPOINT STRUCTURE")
# #     ppt_structure = generator.generate_ppt_structure(presentation)
    
# #     # Save package
# #     if save_package:
# #         print(f"\n💾 SAVING PRESENTATION PACKAGE")
# #         files = generator.save_presentation_package(outline, presentation, ppt_structure)
    
# #     # Merge temp to main corpus if requested and successful
# #     if merge_after_success and "error" not in outline:
# #         print(f"\n🔄 MERGING TEMP UPLOADS TO MAIN CORPUS")
# #         from step5_four_vector_store_with_image_caption_and_text import merge_user_data
# #         merged_count = merge_user_data(user_id)
# #         if merged_count > 0:
# #             print(f"✅ Successfully merged {merged_count} documents to main corpus")
# #         else:
# #             print("⚠️  No documents to merge")
    
# #     # Display summary
# #     print(f"\n📋 PRESENTATION SUMMARY")
# #     generator.print_professional_summary(presentation)
    
# #     return {
# #         "outline": outline,
# #         "presentation": presentation,
# #         "ppt_structure": ppt_structure,
# #         "files": files if save_package else None,
# #         "user_id": user_id,
# #         "search_mode": mode
# #     }



# def create_content_rich_presentation_pipeline(
#     query: str, 
#     user_id: str = "default",
#     mode: str = "uploaded_only",
#     num_slides: int = 8, 
#     presentation_style: str = "corporate",
#     openai_api_key: str = None,
#     save_package: bool = True,
#     merge_after_success: bool = True
# ) -> Dict[str, Any]:
#     """Complete pipeline for content-rich professional presentation generation with user isolation"""
    
#     print("🚀 STARTING PROFESSIONAL PRESENTATION PIPELINE")
#     print("=" * 60)
#     print(f"👤 User: {user_id}")
#     print(f"🔍 Mode: {mode}")
#     print(f"🎯 Style: {presentation_style}")
#     print(f"📊 Slides: {num_slides}")
    
#     # Initialize generator with user context
#     generator = ProfessionalPresentationGenerator(
#         user_id=user_id, 
#         mode=mode, 
#         openai_api_key=openai_api_key
#     )
    
#     # Generate presentation
#     print(f"\n📝 GENERATING PROFESSIONAL PRESENTATION for '{query}'")
#     outline = generator.generate_comprehensive_outline(query, num_slides, presentation_style)
    
#     # Check if outline generation failed
#     if "error" in outline:
#         print(f"❌ Presentation generation failed: {outline['error']}")
#         return {"error": outline["error"]}
    
#     # Check if presentation_title exists before accessing it
#     if 'presentation_title' not in outline:
#         print(f"❌ Outline generation failed - missing presentation title")
#         print(f"📋 Outline structure: {list(outline.keys())}")
#         return {"error": "Outline generation failed - missing required fields"}
    
#     print(f"   ✅ Professional presentation generated: {outline['presentation_title']}")
    
#     # Convert outline to presentation format
#     print(f"\n🔄 CONVERTING TO PRESENTATION FORMAT")
#     presentation = generator.outline_to_presentation(outline)
    
#     # Check if presentation conversion failed
#     if "error" in presentation:
#         print(f"❌ Presentation conversion failed: {presentation['error']}")
#         return {"error": presentation["error"]}
    
#     # Generate PPT structure
#     print(f"\n🏗️  GENERATING POWERPOINT STRUCTURE")
#     ppt_structure = generator.generate_ppt_structure(presentation)
    
#     # Save package
#     files = None
#     if save_package:
#         print(f"\n💾 SAVING PRESENTATION PACKAGE")
#         try:
#             files = generator.save_presentation_package(outline, presentation, ppt_structure)
#             print(f"   ✅ Package saved successfully")
#         except Exception as e:
#             print(f"   ❌ Failed to save package: {e}")
    
#     # Merge temp to main corpus if requested and successful
#     if merge_after_success and "error" not in outline:
#         print(f"\n🔄 MERGING TEMP UPLOADS TO MAIN CORPUS")
#         try:
#             from step5_four_vector_store_with_image_caption_and_text import merge_user_data
#             merged_count = merge_user_data(user_id)
#             if merged_count > 0:
#                 print(f"✅ Successfully merged {merged_count} documents to main corpus")
#             else:
#                 print("⚠️  No documents to merge")
#         except Exception as e:
#             print(f"⚠️  Failed to merge documents: {e}")
    
#     # Display summary
#     print(f"\n📋 PRESENTATION SUMMARY")
#     generator.print_professional_summary(presentation)
    
#     return {
#         "outline": outline,
#         "presentation": presentation,
#         "ppt_structure": ppt_structure,
#         "files": files if save_package else None,
#         "user_id": user_id,
#         "search_mode": mode
#     }

# # Updated main interactive function
# def main_interactive():
#     """Interactive professional presentation generator with user context"""
#     OPENAI_API_KEY = "your-api-key-here"
    
#     print("🎯 PROFESSIONAL PRESENTATION GENERATOR")
#     print("=" * 50)
#     print("⭐ Multi-user architecture with isolated vector stores")
    
#     # Get user context - REQUIRED
#     user_id = input("Enter user ID: ").strip()
#     if not user_id:
#         print("❌ User ID is required!")
#         return
    
#     styles = {
#         "1": "corporate",
#         "2": "technical", 
#         "3": "executive",
#         "4": "sales"
#     }
    
#     modes = {
#         "1": "uploaded_only",
#         "2": "uploaded_plus_corpus", 
#         "3": "corpus_only"
#     }
    
#     while True:
#         try:
#             print("\n" + "="*50)
#             query = input("\nEnter presentation topic (or 'quit' to exit): ").strip()
#             if query.lower() in ['quit', 'exit', 'q']:
#                 break
            
#             if not query:
#                 continue
            
#             # Get number of slides
#             num_slides_input = input("Enter number of slides (default 8): ").strip()
#             num_slides = int(num_slides_input) if num_slides_input else 8
            
#             # Get presentation style
#             print("\nAvailable presentation styles:")
#             print("1. Corporate - Professional business presentations")
#             print("2. Technical - Detailed technical deep-dives") 
#             print("3. Executive - High-level strategic summaries")
#             print("4. Sales - Persuasive marketing presentations")
            
#             style_choice = input("Choose style (1-4, default 1): ").strip()
#             presentation_style = styles.get(style_choice, "corporate")
            
#             # Get search mode
#             print("\nAvailable search modes:")
#             print("1. uploaded_only - Only current uploads")
#             print("2. uploaded_plus_corpus - Current uploads + corpus")
#             print("3. corpus_only - Only corpus (no current uploads)")
            
#             mode_choice = input("Choose mode (1/2/3, default 1): ").strip()
#             mode = modes.get(mode_choice, "uploaded_only")
            
#             # Ask about merging
#             merge_choice = input("Merge temp uploads to corpus after generation? (y/n, default y): ").strip().lower()
#             merge_after_success = merge_choice != 'n'
            
#             print(f"\n🎯 Generating {num_slides}-slide {presentation_style} presentation")
#             print(f"👤 User: {user_id}")
#             print(f"🔍 Mode: {mode}")
#             print(f"⭐ Query: {query}")
            
#             # Run complete pipeline
#             result = create_content_rich_presentation_pipeline(
#                 query=query,
#                 user_id=user_id,
#                 mode=mode,
#                 num_slides=num_slides,
#                 presentation_style=presentation_style,
#                 openai_api_key=OPENAI_API_KEY,
#                 save_package=True,
#                 merge_after_success=merge_after_success
#             )
            
#             if "error" in result:
#                 print(f"\n❌ Pipeline failed: {result['error']}")
#             else:
#                 print(f"\n✅ Professional presentation pipeline completed successfully!")
                
#         except ValueError:
#             print("Please enter a valid number for slides.")
#         except KeyboardInterrupt:
#             print("\nExiting...")
#             break
#         except Exception as e:
#             print(f"Unexpected error: {e}")

# if __name__ == "__main__":
#     # Set your OpenAI API key
#     OPENAI_API_KEY = "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"
    
#     # Option 1: Run interactive mode
#     # main_interactive()
    
#     # Option 2: Run direct pipeline
#     result = create_content_rich_presentation_pipeline(
#         query="Introduction to Aksha AI Surveillance System",
#         user_id="user_123",  # Required - no default
#         mode="corpus_only",
#         num_slides=8,
#         presentation_style="technical",
#         openai_api_key=OPENAI_API_KEY,
#         save_package=True,
#         merge_after_success=True
#     )




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

# Import the updated multi-user vector store
from step5_four_vector_store_with_image_caption_and_text import QueryRetriever, MultiUserChromaDBManager

class ProfessionalPresentationGenerator:
    def __init__(self, user_id: str, mode: str = "uploaded_only", openai_api_key=None, chroma_db_path="./chroma_db"):
        if not user_id:
            raise ValueError("user_id is required for presentation generator")
            
        self.user_id = user_id
        self.mode = mode
        self.client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.retriever = QueryRetriever(user_id=user_id, mode=mode, openai_api_key=openai_api_key)
        self.chroma_manager = MultiUserChromaDBManager(chroma_db_path)
        self.presentation_templates = self._load_presentation_templates()
        
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
        """Retrieve comprehensive relevant content from vector DB"""
        expanded_queries = self.expand_query(query)
        
        all_results = []
        for expanded_query in expanded_queries:
            try:
                # Get more results for comprehensive coverage
                results = self.retriever.search(
                    query=expanded_query, 
                    n_results=20,
                    include_images=False
                )
                if results and results['text_results']:
                    all_results.extend(results['text_results'])
            except Exception as e:
                print(f"Error searching for '{expanded_query}': {e}")
                continue
        
        # Remove duplicates while preserving order
        seen_content = set()
        unique_results = []
        for result in all_results:
            content_preview = result['content'][:150].lower()
            content_hash = hash(content_preview)
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        # Sort by similarity score but be more inclusive
        unique_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # Use a more lenient relevance threshold to get more content
        relevance_threshold = 0.4
        relevant_results = [
            result for result in unique_results 
            if result['similarity_score'] >= relevance_threshold
        ]
        
        # If we still don't have enough content, include even more
        if len(relevant_results) < num_slides * 3:
            relevance_threshold = 0.3
            relevant_results = [
                result for result in unique_results 
                if result['similarity_score'] >= relevance_threshold
            ]
        
        print(f"Retrieved {len(relevant_results)} relevant text chunks (threshold: {relevance_threshold})")
        print(f"Search mode: {self.mode}, User: {self.user_id}")
        
        # Show user stats
        user_stats = self.chroma_manager.get_user_stats(self.user_id)
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
                temperature=0.3,
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

    def save_presentation_package(self, outline: Dict, presentation: Dict, ppt_structure: Dict, base_filename: str = None):
        """Save complete presentation package"""
        if not base_filename:
            title_slug = presentation["presentation_title"].lower().replace(" ", "_")[:50]
            base_filename = f"presentation_{title_slug}"
        
        # Save outline
        outline_file = f"{base_filename}_outline_simple_user_123.json"
        with open(outline_file, 'w', encoding='utf-8') as f:
            json.dump(outline, f, indent=2, ensure_ascii=False)
        
        # Save presentation
        presentation_file = f"{base_filename}_final_simple_user_123.json"
        with open(presentation_file, 'w', encoding='utf-8') as f:
            json.dump(presentation, f, indent=2, ensure_ascii=False)
        
        # Save PPT structure
        ppt_file = f"{base_filename}_ppt_structure_simple_user_123.json"
        with open(ppt_file, 'w', encoding='utf-8') as f:
            json.dump(ppt_structure, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Presentation package saved:")
        print(f"   - Outline: {outline_file}")
        print(f"   - Final presentation: {presentation_file}")
        print(f"   - PPT structure: {ppt_file}")
        
        return {
            "outline_file": outline_file,
            "presentation_file": presentation_file,
            "ppt_structure_file": ppt_file
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
        
        # Show bullet point variation if available
        if "character_summary" in presentation:
            summary = presentation["character_summary"]
            print(f"🔢 Bullet Point Variation: {summary['bullet_point_variation']}")
            print(f"📏 Character Compliance: {summary['compliance_ratio']} within range")
        
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
        
        print(f"\n📑 SLIDE OVERVIEW (Professional Content):")
        for slide in presentation['slides']:
            if slide.get("slide_type") == "content":
                bullet_count = len([line for line in slide.get('content', '').split('\n') if line.strip().startswith('•')])
                word_count = len(slide.get('content', '').split())
                
                print(f"\n   Slide {slide['slide_number']}: {slide['slide_title']}")
                print(f"     📊 Content: {bullet_count} professional points, {word_count} words")
                
                # Show first 3 bullet points to demonstrate quality
                content_lines = [line for line in slide.get('content', '').split('\n') if line.strip().startswith('•')]
                for line in content_lines[:3]:
                    if line.strip():
                        print(f"     {line}")
                
                if len(content_lines) > 3:
                    print(f"     ... and {len(content_lines) - 3} more professional points")


# Main pipeline function
def create_content_rich_presentation_pipeline(
    query: str, 
    user_id: str,
    is_file_uploaded_by_user: bool = False,  # NEW: Track if user uploaded files
    mode: str = "corpus_only",  # Default to corpus_only
    num_slides: int = 8, 
    presentation_style: str = "corporate",
    openai_api_key: str = None,
    save_package: bool = True,
    merge_after_success: bool = True
) -> Dict[str, Any]:
    
    print("🚀 STARTING PROFESSIONAL PRESENTATION PIPELINE")
    print("=" * 60)
    print(f"👤 User: {user_id}")
    print(f"📁 User uploaded files: {'YES' if is_file_uploaded_by_user else 'NO'}")
    print(f"🔍 Mode: {mode}")
    
    # Validate mode based on file upload status
    if not is_file_uploaded_by_user and mode != "corpus_only":
        error_msg = f"❌ Cannot use mode '{mode}'. No files uploaded by user. Please use 'corpus_only' mode."
        print(error_msg)
        return {"error": error_msg}
    
    print(f"🎯 Style: {presentation_style}")
    print(f"📊 Slides: {num_slides}")
    
    # Rest of your existing function continues...
    # Initialize generator with user context
    generator = ProfessionalPresentationGenerator(
        user_id=user_id, 
        mode=mode, 
        openai_api_key=openai_api_key
    )
    
    # Generate presentation
    print(f"\n📝 GENERATING PROFESSIONAL PRESENTATION for '{query}'")
    outline = generator.generate_comprehensive_outline(query, num_slides, presentation_style)
    
    # Check if outline generation failed
    if "error" in outline:
        print(f"❌ Presentation generation failed: {outline['error']}")
        return {"error": outline["error"]}
    
    # Check if presentation_title exists before accessing it
    if 'presentation_title' not in outline:
        print(f"❌ Outline generation failed - missing presentation title")
        print(f"📋 Outline structure: {list(outline.keys())}")
        return {"error": "Outline generation failed - missing required fields"}
    
    print(f"   ✅ Professional presentation generated: {outline['presentation_title']}")
    
    # Convert outline to presentation format
    print(f"\n🔄 CONVERTING TO PRESENTATION FORMAT")
    presentation = generator.outline_to_presentation(outline)
    
    # Check if presentation conversion failed
    if "error" in presentation:
        print(f"❌ Presentation conversion failed: {presentation['error']}")
        return {"error": presentation["error"]}
    
    # Save package
    files = None
    if save_package:
        print(f"\n💾 SAVING PRESENTATION PACKAGE")
        try:
            files = generator.save_presentation_package(outline, presentation, {})
            print(f"   ✅ Package saved successfully")
        except Exception as e:
            print(f"   ❌ Failed to save package: {e}")
    
    # Merge temp to main corpus if requested and successful
    if merge_after_success and "error" not in outline:
        print(f"\n🔄 MERGING TEMP UPLOADS TO MAIN CORPUS")
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
    print(f"\n📋 PRESENTATION SUMMARY")
    generator.print_professional_summary(presentation)
    
    return {
        "outline": outline,
        "presentation": presentation,
        "files": files if save_package else None,
        "user_id": user_id,
        "search_mode": mode
    }


if __name__ == "__main__":
    # Set your OpenAI API key
    OPENAI_API_KEY = "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"  # Replace with your actual API key
    
    # Run direct pipeline
    result = create_content_rich_presentation_pipeline(
        query="Introduction to Aksha AI Surveillance System",
        user_id="user_123",
        mode="corpus_only",
        num_slides=8,
        presentation_style="technical",
        openai_api_key=OPENAI_API_KEY,
        save_package=True,
        merge_after_success=True
    )