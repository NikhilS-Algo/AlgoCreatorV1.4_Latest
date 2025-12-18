#Step2_Processing_unified_document_json_file_for_vector_store.py

import re
import json
from typing import List, Dict, Any
import nltk
from nltk.tokenize import sent_tokenize
import uuid
import os

class DocumentPreprocessor:
    def __init__(self):
        self.noise_patterns = [
            r'©\s*AlgoAnalytics\s*\.?\s*Pvt\s*\.?\s*Ltd\s*\|?\s*Page?\s*\d*',
            r'AlgoAnalytics\s*Pvt\.?\s*Ltd',
            r'Strictly\s*Confidential',
            r'Page\s+\d+',
            r'©.*AlgoAnalytics.*',
            r'\bPage\s*\d+\b',
            r'^\d+$',  # Single page numbers
        ]
        
    def remove_noise(self, text: str) -> str:
        """Remove noisy text patterns"""
        for pattern in self.noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove bullet points and special characters that don't add meaning
        text = re.sub(r'[•●▪■]\s*', '', text)
        return text.strip()
    
    def merge_text_elements(self, text_list: List[str]) -> str:
        """Merge list of text elements into coherent paragraph"""
        merged = ' '.join(text_list)
        merged = self.clean_text(merged)
        merged = self.remove_noise(merged)
        return merged
    
    def split_by_sentences(self, text: str, max_words: int = 150) -> List[str]:
        """Split text into chunks based on sentences and word count"""
        sentences = sent_tokenize(text)
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence_word_count = len(sentence.split())
            
            if current_word_count + sentence_word_count > max_words and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_word_count = sentence_word_count
            else:
                current_chunk.append(sentence)
                current_word_count += sentence_word_count
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

class PPTXProcessor(DocumentPreprocessor):
    def process_slide(self, slide_data: Dict) -> List[Dict]:
        """Process a single PPTX slide"""
        text = self.merge_text_elements(slide_data['text'])
        images = slide_data.get('images', [])
        
        # Generate unique base ID for this slide
        doc_id = slide_data.get('doc_id', 'unknown')
        slide_index = slide_data['index']
        session_id = slide_data.get('session_id', 'default')
        base_chunk_id = f"slide_{doc_id}_{slide_index}"
        
        # If text is short, return as single chunk
        if len(text.split()) <= 150:
            return [{
                'chunk_id': f"{base_chunk_id}_chunk_0_{session_id}",
                'text': text,
                'metadata': {
                    'doc_id': doc_id,
                    'slide_index': slide_index,
                    'images': images,
                    'unit_type': 'slide',
                    'session_id': session_id
                }
            }]
        
        # Split by bullet points if present
        bullet_sections = re.split(r'\n•\s*|\n●\s*', text)
        if len(bullet_sections) > 1:
            chunks = []
            chunk_counter = 0
            current_chunk_text = ""
            current_word_count = 0
            
            for section in bullet_sections:
                if not section.strip():
                    continue
                    
                section_word_count = len(section.split())
                
                # If adding this section exceeds 150 words and we have content, save current chunk
                if current_word_count + section_word_count > 150 and current_chunk_text:
                    chunks.append({
                        'chunk_id': f"{base_chunk_id}_chunk_{chunk_counter}_{session_id}",
                        'text': current_chunk_text.strip(),
                        'metadata': {
                            'doc_id': doc_id,
                            'slide_index': slide_index,
                            'images': images,
                            'unit_type': 'slide',
                            'is_bullet_section': True,
                            'session_id': session_id
                        }
                    })
                    chunk_counter += 1
                    current_chunk_text = section
                    current_word_count = section_word_count
                else:
                    if current_chunk_text:
                        current_chunk_text += " " + section
                    else:
                        current_chunk_text = section
                    current_word_count += section_word_count
            
            # Add the last chunk
            if current_chunk_text:
                chunks.append({
                    'chunk_id': f"{base_chunk_id}_chunk_{chunk_counter}_{session_id}",
                    'text': current_chunk_text.strip(),
                    'metadata': {
                        'doc_id': doc_id,
                        'slide_index': slide_index,
                        'images': images,
                        'unit_type': 'slide',
                        'is_bullet_section': True,
                        'session_id': session_id
                    }
                })
            
            return chunks
        
        # Otherwise split by sentences
        text_chunks = self.split_by_sentences(text, max_words=150)
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                'chunk_id': f"{base_chunk_id}_chunk_{i}_{session_id}",
                'text': chunk_text,
                'metadata': {
                    'doc_id': doc_id,
                    'slide_index': slide_index,
                    'images': images,
                    'unit_type': 'slide',
                    'session_id': session_id
                }
            })
        
        return chunks

class PDFProcessor(DocumentPreprocessor):
    def process_page(self, page_data: Dict) -> List[Dict]:
        """Process a single PDF page"""
        text = self.merge_text_elements(page_data['text'])
        images = page_data.get('images', [])
        
        # Generate unique base ID for this page
        doc_id = page_data.get('doc_id', 'unknown')
        page_index = page_data['index']
        session_id = page_data.get('session_id', 'default')
        base_chunk_id = f"pdf_{doc_id}_page_{page_index}"
        
        # If text is empty after processing, return empty
        if not text.strip():
            return []
        
        # Split into semantic chunks
        text_chunks = self.split_by_sentences(text, max_words=150)
        
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                'chunk_id': f"{base_chunk_id}_chunk_{i}_{session_id}",
                'text': chunk_text,
                'metadata': {
                    'doc_id': doc_id,
                    'page_index': page_index,
                    'images': images,
                    'unit_type': 'page',
                    'session_id': session_id
                }
            })
        
        return chunks

class DOCXProcessor(DocumentPreprocessor):
    def process_section(self, section_data: Dict) -> List[Dict]:
        """Process a DOCX section"""
        text = self.merge_text_elements(section_data['text'])
        images = section_data.get('images', [])
        
        # Generate unique base ID for this section
        doc_id = section_data.get('doc_id', 'unknown')
        section_index = section_data['index']
        session_id = section_data.get('session_id', 'default')
        base_chunk_id = f"docx_{doc_id}_section_{section_index}"
        
        # Remove footnotes and headers
        text = re.sub(r'\[\d+\]', '', text)  # Remove citation numbers
        text = self.remove_noise(text)
        
        # Split into 150-word chunks
        text_chunks = self.split_by_sentences(text, max_words=150)
        
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                'chunk_id': f"{base_chunk_id}_chunk_{i}_{session_id}",
                'text': chunk_text,
                'metadata': {
                    'doc_id': doc_id,
                    'section_index': section_index,
                    'images': images,
                    'unit_type': 'section',
                    'session_id': session_id
                }
            })
        
        return chunks

class TXTProcessor(DocumentPreprocessor):
    def process_paragraph(self, paragraph_data: Dict) -> List[Dict]:
        """Process a TXT paragraph"""
        text = self.merge_text_elements(paragraph_data['text'])
        
        # Generate unique base ID for this paragraph
        doc_id = paragraph_data.get('doc_id', 'unknown')
        para_index = paragraph_data['index']
        session_id = paragraph_data.get('session_id', 'default')
        base_chunk_id = f"txt_{doc_id}_para_{para_index}"
        
        # Use rolling window chunking with 150 words and 30-word overlap
        words = text.split()
        chunk_size = 150
        overlap = 30
        
        chunks = []
        start = 0
        
        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append({
                'chunk_id': f"{base_chunk_id}_chunk_{len(chunks)}_{session_id}",
                'text': chunk_text,
                'metadata': {
                    'doc_id': doc_id,
                    'paragraph_index': para_index,
                    'unit_type': 'paragraph',
                    'window_start': start,
                    'window_end': end,
                    'total_words': len(words),
                    'session_id': session_id
                }
            })
            
            if end >= len(words):
                break
                
            start = end - overlap  # Apply overlap
        
        return chunks

class JSONPreprocessor:
    def __init__(self):
        self.processors = {
            'pptx': PPTXProcessor(),
            'pdf': PDFProcessor(),
            'docx': DOCXProcessor(),
            'txt': TXTProcessor()
        }
    
    def preprocess_documents(self, input_json: Dict, user_id: str = "default", session_id: str = "default_session") -> Dict:
        """Main preprocessing function with session context"""
        processed_docs = []
        
        print(f"Total documents to process for user {user_id}, session {session_id}: {len(input_json['documents'])}")
        
        for document in input_json['documents']:
            doc_type = document['doc_type']
            doc_id = document['doc_id']
            units_count = len(document['units'])
            
            print(f"\nProcessing document: {doc_id} (type: {doc_type}, units: {units_count})")
            
            processor = self.processors.get(doc_type)
            
            if not processor:
                print(f"Warning: No processor for document type {doc_type}")
                continue
            
            doc_chunks = []
            
            for unit in document['units']:
                try:
                    unit_type = unit['unit_type']
                    unit_index = unit['index']
                    
                    # Add session_id to unit data
                    unit['session_id'] = session_id
                    unit['doc_id'] = doc_id
                    
                    if doc_type == 'pptx' and unit_type == 'slide':
                        chunks = processor.process_slide(unit)
                    elif doc_type == 'pdf' and unit_type == 'page':
                        chunks = processor.process_page(unit)
                    elif doc_type == 'docx' and unit_type == 'section':
                        chunks = processor.process_section(unit)
                    elif doc_type == 'txt' and unit_type == 'paragraph':
                        chunks = processor.process_paragraph(unit)
                    else:
                        continue
                    
                    doc_chunks.extend(chunks)
                    
                except Exception as e:
                    print(f"Error processing unit {unit.get('index', 'unknown')} in {doc_type}: {e}")
                    continue
            
            # Add document-level metadata
            for chunk in doc_chunks:
                chunk['metadata']['original_doc_type'] = doc_type
                chunk['metadata']['original_doc_id'] = document['doc_id']
                chunk['metadata']['user_id'] = user_id
                chunk['metadata']['session_id'] = session_id  # Add session context
                # Add word count for verification
                chunk['metadata']['word_count'] = len(chunk['text'].split())
            
            processed_docs.extend(doc_chunks)
            print(f"  Created {len(doc_chunks)} chunks for {doc_id}")
        
        # Ensure all chunk IDs are unique
        processed_docs = self._ensure_unique_chunk_ids(processed_docs)
        
        return {
            'processed_chunks': processed_docs,
            'total_chunks': len(processed_docs),
            'original_document_count': len(input_json['documents']),
            'user_id': user_id,
            'session_id': session_id
        }
    
    def _ensure_unique_chunk_ids(self, chunks: List[Dict]) -> List[Dict]:
        """Ensure all chunk IDs are unique across the entire dataset"""
        seen_ids = set()
        unique_chunks = []
        duplicate_count = 0
        
        for chunk in chunks:
            original_id = chunk['chunk_id']
            
            if original_id in seen_ids:
                # Generate unique ID using UUID
                unique_id = f"{original_id}_{uuid.uuid4().hex[:8]}"
                chunk['chunk_id'] = unique_id
                duplicate_count += 1
                print(f"  Fixed duplicate ID: {original_id} -> {unique_id}")
            else:
                unique_id = original_id
            
            seen_ids.add(unique_id)
            unique_chunks.append(chunk)
        
        if duplicate_count > 0:
            print(f"  Fixed {duplicate_count} duplicate chunk IDs")
        
        return unique_chunks
    
    def save_processed_json(self, processed_data: Dict, output_path: str = None, user_id: str = None, session_id: str = None):
        """Save processed data with session-based naming"""
        if output_path is None and user_id and session_id:
            # Generate session-based filename
            os.makedirs(f"processed_json/{user_id}", exist_ok=True)
            output_path = f"processed_json/{user_id}/step2_processed_{user_id}_{session_id}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved processed data: {output_path}")

# Usage example
def main():
    # Load your JSON file
    user_id = "user_123"
    session_id = "upload_1"
    input_file_path = f"processed_json/{user_id}/unified_documents_{user_id}_{session_id}.json"
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            input_json = json.load(f)
        print(f"Successfully loaded JSON file: {input_file_path}")
    except FileNotFoundError:
        print(f"Error: File '{input_file_path}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: File '{input_file_path}' contains invalid JSON.")
        return
    
    preprocessor = JSONPreprocessor()
    
    # Process the documents with user context
    processed_data = preprocessor.preprocess_documents(input_json, user_id, session_id)
    
    # Save to file
    output_file_path = f"processed_json/{user_id}/step2_processed_{user_id}_{session_id}.json"
    preprocessor.save_processed_json(processed_data, output_file_path)
    print(f"Processed data saved to: {output_file_path}")
    
    # Print summary
    print(f"\n=== Processing Summary ===")
    print(f"User: {processed_data['user_id']}")
    print(f"Session: {processed_data['session_id']}")
    print(f"Original documents: {processed_data['original_document_count']}")
    print(f"Total chunks created: {processed_data['total_chunks']}")
    
    # Show breakdown by document type
    doc_types = {}
    for chunk in processed_data['processed_chunks']:
        doc_type = chunk['metadata']['original_doc_type']
        doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
    
    print(f"\nChunks by document type:")
    for doc_type, count in doc_types.items():
        print(f"  {doc_type}: {count} chunks")
    
    # Show word count statistics
    word_counts = [chunk['metadata']['word_count'] for chunk in processed_data['processed_chunks']]
    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
    max_words = max(word_counts) if word_counts else 0
    min_words = min(word_counts) if word_counts else 0
    
    print(f"\nWord Count Statistics:")
    print(f"  Average: {avg_words:.1f} words")
    print(f"  Maximum: {max_words} words")
    print(f"  Minimum: {min_words} words")
    
    # Show chunks that exceed 150 words (for verification)
    oversized_chunks = [chunk for chunk in processed_data['processed_chunks'] if chunk['metadata']['word_count'] > 160]
    if oversized_chunks:
        print(f"\nWarning: {len(oversized_chunks)} chunks exceed 160 words")
        for chunk in oversized_chunks[:3]:  # Show first 3 oversized chunks
            print(f"  {chunk['chunk_id']}: {chunk['metadata']['word_count']} words")
    
    # Verify all chunk IDs are unique
    chunk_ids = [chunk['chunk_id'] for chunk in processed_data['processed_chunks']]
    unique_ids = set(chunk_ids)
    print(f"\n✅ Unique Chunk IDs: {len(unique_ids)} / {len(chunk_ids)}")
    
    # Show sample chunks
    print(f"\n=== Sample Chunks ===")
    for i, chunk in enumerate(processed_data['processed_chunks'][:3]):
        print(f"\nSample Chunk {i+1}:")
        print(f"ID: {chunk['chunk_id']}")
        print(f"Words: {chunk['metadata']['word_count']}")
        print(f"Text preview: {chunk['text'][:100]}...")
        print(f"Doc Type: {chunk['metadata']['original_doc_type']}")
        print(f"User: {chunk['metadata']['user_id']}")
        print(f"Session: {chunk['metadata']['session_id']}")

if __name__ == "__main__":
    main()