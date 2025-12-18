# __import__('pysqlite3')
# import sys
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

################################### Above code is added to resolve the issue of unsupported version of sqlite3 for chroma


#to create chromadb
import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.config import Settings
from chromadb.utils import embedding_functions

import re
import tqdm
from tqdm import tqdm
import statistics
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
from rank_bm25 import BM25Okapi
from collections import Counter
import math
from itertools import combinations
import imagehash
import io
import json
import faiss
from PIL import Image
import torch
import os
from typing import List, Dict
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch.nn.functional as F
import pickle
from pathlib import Path
import fitz
from typing import Any


from utils.constants import output_files_path, v2_ppt_data_path, v2_json_files_path, v2_persist_directory

# output_files_path = "./retrieval/Output_files"

# # Path for Images of PPT (create)
# v2_ppt_data_path = "./retrieval/version2/PPT_DATA" 

# # Json file path for extracted content (create)
# v2_json_files_path = "./retrieval/version2/Json_Files"

# # persist directory to store vector database (create)
# v2_persist_directory = "./retrieval/version2/PPT_DB_NEW"

def combine_pdf_slides(
    faiss_results: Dict[str, List],
    v2_ppt_data_path: str,
    output_files_path: str,
    slide_counts: List[List[int]]  # [[main_slides_count, similar_slides_count], ...] 
):
    """
    Combine PDF slides from main results only (excluding similar results).

    Args:
        faiss_results: Results from query_chroma function
        output_base_dir: Base directory where PDF files are stored
        output_files_path: Path where output PDF will be saved
        slide_counts: List of [main_slides, similar_slides] counts for each query

    Returns:
        str: Path to the combined PDF file
    """ 

    v2_ppt_data_path = Path(v2_ppt_data_path)
    output_files_path = Path(output_files_path)

    slides = faiss_results.get('metadatas', [])
    result_types = faiss_results.get('result_types', [])

    if not slides or not result_types:
        raise ValueError("No slides or result types found in faiss_results")

    if len(slides) != len(result_types):
        raise ValueError("Mismatch between slides and result_types length")

    # Calculate total number of main slides to include
    total_main_slides = sum(count[0] for count in slide_counts)

    pdf_pages = []
    processed_count = 0

    # Process slides in order, but only include main results
    for i, (slide_metadata, result_type) in enumerate(zip(slides, result_types)):
        # Stop if we've processed all main slides
        if processed_count >= total_main_slides:
            break

        # Only process main results (skip similar results)
        if result_type != "results":
            continue

        try:
            full_file_path = slide_metadata['file_path']

            # Remove .pptx extension if present
            if full_file_path.endswith(".pptx"):
                full_file_path = full_file_path[:full_file_path.rfind(".pptx")]

            base_filename = os.path.basename(full_file_path)
            file_id = slide_metadata['file_id']
            slide_number = slide_metadata["slide_number"]

            # Construct PDF path
            pdf_path = f"{v2_ppt_data_path}/FID{file_id}/{base_filename}.pdf" 

            if os.path.exists(pdf_path):
                pdf_pages.append((pdf_path, slide_number - 1, slide_metadata))
                processed_count += 1
                #print(f"Added slide {slide_number} from {base_filename} (Main result {processed_count}/{total_main_slides})")
            else:
                print(f"PDF file not found: {pdf_path}")

        except KeyError as e:
            print(f"Missing key in slide metadata: {e}")
            continue
        except Exception as e:
            print(f"Error processing slide {i}: {str(e)}")
            continue

    if not pdf_pages:
        print("No valid PDF pages to combine. Exiting function.")
        raise ValueError("No valid slides were found to combine into a PDF.")

    print(f"\nTotal main slides to combine: {len(pdf_pages)}")

    # Create output PDF
    output_pdf = fitz.open()
    successfully_added = 0

    for pdf_path, page_num, slide_metadata in pdf_pages:
        try:
            with fitz.open(pdf_path) as src_pdf:
                if 0 <= page_num < len(src_pdf):
                    output_pdf.insert_pdf(src_pdf, from_page=page_num, to_page=page_num)
                    successfully_added += 1
                else:
                    print(f"Page {page_num + 1} not found in {pdf_path} (has {len(src_pdf)} pages)")
        except Exception as e:
            print(f"Error processing {pdf_path}, page {page_num + 1}: {str(e)}")

    if output_pdf.page_count == 0:
        print("No pages were successfully added to the output PDF.")
        raise ValueError("Cannot save PDF: No pages were added.")

    # Save combined PDF
    combined_pdf_path = output_files_path / "retrieved_slides.pdf"
    output_pdf.save(str(combined_pdf_path))
    output_pdf.close()

    print(f"\nSuccessfully created PDF with {successfully_added} slides: {combined_pdf_path}")
    return str(combined_pdf_path)


def initialize_chroma(v2_persist_directory: str) -> chromadb.Client:
 #Chroma converts the text into the embeddings using all-MiniLM-L6-v2, but we have modified the collection to use another embedding model.
    # sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="./retrieval/version2/Models/e5-large-v2")
    # sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="intfloat/e5-large-v2")
    # sentence_transformer_ef = SentenceTransformer('intfloat/e5-large-v2')

    new_settings = Settings(
        chroma_api_impl="chromadb.api.segment.SegmentAPI",
        is_persistent=True,
        persist_directory=v2_persist_directory,
        chroma_server_ssl_enabled=True,
        chroma_server_host="localhost",
        chroma_server_http_port=8080,
        anonymized_telemetry=False
    )

    # chroma_client = chromadb.PersistentClient(path = v2_persist_directory, settings = new_settings)

    # collection = chroma_client.get_or_create_collection("Slides")
    # # collection = chroma_client.get_or_create_collection("Slides", embedding_function = sentence_transformer_ef)

    return chromadb.PersistentClient(path=v2_persist_directory, settings=new_settings)

chroma_client = initialize_chroma(v2_persist_directory)
collection = chroma_client.get_or_create_collection("Slides")
# hf_model = SentenceTransformer('./retrieval/version2/Models/e5-large-v2')
hf_model = SentenceTransformer('intfloat/e5-large-v2')


def separate_content(text):
    # Remove any surrounding quotes
    text = text.strip("'\"")

    # Split the content into sections
    sections = re.split(r'\n(?=Text:|\*\*Table Summary\*\*:|Images Summary:)', text)
    text_content = ""
    table_content = ""
    images_summary_content = ""

    for section in sections:
        if section.startswith("Text:"):
            text_content = section.replace("Text:", "").strip()
        elif section.startswith("**Table Summary**:"):
            table_content = section.replace("**Table Summary**:", "").strip()
        elif section.startswith("Images Summary:"):
            images_summary_content = section.replace("Images Summary:", "").strip()

    # Clean up the images summary content
    images_summary_content = images_summary_content.strip("[]")

    return text_content, table_content, images_summary_content


# Get all documents and metadatas from the collection
def remove_low_priority_slides_s(collection):

  docs = collection.get(
      include=['documents', 'metadatas']
  )

  # Filter out documents with no text, table, or image summary content
  filtered_docs = []
  for i in range(len(docs['documents'])):
    text_content, table_content, images_summary_content = separate_content(docs['documents'][i])
    if text_content or table_content or images_summary_content:
      filtered_docs.append({
          'id': docs['ids'][i],
          'document': docs['documents'][i],
          'metadata': docs['metadatas'][i]
      })

  # Filter out documents with text content less than 15 characters and no table content, but with image summary content
  selected_docs = []
  for doc in filtered_docs:
    text_content, table_content, images_summary_content = separate_content(doc['document'])
    if len(text_content) < 300 and not table_content:
      selected_docs.append(doc)

  # Add the remaining documents to the new collection
  ids = [doc['id'] for doc in selected_docs]

  return ids

# ids = remove_low_priority_slides_s()
# print(len(ids))



# Get all documents from the collection
# Get all documents from the collection
def remove_low_priority_slides_d():
  docs = collection.get(
      include=['documents', 'metadatas']
  )

  # Filter out documents with no text, table, or image summary content
  filtered_docs = []
  for i in range(len(docs['documents'])):
    text_content, table_content, Image_summary_content = separate_content(docs['documents'][i])
    if text_content or table_content or Image_summary_content:
      filtered_docs.append({
          'id': docs['ids'][i],
          'document': docs['documents'][i],
          'metadata': docs['metadatas'][i]
      })

  # Calculate the length of text content for each document
  text_lengths = []
  for doc in filtered_docs:
    text_content, _, _ = separate_content(doc['document'])
    text_lengths.append(len(text_content))

  # Calculate the threshold for the bottom 20%
  threshold = np.percentile(text_lengths, 20)
#   print(threshold)

  # Select documents that fall in the bottom 10% based on text length, no table content, but with image summary content (not checked??)
  selected_docs = []
  for doc in filtered_docs:
    text_content, table_content, Image_summary_content = separate_content(doc['document'])
    if len(text_content) <= threshold and not table_content:
      selected_docs.append(doc)

  ids = [doc['id'] for doc in selected_docs]

#   print("Length",len(ids))
#   print("Id's:",ids)

  return ids

# ids = remove_low_priority_slides_d()
# print(len(ids))
# print(ids)



def linear_decay(doc_timestamp, current_time, max_age_days=1095):
    time_diff_days = (current_time - doc_timestamp).days
    weight = max(0, 1 - time_diff_days / max_age_days)
    return weight

model_s = SentenceTransformer('./retrieval/version2/Models/e5-small-v2')
# model_s = SentenceTransformer('intfloat/e5-small-v2')

def compute_dynamic_bm25_parameters(query, k1_min=1.0, k1_max=1.5, b_min=0.4, b_max=0.7, max_length=10):
    query_length = len(query)

    # Ensure query_length doesn't exceed max_length for scaling
    query_length = min(query_length, max_length)

    # Calculate k1 and b dynamically using linear scaling
    k1 = k1_min + (k1_max - k1_min) * ((query_length - 1) / (max_length - 1))
    b = b_min + (b_max - b_min) * ((query_length - 1) / (max_length - 1))

    # Round to nearest 0.1
    k1 = round(k1 * 10) / 10
    b = round(b * 10) / 10

    return k1, b

def rerank_slides_based_on_tags_new(data, query_tags):
    # Step 1: Extract aggregated text content per slide
    def extract_slide_text(data):
        slide_text_data = {}
        all_slide_texts = []
        for item in data:
            presentation = item['ids']
            document_content = item['document']
            start_text = document_content.find("Text:\n[") + len("Text:\n[")
            end_text = document_content.find("]", start_text)
            text_content = document_content[start_text:end_text].strip()

            # Skip if text_content is empty
            if not text_content:
                print(f"Skipping Slide {presentation}: Empty text content.")
                continue

            slide_text_data[presentation] = text_content
            all_slide_texts.append(text_content)
            print(f"Slide {presentation}: {text_content}")

        print(f"\nSlide Corpus: {all_slide_texts}\n")
        print(f"No. of slides: {len(all_slide_texts)}\n")
        return slide_text_data, all_slide_texts

    def preprocess_text(slide_text_data):
        preprocessed_data = {}
        for presentation, content in slide_text_data.items():
            cleaned_text = content.lower()
            preprocessed_data[presentation] = cleaned_text
        return preprocessed_data

    def rank_slides_using_bm25(preprocessed_data, query_tags, all_slide_texts):
        tokenized_corpus = [text.lower().split() for text in all_slide_texts]
        k1, b = compute_dynamic_bm25_parameters(query_tags)
        bm25 = BM25Okapi(tokenized_corpus, k1=k1, b=b)
        ranked_bm25_per_presentation = {presentation: {} for presentation in preprocessed_data.keys()}

        for tag in query_tags:
            tokenized_query = tag.lower().split()
            bm25_scores = bm25.get_scores(tokenized_query)
            min_bm25, max_bm25 = min(bm25_scores), max(bm25_scores)
            normalized_bm25_scores = [
                (score - min_bm25) / (max_bm25 - min_bm25) if max_bm25 > min_bm25 else 0 for score in bm25_scores
            ]
            for idx, presentation in enumerate(preprocessed_data.keys()):
                ranked_bm25_per_presentation[presentation][tag] = normalized_bm25_scores[idx]
        return ranked_bm25_per_presentation

    def rank_slides_using_pmi(preprocessed_data, query_tags, all_slide_texts, use_smoothing=False, smoothing_factor=1e-5):
        all_slide_texts = [text.lower() for text in all_slide_texts]
        word_counts = Counter(" ".join(all_slide_texts).split())
        total_words = sum(word_counts.values())
        ranked_pmi_per_presentation = {presentation: {} for presentation in preprocessed_data.keys()}

        for presentation, content in preprocessed_data.items():
            content = content.lower()
            content_size = len(content.split())
            for tag in query_tags:
                tag_lower = tag.lower()
                if " " in tag_lower:
                    tag_pattern_corpus = re.compile(r'\b' + re.escape(tag_lower) + r'\b', re.IGNORECASE)
                    tag_count_in_corpus = len(tag_pattern_corpus.findall(" ".join(all_slide_texts)))
                    tag_pattern_content = re.compile(r'\b' + re.escape(tag_lower) + r'\b', re.IGNORECASE)
                    tag_occurrences_in_content = len(tag_pattern_content.findall(content))
                else:
                    tag_count_in_corpus = word_counts.get(tag_lower, 0)
                    tag_occurrences_in_content = content.split().count(tag_lower)

                if tag_count_in_corpus == 0 or tag_occurrences_in_content == 0:
                    pmi_score = 0
                else:
                    if use_smoothing:
                        pmi_score = np.log(
                            ((tag_occurrences_in_content + smoothing_factor) / content_size) /
                            ((tag_count_in_corpus + smoothing_factor) / total_words)
                        )
                    else:
                        pmi_score = np.log(
                            (tag_occurrences_in_content / content_size) /
                            (tag_count_in_corpus / total_words)
                        )
                ranked_pmi_per_presentation[presentation][tag] = max(pmi_score, 0)

        all_pmi_scores = [score for scores in ranked_pmi_per_presentation.values() for score in scores.values()]
        min_pmi, max_pmi = min(all_pmi_scores), max(all_pmi_scores)
        if max_pmi > min_pmi:
            for presentation in ranked_pmi_per_presentation.keys():
                for tag in ranked_pmi_per_presentation[presentation].keys():
                    ranked_pmi_per_presentation[presentation][tag] = (
                        (ranked_pmi_per_presentation[presentation][tag] - min_pmi) / (max_pmi - min_pmi)
                    )
        return ranked_pmi_per_presentation

    def rank_slides_using_combined_cosine(preprocessed_data, query_tags):
        global model_s
        combined_query = " ".join(query_tags)
        combined_query_embedding = model_s.encode(combined_query, convert_to_tensor=True)
        ranked_cosine_per_presentation = {}

        for presentation, content in preprocessed_data.items():
            slide_embedding = model_s.encode(content, convert_to_tensor=True)
            cosine_score = util.pytorch_cos_sim(combined_query_embedding, slide_embedding).squeeze().item()
            normalized_cosine_score = (cosine_score + 1) / 2
            ranked_cosine_per_presentation[presentation] = normalized_cosine_score
        return ranked_cosine_per_presentation

    def rerank_data_by_scores(data, final_combined_scores):
        for item in data:
            item['final_score'] = final_combined_scores.get(item['ids'], 0)
        sorted_data = sorted(data, key=lambda x: x['final_score'], reverse=True)
        for item in sorted_data:
            item['reranking_score'] = item['final_score']
        return sorted_data

    # ---------- Main Function Flow ----------

    # Step 1: Extract and preprocess slide text
    slide_text_data, all_slide_texts = extract_slide_text(data)

    # ✅ Step 2: Check if there are valid slides
    if not slide_text_data or not all_slide_texts:
        print("No valid slides with content found. Skipping reranking.")
        for item in data:
            item['final_score'] = 0
            item['reranking_score'] = 0
        return data

    preprocessed_text = preprocess_text(slide_text_data)

    # Step 3: Compute BM25 and PMI scores
    bm25_scores = rank_slides_using_bm25(preprocessed_text, query_tags, all_slide_texts)
    pmi_scores = rank_slides_using_pmi(preprocessed_text, query_tags, all_slide_texts, use_smoothing=False)

    # Step 4: Compute cosine scores if needed
    tag_length_threshold = 5
    if len(query_tags) > tag_length_threshold:
        combined_cosine_scores = rank_slides_using_combined_cosine(preprocessed_text, query_tags)
    else:
        combined_cosine_scores = {presentation: 0 for presentation in preprocessed_text.keys()}

    # Step 5: Final combined score per slide
    final_combined_scores = {}
    for presentation in preprocessed_text.keys():
        total_score = sum(
            [
                (bm25_scores[presentation][tag] + pmi_scores[presentation][tag]) / 2
                for tag in query_tags
            ]
        ) / len(query_tags)
        final_score = (total_score + combined_cosine_scores[presentation]) / (
            2 if combined_cosine_scores[presentation] else 1
        )
        final_combined_scores[presentation] = final_score

    # Step 6: Rerank the slides based on final scores
    reranked_data = rerank_data_by_scores(data, final_combined_scores)
    return reranked_data


def calculate_distance(slide1, slide2):
    return abs(slide1['combined_score'] - slide2['combined_score'])

# Function to find the slides that are farthest from each other
def find_farthest_slides(slides, n):
    max_distance = -1
    best_combination = None

    for combo in combinations(slides, n):
        total_distance = 0


        # Calculate the pairwise distances for the combination
        for i in range(len(combo)):
            for j in range(i + 1, len(combo)):
                total_distance += calculate_distance(combo[i], combo[j])

        if total_distance > max_distance:
            max_distance = total_distance
            best_combination = combo

    return best_combination



# Initialising the model that calculates relevance score
model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
relevance_model = AutoModelForSequenceClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Function to calculate relevance score
def get_relevance_score(query, document):
    inputs = tokenizer(query, document, return_tensors="pt", truncation=True, max_length=512, padding=True)
    with torch.no_grad():
        outputs = relevance_model(**inputs)

    logits = outputs.logits.squeeze()

    if logits.ndim == 0:
        logits = logits.unsqueeze(0)

    if logits.shape[0] == 2:
        return F.softmax(logits, dim=0)[1].item()
    elif logits.shape[0] == 1:
        return torch.sigmoid(logits).item()
    else:
        return F.softmax(logits, dim=0).max().item()

# Function to filter unique Image using image perceptual hashing
def filter_unique_Image(image_paths, used_hashes, threshold=5):

    unique_Image = {}

    for image_path,value in image_paths.items():

        image = Image.open(image_path)
        # Calculate perceptual hash (phash) for the image
        phash = imagehash.phash(image) #???

        # Check against all used hashes
        is_unique = True
        for used_hash in used_hashes:
            if phash - used_hash <= threshold:
                is_unique = False
                break

        # If the image is unique, add it to the unique_Image dict
        if is_unique:
            unique_Image[image_path] = value
            used_hashes.add(phash)  # Optionally add this hash to used_hashes

    return unique_Image


def query_chroma(collection, queries: List[Dict], use_hnsw: bool = True, normalize: bool = True,
                 folder_names: List[str] = None, tags: List[str] = None, date_filter: dict = None):
    

    creation_start = date_filter.get("creation_start") if date_filter else None
    creation_end = date_filter.get("creation_end") if date_filter else None
    modification_start = date_filter.get("modification_start") if date_filter else None
    modification_end = date_filter.get("modification_end") if date_filter else None
    all_results = []
    best_result = []
    excluded_files = set()
    used_hashes = set()
    unique_items = []
    slide_counts = []
    removable_slides = remove_low_priority_slides_d() #using static for now 
    for item in removable_slides:
      excluded_files.add(item)
    print("Number of excluded files: ", len(excluded_files)) 

    # Function to check if a date is within specified range
    # def is_date_in_range(date_str, start_date=None, end_date=None):
    #     if not date_str or (start_date is None and end_date is None):
    #         return True

    #     def parse_date_safe(date_input):
    #         """Try parsing ISO first, then fallback to known format."""
    #         try:
    #             return datetime.fromisoformat(date_input)
    #         except ValueError:
    #             try:
    #                 return datetime.strptime(date_input, '%a %b %d %H:%M:%S %Y')
    #             except ValueError:
    #                 return None

    #     try:
    #         # Parse the input date
    #         date_obj = parse_date_safe(date_str)
    #         if not date_obj:
    #             raise ValueError("Unrecognized date format")

    #         # Parse filter dates
    #         start_date_obj = parse_date_safe(start_date) if start_date else None
    #         end_date_obj = parse_date_safe(end_date) if end_date else None

    #         # Check start and end range
    #         if start_date_obj and date_obj < start_date_obj:
    #             return False
    #         if end_date_obj and date_obj > end_date_obj:
    #             return False

    #         return True

    #     except Exception as e:
    #         # print(f"Warning: Could not parse date '{date_str}'. Error: {str(e)}")
    #         return True




    # def is_date_in_range(date_str, start_date=None, end_date=None):

    #     def to_datetime(value):
    #         if value is None:
    #             return None
    #         if isinstance(value, datetime):
    #             return value.replace(tzinfo=None)  # Remove timezone info
    #         if isinstance(value, tuple):
    #             return datetime(*value)
    #         if isinstance(value, str):
    #             try:
    #                 # Try ISO format
    #                 return datetime.fromisoformat(value).replace(tzinfo=None)
    #             except ValueError:
    #                 try:
    #                     # Try 'Thu May 22 11:50:57 2025'
    #                     return datetime.strptime(value, '%a %b %d %H:%M:%S %Y')
    #                 except ValueError:
    #                     try:
    #                         # Try comma-separated string like '2025, 1, 15, 0, 0'
    #                         parts = [int(x.strip()) for x in value.split(',')]
    #                         return datetime(*parts)
    #                     except Exception as e:
    #                         raise ValueError(f"Cannot parse string date: {value}. Error: {e}")
    #         raise ValueError(f"Unsupported date format: {value}")

    #     if not date_str or (start_date is None and end_date is None):
    #         return True

    #     try:
    #         date_obj = to_datetime(date_str)
    #         start_date_obj = to_datetime(start_date)
    #         end_date_obj = to_datetime(end_date)

    #         if start_date_obj and start_date_obj > date_obj:
    #             return False
    #         if end_date_obj and end_date_obj < date_obj:
    #             return False

    #         return True
    #     except Exception as e:
    #         print(f"Warning: Could not parse date '{date_str}'. Error: {str(e)}")
    #         return True


    # def is_date_in_range(date_str, start_date=None, end_date=None):
    #   def to_datetime(value):
    #       if value is None:
    #           return None
    #       if isinstance(value, datetime):
    #           return value
    #       if isinstance(value, tuple):
    #           return datetime(*value)
    #       if isinstance(value, str):
    #           try:
    #               # Try ISO format
    #               return datetime.fromisoformat(value)
    #           except ValueError:
    #               try:
    #                   # Try 'Fri Oct 11 07:31:12 2024'
    #                   return datetime.strptime(value, '%a %b %d %H:%M:%S %Y')
    #               except ValueError:
    #                   try:
    #                       # Try comma-separated string like '2025, 1, 15, 0, 0'
    #                       parts = [int(x.strip()) for x in value.split(',')]
    #                       return datetime(*parts)
    #                   except Exception as e:
    #                       raise ValueError(f"Cannot parse string date: {value}. Error: {e}")
    #       raise ValueError(f"Unsupported date format: {value}")

    #   if not date_str or (start_date is None and end_date is None):
    #       return True

    #   try:
    #       date_obj = to_datetime(date_str)
    #       start_date_obj = to_datetime(start_date)
    #       end_date_obj = to_datetime(end_date)

    #       if start_date_obj and start_date_obj > date_obj:
    #           return False
    #       if end_date_obj and end_date_obj < date_obj:
    #           return False

    #       return True
    #   except Exception as e:
    #       print(f"Warning: Could not parse date '{date_str}'. Error: {str(e)}")
    #       return True

    for count,query in enumerate(queries):
      for query_text, num_of_slides in query.items():
        # Use if you want to retrieve slides from some specific PPTs
        if folder_names:
            all_data = collection.get(include=['embeddings', 'documents', 'metadatas'])
            filtered_data = {
                'embeddings': [],
                'documents': [],
                'metadatas': [],
                'ids': []
            }
            new_filtered_data = {
                'embeddings': [],
                'documents': [],
                'metadatas': [],
                'ids': []
            }
            for embedding, document, metadata, ids in zip(all_data['embeddings'], all_data['documents'], all_data['metadatas'], all_data['ids']):
                # # Apply date filters
                # creation_date_valid = is_date_in_range(
                #     metadata.get('creation_date'), creation_start, creation_end
                # )

                # modification_date_valid = is_date_in_range(
                #     metadata.get('last_modified_date'), modification_start, modification_end
                # )

                # # Skip if the document doesn't match date filters
                # if not (creation_date_valid and modification_date_valid):
                #     continue

                text_content, table_content, Image_summary_content = separate_content(document)
                if len(text_content) > 150:
                    filtered_data['embeddings'].append(embedding)
                    filtered_data['documents'].append(document)
                    filtered_data['metadatas'].append(metadata)
                    filtered_data['ids'].append(ids)
            all_data = filtered_data
            
            # print('Extracting folders....')
            # print(all_data['metadatas'])
            # Extract folders at index 5 from the file_path
            # all_metadata_folders = [
            #     s['file_path'].split('/')[6]
            #     for s in all_data['metadatas']
            #     if 'file_path' in s and len(s['file_path'].split('/')) > 5  # ensure index 5 exists
            # ]

            all_metadata_folders = [s['file_path'].split('/')[6] for s in all_data['metadatas'] ] 

            # print("All extracted metadata folders:", all_metadata_folders)

            # Initialize new data dictionary
            # new_filtered_data = {
            #     'embeddings': [],
            #     'documents': [],
            #     'metadatas': [],
            #     'ids': []
            # }

            # Filter entries based on matching folder names
            for i, metadata_folder_name in enumerate(all_metadata_folders):
                # if metadata_folder_name in folder_names:
                    # print(f"Matched folder: {metadata_folder_name} (file: {all_data['metadatas'][i]['file_path']})")
                if all_data['metadatas'][i]['file_id'] in folder_names:
                    new_filtered_data['embeddings'].append(all_data['embeddings'][i])
                    new_filtered_data['documents'].append(all_data['documents'][i])
                    new_filtered_data['metadatas'].append(all_data['metadatas'][i])
                    new_filtered_data['ids'].append(all_data['ids'][i])

            # Replace old data with filtered data
            all_data = new_filtered_data

            print("\nNumber of filtered records:", len(all_data['ids']))

        # Normally, executes from here
        else:
            all_data = collection.get(include=['embeddings', 'documents', 'metadatas'])
            filtered_data = {
                'embeddings': [],
                'documents': [],
                'metadatas': [],
                'ids': []
            }

            for embedding, document, metadata, ids in zip(all_data['embeddings'], all_data['documents'], all_data['metadatas'], all_data['ids']):
                # Apply date filters
                # creation_date_valid = is_date_in_range(
                #     metadata.get('creation_date'), creation_start, creation_end
                # )

                # modification_date_valid = is_date_in_range(
                #     metadata.get('last_modified_date'), modification_start, modification_end
                # )

                # # Skip if the document doesn't match date filters
                # if not (creation_date_valid and modification_date_valid):
                #     continue

                text_content, table_content, Image_summary_content = separate_content(document)
                if len(text_content) > 150:
                    filtered_data['embeddings'].append(embedding)
                    filtered_data['documents'].append(document)
                    filtered_data['metadatas'].append(metadata)
                    filtered_data['ids'].append(ids)
            all_data = filtered_data
            print("Filtered records:", len(all_data['ids']))
            print("\n")

        # Skip further processing if no documents match the criteria
        if len(all_data['embeddings']) == 0:
            #print("No documents found matching the specified date range criteria")
            continue

        embeddings = np.array(all_data['embeddings']).astype('float32')

        # To normalize the embeddings
        if normalize:
            if embeddings.ndim == 1:
                embeddings = embeddings / np.linalg.norm(embeddings)
            else:
                embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        dimension = embeddings.shape[1]

        # Initialize the index
        if use_hnsw:
            M = 16
            index = faiss.IndexHNSWFlat(dimension, M)
            index.hnsw.efConstruction = 40
            index.hnsw.efSearch = 32
        else:
            index = faiss.IndexFlatL2(dimension)

        index.add(embeddings)

        # Getting embeddings for the query
        query_embedding = hf_model.encode(query_text)
        if normalize:
            query_embedding = query_embedding / np.linalg.norm(query_embedding)

        query_embedding = query_embedding.reshape(1, -1)

        if query_embedding.shape[1] != dimension:
            print(f"Error: Query embedding dimension ({query_embedding.shape[1]}) does not match index dimension ({dimension}).")
            continue

        # Querying the database, using the query, to retrieve slides
        try:
            distances, indices = index.search(query_embedding.astype('float32'), min(num_of_slides * 6, len(embeddings)))
        except Exception as e:
            print(f"Error during search: {str(e)}")
            continue

        # Filtering the results based on relevance of different elements
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            document = all_data['documents'][idx]
            metadata = all_data['metadatas'][idx]
            ids = all_data['ids'][idx]
            text_content, table_content, Image_summary_content = separate_content(document)
            text_relevance_score = get_relevance_score(query_text, text_content)
            table_relevance_score = get_relevance_score(query_text, table_content)
            Image_summary_relevance_score = get_relevance_score(query_text, Image_summary_content)

            # Calculating the combined score, giving different weights to different sections
            similarity_score = 1 / (1 + distance)
            similarity_score = (similarity_score - 0.5)*2

            alpha = 0.3
            text_weight = 0.6
            table_weight = 0.2
            Image_summary_weight = 0.2

            relevance_score = (text_weight)*(text_relevance_score) + (table_weight)*(table_relevance_score) + (Image_summary_weight)*(Image_summary_relevance_score)

            combined_score = alpha * relevance_score + (1 - alpha) * similarity_score

            # Storing the results
            results.append({
                'ids': ids,
                'document': document,
                'metadata': metadata,
                'distance': distance,
                'length': len(text_content),
                'text_relevance_score': text_relevance_score,
                'table_relevance_score': table_relevance_score,
                'Image_summary_relevance_score': Image_summary_relevance_score,
                'similarity_score': similarity_score,
                'relevance_score': relevance_score,
                'combined_score': combined_score,
                'result_type': "results"
            })

        # Filtering out the slides that are too similar
        results = [r for r in results if r['ids'] not in excluded_files]
        results.sort(key=lambda x: x['combined_score'], reverse=True)
        # print("results: ", results[0]['metadata'])
        image_paths = {}
        for r in results:
            full_file_path = r['metadata']['filename']
            file_id= r['metadata']['file_id']
            base_filename = os.path.basename(full_file_path)
            base_filename_no_ext = os.path.splitext(base_filename)[0]
            slide_number = r['metadata']['slide_number']
            file_path = f"{v2_ppt_data_path}/FID{file_id}/slide_{slide_number}.png"
            image_paths[file_path] = r['ids']

        #CHECK FILTER_UNIQUE_IMAGE
        unique_slides = filter_unique_Image(image_paths, used_hashes)
        results = [r for r in results if r['ids'] in unique_slides.values()]

        if tags and tags[count] != []:
            results = rerank_slides_based_on_tags_new(results, tags[count])
            reranked_results = results[:num_of_slides]
            reranked_results = sorted(reranked_results, key=lambda x: x['reranking_score'], reverse=True)
        else:
            for item in results:
                item['reranking_score'] = 0
            reranked_results = results[:num_of_slides]
            reranked_results = sorted(reranked_results, key=lambda x: x['combined_score'], reverse=True)

        for r in reranked_results:
            if 'metadata' in r and 'similar_ids' in r['metadata']:
                r['metadata']['similar_ids'] = r['metadata']['similar_ids'].split(',')

        # Extract unique similar slides
        similar_slides = {
            similar_id
            for r in reranked_results
            if 'metadata' in r and 'similar_ids' in r['metadata']
            for similar_id in r['metadata']['similar_ids']
        }

        # print(similar_slides)

        similar_results = []
        for target_id in similar_slides:
            # Skip if target_id is in excluded_files (low priority slides) 
          if target_id in excluded_files:
              continue 
          for i in range(len(all_data['ids'])):
            text_content, _, _ = separate_content(all_data['documents'][i])
            if all_data['ids'][i] == target_id and len(text_content) > 150:
                # Apply date filters to similar slides as well
                # metadata = all_data['metadatas'][i]
                # creation_date_valid = is_date_in_range(
                #     metadata.get('creation_date'), creation_start, creation_end
                # )

                # modification_date_valid = is_date_in_range(
                #     metadata.get('last_modified_date'), modification_start, modification_end
                # )

                # # Skip if the similar document doesn't match date filters
                # if not (creation_date_valid and modification_date_valid):
                #     continue

                # Construct a dictionary-like structure with relevant data
                data = {
                    "ids": all_data['ids'][i],
                    "document": all_data['documents'][i],
                    "metadata": all_data['metadatas'][i],
                    "distance": "NA",
                    "length" : len(all_data['documents'][i]),
                    "text_relevance_score": "NA",
                    "table_relevance_score": "NA",
                    "Image_summary_relevance_score": "NA",
                    "similarity_score": "NA",
                    "relevance_score": "NA",
                    "combined_score": "NA",
                    "reranking_score" : "NA",
                    "final_score" : "NA",
                    "result_type": "similar_results"
                }
                similar_results.append(data)
                break
        # print(len(similar_results))
        # print(similar_results)

        image_paths = {}
        for r in similar_results:
            full_file_path = r['metadata']['filename']
            file_id= r['metadata']['file_id']
            base_filename = os.path.basename(full_file_path)
            base_filename_no_ext = os.path.splitext(base_filename)[0]
            slide_number = r['metadata']['slide_number']
            slide_number = slide_number
            file_path = f"{v2_ppt_data_path}/FID{file_id}/slide_{slide_number}.png"
            image_paths[file_path] = r['ids']

        unique_similar_slides = filter_unique_Image(image_paths, used_hashes)
        similar_results = [r for r in similar_results if r['ids'] in unique_similar_slides.values()]

        no_of_slides = min(len(similar_results),10)

        if tags and tags[count] != []:
            similar_results = rerank_slides_based_on_tags_new(similar_results, tags[count])
            reranked_similar_results = similar_results[:no_of_slides]
            reranked_similar_results = sorted(reranked_similar_results, key=lambda x: x['reranking_score'], reverse=True)
        else:
            # Fixed the variable name error here (current_results -> similar_results)
            for item in similar_results:
                item['reranking_score'] = 0
            reranked_similar_results = similar_results[:no_of_slides]
            reranked_similar_results = sorted(reranked_similar_results, key=lambda x: x['combined_score'], reverse=True)

        result_types = ["results", "similar_results"]
        combined_results = {"results": reranked_results, "similar_results": reranked_similar_results}
        # print(len(combined_results['results']))

        # Print and collect the best results for the current result type
        no_of_similar_slides = len(combined_results['similar_results'])
        slide_counts.append([num_of_slides,no_of_similar_slides])
        print(f"No of similar results - {no_of_similar_slides}")
        for result_type in result_types:
            print(f"Result Type: {result_type}")
            current_results = combined_results[result_type]
            print(f"Current Results: {len(current_results)}")
            for i, result in enumerate(current_results):
                excluded_files.add(result['ids'])
                filename = result['metadata']['filename']
                slide_number = result['metadata']['slide_number']
                creation_date = result['metadata'].get('creation_date', 'Not available')
                modified_date = result['metadata'].get('last_modified_date', 'Not available')

                # print(f"\nResult {i+1} for query: '{query_text}' ({result_type})")
                # print(f"Filename: {filename}")
                # print(f"Slide Number: {slide_number}")
                # print(f"Creation Date: {creation_date}")
                # print(f"Last Modified Date: {modified_date}")
                # print(f"Distance: {result['distance'] if isinstance(result['distance'], (int, float)) else result['distance']}")
                # print(f"Length : {result['length']}")
                # print(f"Text Relevance Score: {result['text_relevance_score']:.4f}" if isinstance(result['text_relevance_score'], (int, float)) else f"Text Relevance Score: {result['text_relevance_score']}")
                # print(f"Table Relevance Score: {result['table_relevance_score']:.4f}" if isinstance(result['table_relevance_score'], (int, float)) else f"Table Relevance Score: {result['table_relevance_score']}")
                # print(f"Image Summary Relevance Score: {result['Image_summary_relevance_score']:.4f}" if isinstance(result['Image_summary_relevance_score'], (int, float)) else f"Image Summary Relevance Score: {result['Image_summary_relevance_score']}")
                # print(f"Relevance Score: {result['relevance_score']:.4f}" if isinstance(result['relevance_score'], (int, float)) else f"Relevance Score: {result['relevance_score']}")
                # print(f"Combined Score: {result['combined_score']:.4f}" if isinstance(result['combined_score'], (int, float)) else f"Combined Score: {result['combined_score']}")
                # print(f"Reranking Score: {result['reranking_score']:.4f}" if isinstance(result['reranking_score'], (int, float)) else f"Reranking Score: {result['reranking_score']}")
                # print(f"Content: {result['document'][:100]}...")  # Print first 100 characters
                # print("-" * 50)
                all_results.append(result)

    faiss_results = {
        'documents': [r['document'] for r in all_results],
        'metadatas': [r['metadata'] for r in all_results],
        'distances': [r['distance'] for r in all_results],
        'text_relevance_scores': [r['text_relevance_score'] for r in all_results],
        'table_relevance_scores': [r['table_relevance_score'] for r in all_results],
        'images_summary_relevance_scores': [r.get('images_summary_relevance_score', 0.0) for r in all_results],
        # 'images_summary_relevance_scores': [r['images_summary_relevance_score'] for r in all_results],
        'relevance_scores': [r['relevance_score'] for r in all_results],
        'combined_scores': [r['combined_score'] for r in all_results],
        'reranking_scores': [r['reranking_score'] for r in all_results],
        'result_types': [r['result_type'] for r in all_results],
        'slide_counts' : slide_counts
        #'excluded_files': excluded_files
    }

    # Prepare the response
    #print(slide_counts)

#########################################################################
# Get data from faiss_results
    result_types = faiss_results['result_types']   # ['results', 'similar_results', ...]
    metadatas = faiss_results['metadatas']

    json_output = []
    result_index = 0
    number = 0

    for count, query in enumerate(queries):
        for query_text, num_of_slides in query.items():
            query_result = {
                "query": str(query_text).strip(),
                "results": []
            }
            
            # Only process main results for this query
            main_slides_added = 0
            
            # Skip through results until we find main results for this query
            while result_index < len(metadatas) and main_slides_added < num_of_slides:
                # Only include main results (skip similar results)
                if result_index < len(result_types) and result_types[result_index] == "results":
                    metadata = metadatas[result_index]
                    slide_info = {
                        "id": number + 1,
                        "slideNumber": metadata['slide_number'],
                        "pptName": metadata['file_path']
                    }
                    number += 1
                    query_result["results"].append(slide_info)
                    main_slides_added += 1
                
                result_index += 1
            
            json_output.append(query_result)

    # Save to a JSON file
    os.makedirs(output_files_path, exist_ok=True)
    with open(f"{output_files_path}/slide_composition.json", "w") as f:
        json.dump(json_output, f, indent=4)

    # Get total slides from main results only
    total_slides = sum(len(q["results"]) for q in json_output)

    # Create PDF with main results only
    # Get slide_counts from faiss_results
    slide_counts = faiss_results.get('slide_counts', [])

    # Updated defensive check before combining slides
    if not faiss_results or not faiss_results.get("metadatas") or not faiss_results.get("result_types"):
        print("No documents found matching the specified date range criteria") 
        return None  # or raise HTTPException(status_code=404, detail="No matching slides found.")


    pdf = combine_pdf_slides(
        faiss_results,
        v2_ppt_data_path,
        output_files_path,
        slide_counts
    ) 

    print(f"\nJSON created with {total_slides} main result slides")
    
    #########################################################################
    # Save retrieved_slides.json (full details for only PDF slides)
    retrieved_slides = []
    slide_index = 0

    for query in json_output:
        query_entry = {
            "query": query["query"],
            "results": []
        }
        for result in query["results"]:
            slide_index += 1

            # Lookup full result details
            r = None
            for item in all_results:
                if str(item["metadata"].get("slide_number")) == str(result["slideNumber"]) and \
                   str(item["metadata"].get("file_path")) == str(result["pptName"]) and \
                   item["result_type"] == "results":
                    r = item
                    break

            if r:
                query_entry["results"].append({
                    "index": slide_index,
                    "slideNumber": result["slideNumber"],
                    "pptName": result["pptName"],
                    "metadata": r.get("metadata", {}),
                    "slideContent": r.get("document", ""),
                    # "scores": {
                    #     "distance": r.get("distance"),
                    #     "length": r.get("length"),
                    #     "text_relevance_score": r.get("text_relevance_score"),
                    #     "table_relevance_score": r.get("table_relevance_score"),
                    #     "Image_summary_relevance_score": r.get("Image_summary_relevance_score"),
                    #     "similarity_score": r.get("similarity_score"),
                    #     "relevance_score": r.get("relevance_score"),
                    #     "combined_score": r.get("combined_score"),
                    #     "reranking_score": r.get("reranking_score"),
                    #     "result_type": r.get("result_type"),
                    # }
                })

        retrieved_slides.append(query_entry)


    # Save JSON file to your fixed path
    retrieved_json_path = r"C:\\Users\\Administrator\\Desktop\\AlgoCreator_Chatbot\\AlgoCreator_Chatbot\\RAG\\tools\\JSON's\\retrieved_slides.json"
    

    # Ensure directory exists before saving
    os.makedirs(os.path.dirname(retrieved_json_path), exist_ok=True)

    with open(retrieved_json_path, "w", encoding="utf-8") as f:
        json.dump(retrieved_slides, f, indent=4, ensure_ascii=False)

    print(f"Retrieved slides JSON saved at: {retrieved_json_path}")



    return pdf


#########################################################################

    # # Print the results in a tabular format
    # result_index = -1
    # json_output = []

    # number = 0

    # for count, query in enumerate(queries):
    #     for query_text, num_of_slides in query.items():
    #         query_result = {
    #             "query": str(query_text).strip(),
    #             "results": []
    #         }

    #         for _ in range(num_of_slides):
    #             result_index += 1
    #             if result_index < len(faiss_results['metadatas']):
    #                 metadata = faiss_results['metadatas'][result_index]
    #                 slide_info = {
    #                     "id": number + 1,
    #                     "slideNumber": metadata['slide_number'],
    #                     "pptName": metadata['file_path']
    #                 }
    #                 number += 1
    #                 query_result["results"].append(slide_info)

    #         json_output.append(query_result)

    # # Save to a JSON file
    # with open(f"{output_files_path}/slide_composition.json", "w") as f:
    #     json.dump(json_output, f, indent=4)

    # # print("README.md file has been created.")

    # # pdf = combine_pdf_slides(faiss_results, v2_persist_directory, output_files_path)
    # total_slides = sum(len(q["results"]) for q in json_output)

    # pdf = combine_pdf_slides(
    #     faiss_results,
    #     v2_ppt_data_path,
    #     output_files_path,
    #     num_slides_to_include=total_slides
    # )
    # return pdf 

##########################################################################################
#Code for V4 starts from here
##########################################################################################

def query_chroma_v4(collection, queries: List[Dict], use_hnsw: bool = True, normalize: bool = True,
                 folder_names: List[str] = None, tags: List[str] = None, date_filter: dict = None):
    
    creation_start = date_filter.get("creation_start") if date_filter else None
    creation_end = date_filter.get("creation_end") if date_filter else None
    modification_start = date_filter.get("modification_start") if date_filter else None
    modification_end = date_filter.get("modification_end") if date_filter else None
    all_results = []
    best_result = []
    excluded_files = set()
    used_hashes = set()
    unique_items = []
    slide_counts = []
    removable_slides = remove_low_priority_slides_d() #using static for now 
    for item in removable_slides:
      excluded_files.add(item)
    print("Excluded files: ", excluded_files) 


    def is_date_in_range(date_str, start_date=None, end_date=None):

        def to_datetime(value):
            if value is None:
                return None
            if isinstance(value, datetime):
                return value.replace(tzinfo=None)  # Remove timezone info
            if isinstance(value, tuple):
                return datetime(*value)
            if isinstance(value, str):
                try:
                    # Try ISO format
                    return datetime.fromisoformat(value).replace(tzinfo=None)
                except ValueError:
                    try:
                        # Try 'Thu May 22 11:50:57 2025'
                        return datetime.strptime(value, '%a %b %d %H:%M:%S %Y')
                    except ValueError:
                        try:
                            # Try comma-separated string like '2025, 1, 15, 0, 0'
                            parts = [int(x.strip()) for x in value.split(',')]
                            return datetime(*parts)
                        except Exception as e:
                            raise ValueError(f"Cannot parse string date: {value}. Error: {e}")
            raise ValueError(f"Unsupported date format: {value}")

        if not date_str or (start_date is None and end_date is None):
            return True

        try:
            date_obj = to_datetime(date_str)
            start_date_obj = to_datetime(start_date)
            end_date_obj = to_datetime(end_date)

            if start_date_obj and start_date_obj > date_obj:
                return False
            if end_date_obj and end_date_obj < date_obj:
                return False

            return True
        except Exception as e:
            print(f"Warning: Could not parse date '{date_str}'. Error: {str(e)}")
            return True

    for count,query in enumerate(queries):
      for query_text, num_of_slides in query.items():
        # Use if you want to retrieve slides from some specific PPTs
        if folder_names:
            all_data = collection.get(include=['embeddings', 'documents', 'metadatas'])
            filtered_data = {
                'embeddings': [],
                'documents': [],
                'metadatas': [],
                'ids': []
            }
            new_filtered_data = {
                'embeddings': [],
                'documents': [],
                'metadatas': [],
                'ids': []
            }
            for embedding, document, metadata, ids in zip(all_data['embeddings'], all_data['documents'], all_data['metadatas'], all_data['ids']):
                # Apply date filters
                creation_date_valid = is_date_in_range(
                    metadata.get('creation_date'), creation_start, creation_end
                )

                modification_date_valid = is_date_in_range(
                    metadata.get('last_modified_date'), modification_start, modification_end
                )

                # Skip if the document doesn't match date filters
                if not (creation_date_valid and modification_date_valid):
                    continue

                text_content, table_content, Image_summary_content = separate_content(document)
                if len(text_content) > 150:
                    filtered_data['embeddings'].append(embedding)
                    filtered_data['documents'].append(document)
                    filtered_data['metadatas'].append(metadata)
                    filtered_data['ids'].append(ids)
            all_data = filtered_data
            
            # print('Extracting folders....')
            # print(all_data['metadatas'])
            # Extract folders at index 5 from the file_path
            # all_metadata_folders = [
            #     s['file_path'].split('/')[6]
            #     for s in all_data['metadatas']
            #     if 'file_path' in s and len(s['file_path'].split('/')) > 5  # ensure index 5 exists
            # ]

            all_metadata_folders = [s['file_path'].split('/')[6] for s in all_data['metadatas'] ] 

            # print("All extracted metadata folders:", all_metadata_folders)

            # Filter entries based on matching folder names
            for i, metadata_folder_name in enumerate(all_metadata_folders):
                if metadata_folder_name in folder_names:
                    # print(f"Matched folder: {metadata_folder_name} (file: {all_data['metadatas'][i]['file_path']})")
                    new_filtered_data['embeddings'].append(all_data['embeddings'][i])
                    new_filtered_data['documents'].append(all_data['documents'][i])
                    new_filtered_data['metadatas'].append(all_data['metadatas'][i])
                    new_filtered_data['ids'].append(all_data['ids'][i])

            # Replace old data with filtered data
            all_data = new_filtered_data

            print("\nNumber of filtered records:", len(all_data['ids']))

        # Normally, executes from here
        else:
            all_data = collection.get(include=['embeddings', 'documents', 'metadatas'])
            filtered_data = {
                'embeddings': [],
                'documents': [],
                'metadatas': [],
                'ids': []
            }

            for embedding, document, metadata, ids in zip(all_data['embeddings'], all_data['documents'], all_data['metadatas'], all_data['ids']):
                # Apply date filters
                creation_date_valid = is_date_in_range(
                    metadata.get('creation_date'), creation_start, creation_end
                )

                modification_date_valid = is_date_in_range(
                    metadata.get('last_modified_date'), modification_start, modification_end
                )

                # Skip if the document doesn't match date filters
                if not (creation_date_valid and modification_date_valid):
                    continue

                text_content, table_content, Image_summary_content = separate_content(document)
                if len(text_content) > 150:
                    filtered_data['embeddings'].append(embedding)
                    filtered_data['documents'].append(document)
                    filtered_data['metadatas'].append(metadata)
                    filtered_data['ids'].append(ids)
            all_data = filtered_data
            print("Filtered records:", len(all_data['ids']))
            print("\n")

        # Skip further processing if no documents match the criteria
        if len(all_data['embeddings']) == 0:
            #print("No documents found matching the specified date range criteria")
            continue

        embeddings = np.array(all_data['embeddings']).astype('float32')

        # To normalize the embeddings
        if normalize:
            if embeddings.ndim == 1:
                embeddings = embeddings / np.linalg.norm(embeddings)
            else:
                embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        dimension = embeddings.shape[1]

        # Initialize the index
        if use_hnsw:
            M = 16
            index = faiss.IndexHNSWFlat(dimension, M)
            index.hnsw.efConstruction = 40
            index.hnsw.efSearch = 32
        else:
            index = faiss.IndexFlatL2(dimension)

        index.add(embeddings)

        # Getting embeddings for the query
        query_embedding = hf_model.encode(query_text)
        if normalize:
            query_embedding = query_embedding / np.linalg.norm(query_embedding)

        query_embedding = query_embedding.reshape(1, -1)

        if query_embedding.shape[1] != dimension:
            print(f"Error: Query embedding dimension ({query_embedding.shape[1]}) does not match index dimension ({dimension}).")
            continue

        # Querying the database, using the query, to retrieve slides
        try:
            distances, indices = index.search(query_embedding.astype('float32'), min(num_of_slides * 6, len(embeddings)))
        except Exception as e:
            print(f"Error during search: {str(e)}")
            continue

        # Filtering the results based on relevance of different elements
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            document = all_data['documents'][idx]
            metadata = all_data['metadatas'][idx]
            ids = all_data['ids'][idx]
            text_content, table_content, Image_summary_content = separate_content(document)
            text_relevance_score = get_relevance_score(query_text, text_content)
            table_relevance_score = get_relevance_score(query_text, table_content)
            Image_summary_relevance_score = get_relevance_score(query_text, Image_summary_content)

            # Calculating the combined score, giving different weights to different sections
            similarity_score = 1 / (1 + distance)
            similarity_score = (similarity_score - 0.5)*2

            alpha = 0.3
            text_weight = 0.6
            table_weight = 0.2
            Image_summary_weight = 0.2

            relevance_score = (text_weight)*(text_relevance_score) + (table_weight)*(table_relevance_score) + (Image_summary_weight)*(Image_summary_relevance_score)

            combined_score = alpha * relevance_score + (1 - alpha) * similarity_score

            # Storing the results
            results.append({
                'ids': ids,
                'document': document,
                'metadata': metadata,
                'distance': distance,
                'length': len(text_content),
                'text_relevance_score': text_relevance_score,
                'table_relevance_score': table_relevance_score,
                'Image_summary_relevance_score': Image_summary_relevance_score,
                'similarity_score': similarity_score,
                'relevance_score': relevance_score,
                'combined_score': combined_score,
                'result_type': "results"
            })

        # Filtering out the slides that are too similar
        results = [r for r in results if r['ids'] not in excluded_files]
        results.sort(key=lambda x: x['combined_score'], reverse=True)
        # print("results: ", results[0]['metadata'])
        image_paths = {}
        for r in results:
            full_file_path = r['metadata']['filename']
            file_id= r['metadata']['file_id']
            base_filename = os.path.basename(full_file_path)
            base_filename_no_ext = os.path.splitext(base_filename)[0]
            slide_number = r['metadata']['slide_number']
            file_path = f"{v2_ppt_data_path}/FID{file_id}/slide_{slide_number}.png"
            image_paths[file_path] = r['ids']

        #CHECK FILTER_UNIQUE_IMAGE
        unique_slides = filter_unique_Image(image_paths, used_hashes)
        results = [r for r in results if r['ids'] in unique_slides.values()]

        if tags and tags[count] != []:
            results = rerank_slides_based_on_tags_new(results, tags[count])
            reranked_results = results[:num_of_slides]
            reranked_results = sorted(reranked_results, key=lambda x: x['reranking_score'], reverse=True)
        else:
            for item in results:
                item['reranking_score'] = 0
            reranked_results = results[:num_of_slides]
            reranked_results = sorted(reranked_results, key=lambda x: x['combined_score'], reverse=True)

        for r in reranked_results:
            if 'metadata' in r and 'similar_ids' in r['metadata']:
                r['metadata']['similar_ids'] = r['metadata']['similar_ids'].split(',')

        # Extract unique similar slides
        similar_slides = {
            similar_id
            for r in reranked_results
            if 'metadata' in r and 'similar_ids' in r['metadata']
            for similar_id in r['metadata']['similar_ids']
        }

        # print(similar_slides)

        similar_results = []
        for target_id in similar_slides:
            # Skip if target_id is in excluded_files (low priority slides) 
          if target_id in excluded_files:
              continue 
          for i in range(len(all_data['ids'])):
            text_content, _, _ = separate_content(all_data['documents'][i])
            if all_data['ids'][i] == target_id and len(text_content) > 150:
                # Apply date filters to similar slides as well
                metadata = all_data['metadatas'][i]
                creation_date_valid = is_date_in_range(
                    metadata.get('creation_date'), creation_start, creation_end
                )

                modification_date_valid = is_date_in_range(
                    metadata.get('last_modified_date'), modification_start, modification_end
                )

                # Skip if the similar document doesn't match date filters
                if not (creation_date_valid and modification_date_valid):
                    continue

                # Construct a dictionary-like structure with relevant data
                data = {
                    "ids": all_data['ids'][i],
                    "document": all_data['documents'][i],
                    "metadata": all_data['metadatas'][i],
                    "distance": "NA",
                    "length" : len(all_data['documents'][i]),
                    "text_relevance_score": "NA",
                    "table_relevance_score": "NA",
                    "Image_summary_relevance_score": "NA",
                    "similarity_score": "NA",
                    "relevance_score": "NA",
                    "combined_score": "NA",
                    "reranking_score" : "NA",
                    "final_score" : "NA",
                    "result_type": "similar_results"
                }
                similar_results.append(data)
                break
        # print(len(similar_results))
        # print(similar_results)

        image_paths = {}
        for r in similar_results:
            full_file_path = r['metadata']['filename']
            file_id= r['metadata']['file_id']
            base_filename = os.path.basename(full_file_path)
            base_filename_no_ext = os.path.splitext(base_filename)[0]
            slide_number = r['metadata']['slide_number']
            slide_number = slide_number
            file_path = f"{v2_ppt_data_path}/FID{file_id}/slide_{slide_number}.png"
            image_paths[file_path] = r['ids']

        unique_similar_slides = filter_unique_Image(image_paths, used_hashes)
        similar_results = [r for r in similar_results if r['ids'] in unique_similar_slides.values()]

        no_of_slides = min(len(similar_results),10)

        if tags and tags[count] != []:
            similar_results = rerank_slides_based_on_tags_new(similar_results, tags[count])
            reranked_similar_results = similar_results[:no_of_slides]
            reranked_similar_results = sorted(reranked_similar_results, key=lambda x: x['reranking_score'], reverse=True)
        else:
            # Fixed the variable name error here (current_results -> similar_results)
            for item in similar_results:
                item['reranking_score'] = 0
            reranked_similar_results = similar_results[:no_of_slides]
            reranked_similar_results = sorted(reranked_similar_results, key=lambda x: x['combined_score'], reverse=True)

        result_types = ["results", "similar_results"]
        combined_results = {"results": reranked_results, "similar_results": reranked_similar_results}
        # print(len(combined_results['results']))

        # Print and collect the best results for the current result type
        no_of_similar_slides = len(combined_results['similar_results'])
        slide_counts.append([num_of_slides,no_of_similar_slides])
        print(f"No of similar results - {no_of_similar_slides}")
        for result_type in result_types:
            print(f"Result Type: {result_type}")
            current_results = combined_results[result_type]
            print(f"Current Results: {len(current_results)}")
            for i, result in enumerate(current_results):
                excluded_files.add(result['ids'])
                filename = result['metadata']['filename']
                slide_number = result['metadata']['slide_number']
                creation_date = result['metadata'].get('creation_date', 'Not available')
                modified_date = result['metadata'].get('last_modified_date', 'Not available')

                # print(f"\nResult {i+1} for query: '{query_text}' ({result_type})")
                # print(f"Filename: {filename}")
                # print(f"Slide Number: {slide_number}")
                # print(f"Creation Date: {creation_date}")
                # print(f"Last Modified Date: {modified_date}")
                # print(f"Distance: {result['distance'] if isinstance(result['distance'], (int, float)) else result['distance']}")
                # print(f"Length : {result['length']}")
                # print(f"Text Relevance Score: {result['text_relevance_score']:.4f}" if isinstance(result['text_relevance_score'], (int, float)) else f"Text Relevance Score: {result['text_relevance_score']}")
                # print(f"Table Relevance Score: {result['table_relevance_score']:.4f}" if isinstance(result['table_relevance_score'], (int, float)) else f"Table Relevance Score: {result['table_relevance_score']}")
                # print(f"Image Summary Relevance Score: {result['Image_summary_relevance_score']:.4f}" if isinstance(result['Image_summary_relevance_score'], (int, float)) else f"Image Summary Relevance Score: {result['Image_summary_relevance_score']}")
                # print(f"Relevance Score: {result['relevance_score']:.4f}" if isinstance(result['relevance_score'], (int, float)) else f"Relevance Score: {result['relevance_score']}")
                # print(f"Combined Score: {result['combined_score']:.4f}" if isinstance(result['combined_score'], (int, float)) else f"Combined Score: {result['combined_score']}")
                # print(f"Reranking Score: {result['reranking_score']:.4f}" if isinstance(result['reranking_score'], (int, float)) else f"Reranking Score: {result['reranking_score']}")
                # print(f"Content: {result['document'][:100]}...")  # Print first 100 characters
                # print("-" * 50)
                all_results.append(result)

    faiss_results = {
        'documents': [r['document'] for r in all_results],
        'metadatas': [r['metadata'] for r in all_results],
        'distances': [r['distance'] for r in all_results],
        'text_relevance_scores': [r['text_relevance_score'] for r in all_results],
        'table_relevance_scores': [r['table_relevance_score'] for r in all_results],
        'images_summary_relevance_scores': [r.get('images_summary_relevance_score', 0.0) for r in all_results],
        # 'images_summary_relevance_scores': [r['images_summary_relevance_score'] for r in all_results],
        'relevance_scores': [r['relevance_score'] for r in all_results],
        'combined_scores': [r['combined_score'] for r in all_results],
        'reranking_scores': [r['reranking_score'] for r in all_results],
        'result_types': [r['result_type'] for r in all_results],
        'slide_counts' : slide_counts
        #'excluded_files': excluded_files
    }

    # Prepare the response
    #print(slide_counts)

    # Prepare slide metadata for API response
    slide_metadata = []
    for result in all_results:
        if result['result_type'] == "results":
            slide_metadata.append({
                "slide_id": result['ids'],
                "slide_summary": result['document'][:200],  # Or use a summary field if available
                "topic": result['metadata'].get("topic", "General"),
                "slide_number": result['metadata'].get("slide_number"),
                "ppt_name": result['metadata'].get("file_path")
            })
    
#########################################################################
    # Get data from faiss_results
    result_types = faiss_results['result_types']   # ['results', 'similar_results', ...]
    metadatas = faiss_results['metadatas']

    json_output = []
    result_index = 0
    number = 0

    for count, query in enumerate(queries):
        for query_text, num_of_slides in query.items():
            query_result = {
                "query": str(query_text).strip(),
                "results": []
            }
            
            # Only process main results for this query
            main_slides_added = 0
            
            # Skip through results until we find main results for this query
            while result_index < len(metadatas) and main_slides_added < num_of_slides:
                # Only include main results (skip similar results)
                if result_index < len(result_types) and result_types[result_index] == "results":
                    metadata = metadatas[result_index]
                    slide_info = {
                        "id": number + 1,
                        "slideNumber": metadata['slide_number'],
                        "pptName": metadata['file_path']
                    }
                    number += 1
                    query_result["results"].append(slide_info)
                    main_slides_added += 1
                
                result_index += 1
            
            json_output.append(query_result)

    # Save to a JSON file
    with open(f"{output_files_path}/slide_composition.json", "w") as f:
        json.dump(json_output, f, indent=4)

    # Get total slides from main results only
    total_slides = sum(len(q["results"]) for q in json_output)

    # Create PDF with main results only
    # Get slide_counts from faiss_results
    slide_counts = faiss_results.get('slide_counts', [])

    # Updated defensive check before combining slides
    if not faiss_results or not faiss_results.get("metadatas") or not faiss_results.get("result_types"):
        print("No documents found matching the specified date range criteria") 
        return None  # or raise HTTPException(status_code=404, detail="No matching slides found.")


    pdf = combine_pdf_slides(
        faiss_results,
        v2_ppt_data_path,
        output_files_path,
        slide_counts
    ) 

    print(f"\nJSON created with {total_slides} main result slides")
    #########################################################################
    # Save retrieved_slides.json (full details for only PDF slides)
    retrieved_slides = []
    slide_index = 0

    for query in json_output:
        query_entry = {
            "query": query["query"],
            "results": []
        }
        for result in query["results"]:
            slide_index += 1

            # Lookup full result details
            r = None
            for item in all_results:
                if str(item["metadata"].get("slide_number")) == str(result["slideNumber"]) and \
                   str(item["metadata"].get("file_path")) == str(result["pptName"]) and \
                   item["result_type"] == "results":
                    r = item
                    break

            if r:
                query_entry["results"].append({
                    "index": slide_index,
                    "slideNumber": result["slideNumber"],
                    "pptName": result["pptName"],
                    "metadata": r.get("metadata", {}),
                    "slideContent": r.get("document", ""),
                    "scores": {
                        "distance": r.get("distance"),
                        "length": r.get("length"),
                        "text_relevance_score": r.get("text_relevance_score"),
                        "table_relevance_score": r.get("table_relevance_score"),
                        "Image_summary_relevance_score": r.get("Image_summary_relevance_score"),
                        "similarity_score": r.get("similarity_score"),
                        "relevance_score": r.get("relevance_score"),
                        "combined_score": r.get("combined_score"),
                        "reranking_score": r.get("reranking_score"),
                        "result_type": r.get("result_type"),
                    }
                })

        retrieved_slides.append(query_entry)

    # Save JSON file to your fixed path
    retrieved_json_path = r"C:\\Users\\Administrator\\Desktop\\AlgoCreator_Chatbot\\AlgoCreator_Chatbot\\RAG\\tools\\JSON's\\retrieved_slides.json"

    # Ensure directory exists before saving
    os.makedirs(os.path.dirname(retrieved_json_path), exist_ok=True)

    with open(retrieved_json_path, "w", encoding="utf-8") as f:
        json.dump(retrieved_slides, f, indent=4, ensure_ascii=False)

    print(f"Retrieved slides JSON saved at: {retrieved_json_path}")
    
    return {
        "pdf_url": pdf,  # Path to generated PDF
        "slide_metadata": slide_metadata
    }


# Load all records from JSON
def load_and_process_json(file_path: str) -> List[Dict]:
    with open(file_path, "r") as f:
        data = json.load(f)
        return data if isinstance(data, list) else [data]

# Flatten all slide records
def flatten_slide_data(raw_data: List[Dict]) -> List[Dict]:
    flattened = []
    for file_data in raw_data:
        file_name = file_data.get("pptx_name", "unknown")
        file_id = file_data.get("file_id", "")
        slides = file_data.get("slide_details", [])
        file_path = file_data.get("pptx_path", "")
        creation_date = file_data.get("creation_date", "")
        modified_date = file_data.get("last_mod_date", "")

        for slide in slides:
            slide_number = slide.get("Slide_Number", 0)
            record_id = f"FID{file_id}_{file_name}_Slide_{slide_number}"

            combined_text = (
                f"Text:\n{slide.get('Text', '')}\n\n"
                f"Table Summary:\n{slide.get('Table Summary', '')}\n\n"
                f"Images Summary:\n{slide.get('Image Summary', '')}\n\n"
                f"Tags:\n{', '.join(slide.get('Tags associated', []))}"
            )

            metadata = {
                "file_id": file_id,
                "filename": file_name,
                "file_path": file_path,
                "slide_number": slide_number,
                "creation_date": creation_date,
                "last_modified_date": modified_date
            }

            flattened.append({
                "id": record_id,
                "text": combined_text,
                "metadata": metadata
            })
    return flattened

# Embed and store into ChromaDB
batch_size = 2

def embed_and_store(collection, data: List[Dict]):
    num_batches = len(data) // batch_size + (1 if len(data) % batch_size != 0 else 0)
    embedder = SentenceTransformer('intfloat/e5-large-v2')
    for i in tqdm(range(0, len(data), batch_size), desc="Processing batches", total=num_batches):
        batch = data[i:i + batch_size]
        
        texts = [item["text"] for item in batch]
        ids = [item["id"] for item in batch]
        metadatas = [item["metadata"] for item in batch]

        embeddings = embedder.encode(texts, normalize_embeddings=True)

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
    return collection

def main():
    # Step 1: Initialize the Chroma collection
    # collection_main = initialize_chroma(v2_persist_directory)

    chroma_client_main = initialize_chroma(v2_persist_directory)
    collection_main = chroma_client_main.get_or_create_collection("Slides")

    # Step 2: Check if the collection is empty and populate it if necessary
    if collection_main.count() == 0:
        # Main execution (From Scratch)
        for file in os.listdir(v2_json_files_path):
            file_path = os.path.join(v2_json_files_path, file)
            raw_data = load_and_process_json(file_path)
            flattened_data = flatten_slide_data(raw_data)
            collection_main = embed_and_store(collection_main, flattened_data)
    else:
        print(f"Found existing chromadb at {v2_persist_directory}")
    
    # Step 3: Define the queries, tags, and folder names
    queries = [
        {"Introduction to AlgoAnalytics - About us, our team, management, founders, offerings and expertise": 4}
    ]
    
    tags = [["AlgoAnalytics"]]
    folder_names = ['AlgoPPTOld', 'AlgoPPT']
    date_filter = None
    
    # Step 4: Run the query against Chroma
    # faiss_results = query_chroma(collection, queries, use_hnsw=True, normalize=True, folder_names=folder_names, tags=tags)

    # Step 5: Run the query against Chroma and return the PDF path
    pdf_path = query_chroma(collection, queries, use_hnsw=True, normalize=True, tags=tags, folder_names=folder_names, date_filter=date_filter)
    
    return pdf_path

# Entry point for the script
# if __name__ == "__main__":
#     pdf_path = main()
#     print(f"PDF path: {pdf_path}")

def run_retrieval_pipeline_v2(queries, tags, folder_names, date_filter):

    # collection = initialize_chroma(v2_persist_directory)

    chroma_client_v2 = initialize_chroma(v2_persist_directory)
    collection_v2 = chroma_client_v2.get_or_create_collection("Slides")

    if collection_v2.count()== 0:
    # Main execution (From Scratch)
        for file in os.listdir(v2_json_files_path):
            file_path = os.path.join(v2_json_files_path, file)
            raw_data = load_and_process_json(file_path)
            flattened_data = flatten_slide_data(raw_data)
            collection_v2 = embed_and_store(collection_v2, flattened_data)
            embed_and_store(collection_v2, flattened_data)
    else:
        print(f"Found existing chromadb at {v2_persist_directory} ")
    
    try:
        pdf_path = query_chroma(collection_v2, queries, use_hnsw=True, normalize=True, tags=tags, folder_names=folder_names,date_filter = date_filter)
    except ValueError as e:
        print(f"[Retrieval Error] {str(e)}")
        return None  # Indicates no valid slides to combine
    
    return pdf_path

def run_retrieval_pipeline_v4(queries, tags, folder_names, date_filter):
    # Initialize Chroma collection
    chroma_client_v2 = initialize_chroma(v2_persist_directory)
    collection_v2 = chroma_client_v2.get_or_create_collection("Slides")

    if collection_v2.count() == 0:
        # Main execution (From Scratch)
        for file in os.listdir(v2_json_files_path):
            file_path = os.path.join(v2_json_files_path, file)
            raw_data = load_and_process_json(file_path)
            flattened_data = flatten_slide_data(raw_data)
            collection_v2 = embed_and_store(collection_v2, flattened_data)
            embed_and_store(collection_v2, flattened_data)
    else:
        print(f"Found existing chromadb at {v2_persist_directory}")

    try:
        # Run the query and get the PDF path
        pdf_path = query_chroma_v4(
            collection_v2,
            queries,
            use_hnsw=True,
            normalize=True,
            tags=tags,
            folder_names=folder_names,
            date_filter=date_filter
        )
    except ValueError as e:
        print(f"[Retrieval Error] {str(e)}")
        return None

    # --- New: Collect slide metadata for all main results ---
    # Get all documents, metadatas, and IDs from the collection
    all_data = collection_v2.get(include=["documents", "metadatas"])
    slide_metadata = []

    for i in range(len(all_data["ids"])):
        slide_id = all_data["ids"][i]
        metadata = all_data["metadatas"][i]
        document = all_data["documents"][i]
        slide_summary = document[:200]  # Or use a summary field if available

        slide_metadata.append({
            "slide_id": slide_id,
            "slide_summary": slide_summary,
            "topic": metadata.get("topic", ""),
            "slide_number": metadata.get("slide_number", ""),
            "ppt_name": metadata.get("file_path", "")
        })

    # Optionally, filter slide_metadata to only those included in the PDF if needed

    return {
        "pdf_file_path": pdf_path,
        "slide_metadata": slide_metadata
    }
