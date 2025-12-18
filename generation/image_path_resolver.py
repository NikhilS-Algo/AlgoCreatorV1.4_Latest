# image_path_resolver.py

import os
from typing import List, Dict, Optional

class ImagePathResolver:
    """
    Resolves relative image paths to absolute filesystem paths
    Handles the conversion between stored paths and actual file locations
    """
    
    @staticmethod
    def resolve_to_absolute_path(stored_path: str, user_id: str) -> str:
        """
        Convert stored relative path to actual absolute filesystem path
        
        Args:
            stored_path: Path stored in VectorDB (e.g., "images/virat/main_corpus/img_xxx.jpg")
            user_id: User ID for path resolution
            
        Returns:
            Absolute filesystem path
        """
        # If it's already an absolute path and exists, return as-is
        if os.path.isabs(stored_path) and os.path.exists(stored_path):
            return stored_path
        
        # If it's a relative path starting with "images/", convert to absolute
        if stored_path.startswith(f"images/{user_id}/main_corpus/"):
            # This is our standard format - convert to absolute
            absolute_path = os.path.abspath(stored_path)
            if os.path.exists(absolute_path):
                return absolute_path
        
        # Try to extract filename and search in standard locations
        filename = os.path.basename(stored_path)
        
        # Search in priority order
        search_locations = [
            # Primary location - main_corpus
            os.path.abspath(f"images/{user_id}/main_corpus/{filename}"),
            # Fallback location - temp_uploads (during processing)
            os.path.abspath(f"images/{user_id}/temp_uploads/{filename}"),
            # Legacy locations
            os.path.abspath(stored_path),
            stored_path,  # Original as last resort
        ]
        
        for location in search_locations:
            if os.path.exists(location):
                return location
        
        # If not found, log warning but return the expected main_corpus path
        print(f"⚠️  Image not found, returning expected path: {stored_path}")
        return os.path.abspath(f"images/{user_id}/main_corpus/{filename}")
    
    @staticmethod
    def store_relative_path(user_id: str, filename: str) -> str:
        """
        Generate consistent relative path for storage in VectorDB
        
        Args:
            user_id: User ID
            filename: Image filename
            
        Returns:
            Relative path in format: "images/{user_id}/main_corpus/{filename}"
        """
        return f"images/{user_id}/main_corpus/{filename}"
    
    @staticmethod
    def is_image_accessible(stored_path: str, user_id: str) -> bool:
        """
        Check if an image is accessible at its resolved location
        
        Args:
            stored_path: Path stored in VectorDB
            user_id: User ID
            
        Returns:
            True if image is accessible, False otherwise
        """
        resolved_path = ImagePathResolver.resolve_to_absolute_path(stored_path, user_id)
        return os.path.exists(resolved_path)
    
    @staticmethod
    def ensure_images_accessible(image_metadata_list: List[Dict], user_id: str) -> Dict:
        """
        Check accessibility of all images and return statistics
        
        Args:
            image_metadata_list: List of image metadata dictionaries
            user_id: User ID
            
        Returns:
            Dictionary with accessibility statistics
        """
        accessible_images = []
        inaccessible_images = []
        
        for img_meta in image_metadata_list:
            stored_path = img_meta.get('image_path', '')
            resolved_path = ImagePathResolver.resolve_to_absolute_path(stored_path, user_id)
            is_accessible = os.path.exists(resolved_path)
            
            # Add resolution info to metadata
            img_meta['resolved_path'] = resolved_path
            img_meta['is_accessible'] = is_accessible
            img_meta['filename'] = os.path.basename(stored_path)
            
            if is_accessible:
                accessible_images.append(img_meta)
            else:
                inaccessible_images.append(img_meta)
        
        return {
            'accessible_images': accessible_images,
            'inaccessible_images': inaccessible_images,
            'total_accessible': len(accessible_images),
            'total_inaccessible': len(inaccessible_images),
            'accessibility_rate': len(accessible_images) / len(image_metadata_list) if image_metadata_list else 0
        }
    
    @staticmethod
    def get_image_locations(user_id: str) -> Dict:
        """
        Get information about image storage locations
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with location information
        """
        main_corpus_dir = f"images/{user_id}/main_corpus"
        temp_uploads_dir = f"images/{user_id}/temp_uploads"
        
        main_exists = os.path.exists(main_corpus_dir)
        temp_exists = os.path.exists(temp_uploads_dir)
        
        main_images = []
        temp_images = []
        
        if main_exists:
            main_images = [f for f in os.listdir(main_corpus_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
        
        if temp_exists:
            temp_images = [f for f in os.listdir(temp_uploads_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
        
        return {
            'main_corpus': {
                'path': os.path.abspath(main_corpus_dir),
                'exists': main_exists,
                'image_count': len(main_images),
                'images': main_images[:10]  # First 10 images
            },
            'temp_uploads': {
                'path': os.path.abspath(temp_uploads_dir),
                'exists': temp_exists,
                'image_count': len(temp_images),
                'images': temp_images[:10]  # First 10 images
            }
        }