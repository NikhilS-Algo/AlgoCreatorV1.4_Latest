#step3_Image_caption_generator_Openai.py

import json
import torch
from PIL import Image
import base64
from io import BytesIO
from typing import List, Dict, Any
import os
from openai import OpenAI
import time
from dotenv import load_dotenv
load_dotenv()



from dotenv import load_dotenv
load_dotenv()

class GPT4oMiniCaptionGenerator:
    def __init__(self, api_key: str = None, max_retries: int = 3, delay: float = 1.0):
        """
        Initialize GPT-4o-mini caption generator
        
        Args:
            api_key: OpenAI API key (if None, will use OPENAI_API_KEY environment variable)
            max_retries: Maximum number of retries for API calls
            delay: Delay between retries in seconds
        """
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        self.max_retries = max_retries
        self.delay = delay
        
        if not self.client.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode image to base64 string for API consumption"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')
                
                # Save to bytes buffer
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                buffer.seek(0)
                
                # Encode to base64
                image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                return image_base64
        except Exception as e:
            print(f"Error encoding image {image_path}: {e}")
            raise
    
    def generate_caption(self, image_path: str) -> str:
        """
        Generate detailed, semantically rich caption for a single image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Detailed caption describing the image content
        """
        for attempt in range(self.max_retries):
            try:
                # Encode image
                base64_image = self.encode_image_to_base64(image_path)
                
                # System prompt for detailed, categorization-friendly descriptions
                system_prompt = """
                You are an expert in generating precise, descriptive image captions for semantic search.
                Generate a single, cohesive, and detailed paragraph with STRICT maximum of 250 characters.
                1. Explicitly identifies whether the image is a logo, symbol, icon, photograph, diagram, or illustration.
                2. Describes all key visual elements
                3. Notes any visible text, branding, or identifiable objects.
                5. Uses clear, search-optimized language suitable for embedding in a vector database.

                For logos: "This is a logo for [brand/company] featuring [design description]."
                For symbols: "This appears to be a symbol representing [concept]."
                For icons: "This is an icon depicting [subject]."

                Avoid redundancy and Keep the description factual, concise, and useful for semantic similarity search, don't assume or made up things
                Ensure the output is one well-structured paragraph with STRICT maximum 250 characters .

                """

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text", 
                                    "text": "Please provide a detailed description of this image that would be useful for semantic search and categorization in a vector database. Be specific about what type of content this is (logo, photograph, diagram, etc.)."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=50,
                    temperature=0.1  # Low temperature for consistent, factual descriptions
                )
                
                caption = response.choices[0].message.content.strip()
                return caption
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {image_path}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.delay * (2 ** attempt))  # Exponential backoff
                else:
                    return f"Error: Could not generate caption - {str(e)}"
    
    def batch_generate_captions(self, image_paths: List[str], batch_delay: float = 0.0) -> List[str]:
        """
        Generate captions for multiple images with rate limiting
        
        Args:
            image_paths: List of paths to image files
            batch_delay: Delay between API calls to respect rate limits
            
        Returns:
            List of captions in the same order as input paths
        """
        captions = []
        for i, image_path in enumerate(image_paths):
            print(f"Processing image {i+1}/{len(image_paths)}: {os.path.basename(image_path)}")
            caption = self.generate_caption(image_path)
            captions.append(caption)
            
            # Rate limiting between images
            if i < len(image_paths) - 1:
                time.sleep(batch_delay)
                
        return captions

class ImageCaptionProcessor:
    def __init__(self, api_key: str = None):
        """
        Initialize the image caption processor
        
        Args:
            api_key: OpenAI API key
        """
        self.caption_generator = GPT4oMiniCaptionGenerator(api_key)
    
    def process_user_documents(self, user_id: str, session_id: str, step2_input_file: str = None, batch_delay: float = 0.0) -> str:
        """
        Process documents for a specific user and generate image captions
        
        Args:
            user_id: User ID (required)
            session_id: Session ID (required)
            step2_input_file: Optional custom input file path
            batch_delay: Delay between API calls for rate limiting
            
        Returns:
            Path to the output JSON file
        """
        if not user_id or not session_id:
            raise ValueError("user_id and session_id are required")
        
        # Generate file names based on user ID and session
        if step2_input_file:
            input_file = step2_input_file
        else:
            input_file = f"processed_json/{user_id}/step2_processed_{user_id}_{session_id}.json"
        
        output_file = f"processed_json/{user_id}/step3_captions_{user_id}_{session_id}.json"
        
        print(f"🔄 Processing image captions for user: {user_id}, session: {session_id}")
        print(f"📥 Input file: {input_file}")
        print(f"📤 Output file: {output_file}")
        
        # Check if input file exists
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Load processed documents
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ Loaded JSON file: {input_file}")
        except Exception as e:
            print(f"❌ Error loading JSON file: {e}")
            raise
        
        # Collect all unique image paths
        all_image_paths = set()
        image_to_chunks = {}  # Track which chunks reference which images
        
        for chunk_idx, chunk in enumerate(data['processed_chunks']):
            images = chunk['metadata'].get('images', [])
            for img_path in images:
                if img_path and os.path.exists(img_path):  # Skip empty paths and non-existent files
                    all_image_paths.add(img_path)
                    if img_path not in image_to_chunks:
                        image_to_chunks[img_path] = []
                    image_to_chunks[img_path].append(chunk_idx)
        
        print(f"📊 Found {len(all_image_paths)} unique images across {len(data['processed_chunks'])} chunks")
        
        # Generate captions for all images
        image_captions = {}
        image_paths_list = list(all_image_paths)
        
        # Filter out images that don't exist
        valid_image_paths = []
        for img_path in image_paths_list:
            if os.path.exists(img_path):
                valid_image_paths.append(img_path)
            else:
                print(f"⚠️ Warning: Image file not found: {img_path}")
                image_captions[img_path] = f"Error: Image file not found - {img_path}"
        
        if valid_image_paths:
            print(f"🖼️ Processing {len(valid_image_paths)} valid images with GPT-4o-mini...")
            
            # Generate captions in batches with rate limiting
            captions = self.caption_generator.batch_generate_captions(valid_image_paths, batch_delay)
            
            # Map captions back to image paths
            for img_path, caption in zip(valid_image_paths, captions):
                image_captions[img_path] = caption
                print(f"✅ Generated caption for {os.path.basename(img_path)}: {caption[:50]}...")
        else:
            print("ℹ️ No valid images found to process")
        
        # Update chunks with image captions
        updated_chunks = 0
        for chunk in data['processed_chunks']:
            images = chunk['metadata'].get('images', [])
            if images:
                # Create new images_with_captions list
                images_with_captions = []
                for img_path in images:
                    if img_path in image_captions:
                        images_with_captions.append({
                            'path': img_path,
                            'caption': image_captions[img_path],
                            'caption_model': 'gpt-4o-mini',
                            'user_id': user_id,
                            'session_id': session_id
                        })
                    else:
                        images_with_captions.append({
                            'path': img_path,
                            'caption': 'Caption not generated',
                            'caption_model': 'none',
                            'user_id': user_id,
                            'session_id': session_id
                        })
                
                # Replace old images list with new structure
                chunk['metadata']['images_with_captions'] = images_with_captions
                updated_chunks += 1
        
        # Add user context to the data
        data['user_id'] = user_id
        data['session_id'] = session_id
        data['processing_timestamp'] = time.time()
        data['total_images_processed'] = len(valid_image_paths)
        data['total_chunks_with_images'] = updated_chunks
        
        # Save updated data with session-based name
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved updated data to: {output_file}")
            print(f"📝 Updated {updated_chunks} chunks with detailed image captions")
        except Exception as e:
            print(f"❌ Error saving output file: {e}")
            raise
        
        return output_file

if __name__ == "__main__":
    # Load environment variables from .env file
    
    # Just provide the user_id and session_id - file names will be generated automatically
    user_id = "user_123"
    session_id = "upload_1"
    
    # API key from environment variable (now loaded from .env)
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ Please set OPENAI_API_KEY environment variable in your .env file")
        exit(1)
    
    print(f"🔑 API Key loaded successfully: {api_key[:10]}...")  # Show first 10 chars for verification
    
    # Initialize processor and run
    processor = ImageCaptionProcessor(api_key=api_key)
    output_file = processor.process_user_documents(user_id=user_id, session_id=session_id)
    
    print(f"\n✅ Completed! Output file: {output_file}")