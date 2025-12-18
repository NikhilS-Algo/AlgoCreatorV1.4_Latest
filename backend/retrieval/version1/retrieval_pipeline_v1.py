"""
    Data_Retrieval_Pipeline_From_Text_V2

    Long queries along with how many slides to retreive per pointer can be given

"""
##############################
# This has been added to resolve the issue of unsupported-version-of-sqlite3-chroma
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
##############################
from sentence_transformers import SentenceTransformer
from chromadb.utils import embedding_functions
# import streamlit as st

#for seperate content function
import re

#for calculate distance function
from itertools import combinations
import numpy as np

#to create chromadb
import json
from typing import List, Dict
from chromadb.config import Settings
import chromadb

#for main retreival function
import json
import fitz  # PyMuPDF
from PIL import Image
import imagehash
import io
import faiss
# import numpy as np
import torch
import os
import re
from PIL import Image
from typing import List, Dict
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch.nn.functional as F

#for combining pdf slides function
from pathlib import Path
import fitz
#import os
from typing import List, Dict


#for converting pdf to pptx
# import convertapi
# import base64
# import time


# Replace with your drive paths

# # key to convertapi from main account(shared)
# api_secret = 'secret_7UTWxZA3qckjwlwX'

from utils.constants import output_files_path, v1_base_dir, v1_json_files_path, v1_persist_directory
hf_model = SentenceTransformer('intfloat/e5-large-v2')
model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
relevance_model = AutoModelForSequenceClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

def combine_pdf_slides(faiss_results: Dict[str, List[Dict[str, str]]], base_dir: str, output_files_path: str):

    # Convert to Path objects
    base_dir = Path(base_dir)
    output_files_path = Path(output_files_path)

    slides = faiss_results['metadatas']

    pdf_pages = []

    for item in slides:
        ppt_name = item['filename'].replace('.pptx', '')
        slide_number = int(item['slide_number'].replace('slide_',''))

        # Construct the full file path for the image
        pdf_path = f"{base_dir}/{ppt_name}/{ppt_name}.pdf"
        #pdf_path = base_dir/{ppt_name}/{ppt_name}.pdf

        if os.path.exists(pdf_path):
            pdf_pages.append((pdf_path, slide_number - 1))
        else:
            print(f"PDF file not found: {pdf_path}")

    # Create a new PDF document
    output_pdf = fitz.open()

    for pdf_path, page_num in pdf_pages:
        try:
            with fitz.open(pdf_path) as src_pdf:
                if 0 <= page_num < len(src_pdf)+1:
                    output_pdf.insert_pdf(src_pdf, from_page=page_num, to_page=page_num)
                    #print(f"Page {page_num + 1} inserted")
                else:
                    print(f"Page {page_num + 1} not found in {pdf_path}")
        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")

    # Save the combined PDF
    combined_pdf_path = output_files_path / "v2_generated_pdf.pdf"
    output_pdf.save(combined_pdf_path)
    output_pdf.close()

    print(f'PDF with combined slides created successfully and saved at {combined_pdf_path}')

    # Return the path where the PDF is saved
    return str(combined_pdf_path)
    

def initialize_chroma():

    #Chroma converts the text into the embeddings using all-MiniLM-L6-v2, but we have modified the collection to use another embedding model.

    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="intfloat/e5-large-v2")

    #The Settings object is passed to the Client to configure the database connection.
    new_settings = Settings(
        chroma_api_impl="chromadb.api.segment.SegmentAPI",
        is_persistent=True,
        persist_directory = v1_persist_directory, #Sets the directory where the database files will be stored.
        chroma_server_ssl_enabled=True,
        chroma_server_host="localhost",
        chroma_server_http_port=8080,
        anonymized_telemetry=False
    )
    #Creates a new Client instance from the chromadb library.
    chroma_client = chromadb.PersistentClient(path = v1_persist_directory, settings=new_settings)
    
    collection = chroma_client.get_or_create_collection("Slides", embedding_function = sentence_transformer_ef)
    
    return collection


'''Use only to create ChromaDB from scratch using JSON files'''

# Load and process the JSON data
def load_and_process_json(file_path: str) -> List[Dict]: 
    with open(file_path, 'r') as file:
        data = json.load(file)

    processed_data = []
    for item in data['output']:
        filename = item['filename']
        for slide in item['content']:
            processed_data.append({
                'id': f"{filename}_{slide['slide_number']}",
                'text': slide['text'],
                'images_summary' : slide['images_summary'],
                'metadata': {
                    'filename': filename,
                    'slide_number': slide['slide_number']
                }
            })
    return processed_data

# Store data in Chroma
def store_in_chroma(collection, data: List[Dict]):
    ids = [item['id'] for item in data]
    texts = [f"Text:\n{item['text']}\n\nImages Summary:\n{item['images_summary']}" for item in data]
    metadatas = [item['metadata'] for item in data]

    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas
    )

    return collection

'''To separate slide content into text, table and image summary, for further scoring'''

def separate_content(text):
    # Remove any surrounding quotes
    text = text.strip("'\"")

    # Split the content into sections
    sections = re.split(r'\n(?=Text:|\*\*Table\*\*:|Images Summary:)', text)
    text_content = ""
    table_content = ""
    images_summary_content = ""

    for section in sections:
        if section.startswith("Text:"):
            text_content = section.replace("Text:", "").strip()
        elif section.startswith("**Table**:"):
            table_content = section.replace("**Table**:", "").strip()
        elif section.startswith("Images Summary:"):
            images_summary_content = section.replace("Images Summary:", "").strip()

    # Clean up the images summary content
    images_summary_content = images_summary_content.strip("[]")

    return text_content, table_content, images_summary_content

'''To get the most different slide combinations'''

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

'''Main Retrieval Function'''


#It will convert the query into embedding thus high-performing embedding model is used 
# Initialising the model that calculates relevance score

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

# Query Chroma function
def query_chroma(collection, queries: List[Dict], use_hnsw: bool = True, normalize: bool = True, filenames: List[str] = None):
    all_results = []
    best_result = []
    excluded_files = set()
    used_hashes = set()
    unique_items = []

# Function to filter unique images using image perceptual hashing
    def filter_unique_images(image_paths, used_hashes, threshold=5):

        unique_images = {}

        for image_path,value in image_paths.items():

            image = Image.open(image_path)
            # Calculate perceptual hash (phash) for the image
            phash = imagehash.phash(image)

            # Check against all used hashes
            is_unique = True
            for used_hash in used_hashes:
                if phash - used_hash <= threshold:
                    is_unique = False
                    break

            # If the image is unique, add it to the unique_images dict
            if is_unique:
                unique_images[image_path] = value
                used_hashes.add(phash)  # Optionally add this hash to used_hashes

        return unique_images

    for query in queries:
    #   for query_text, num_of_slides in query.items():
        query_text = query.get("query_text")
        num_of_slides = int(query.get("num_of_slides", 1))  # Ensure num_of_slides is an integer
        # Use if you want to retrieve slides from some specific PPTs
        if filenames:
            all_data = collection.get(include=['embeddings', 'documents', 'metadatas'])
            filtered_data = {
                'embeddings': [],
                'documents': [],
                'metadatas': [],
                'ids': []
            }
            for embedding, document, metadata,ids in zip(all_data['embeddings'], all_data['documents'], all_data['metadatas'],all_data['ids']):
                text_content, table_content, images_summary_content = separate_content(document)
                if len(text_content) > 150:
                    filtered_data['embeddings'].append(embedding)
                    filtered_data['documents'].append(document)
                    filtered_data['metadatas'].append(metadata)
                    filtered_data['ids'].append(ids)
            all_data = filtered_data

            for i, metadata in enumerate(all_data['metadatas']):
                if metadata['filename'] in filenames:
                    filtered_data['embeddings'].append(all_data['embeddings'][i])
                    filtered_data['documents'].append(all_data['documents'][i])
                    filtered_data['metadatas'].append(all_data['metadatas'][i])
                    filtered_data['ids'].append(all_data['ids'][i])
            all_data = filtered_data
        # Normally, executes from here
        else:
            all_data = collection.get(include=['embeddings', 'documents', 'metadatas'])
            filtered_data = {
                'embeddings': [],
                'documents': [],
                'metadatas': [],
                'ids': []
            }

            for embedding, document, metadata,ids in zip(all_data['embeddings'], all_data['documents'], all_data['metadatas'],all_data['ids']):
                text_content, table_content, images_summary_content = separate_content(document)
                if len(text_content) > 150:
                    filtered_data['embeddings'].append(embedding)
                    filtered_data['documents'].append(document)
                    filtered_data['metadatas'].append(metadata)
                    filtered_data['ids'].append(ids)
            all_data = filtered_data

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
            distances, indices = index.search(query_embedding.astype('float32'), min(num_of_slides * 2, len(embeddings)))
        except Exception as e:
            print(f"Error during search: {str(e)}")
            continue

        # Filtering the results based on relevance of different elements
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            document = all_data['documents'][idx]
            metadata = all_data['metadatas'][idx]
            ids = all_data['ids'][idx]
            text_content, table_content, images_summary_content = separate_content(document)
            text_relevance_score = get_relevance_score(query_text, text_content)
            table_relevance_score = get_relevance_score(query_text, table_content)
            images_summary_relevance_score = get_relevance_score(query_text, images_summary_content)

            # Calculating the combined score, giving different weights to different sections
            relevance_score = 0.6*(text_relevance_score) + 0.2*(table_relevance_score) + 0.2*(images_summary_relevance_score)

            similarity_score = 1 / (1 + distance)
            similarity_score = (similarity_score - 0.5)*2

            alpha = 0.3
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
                'images_summary_relevance_score': images_summary_relevance_score,
                'similarity_score': similarity_score,
                'relevance_score': relevance_score,
                'combined_score': combined_score
            })

        # Filtering out the slides that are too similar
        results = [r for r in results if r['ids'] not in excluded_files]
        results.sort(key=lambda x: x['combined_score'], reverse=True)
        image_paths = {f"{v1_base_dir}/{r['metadata']['filename']}/{r['metadata']['slide_number']}.png" : r['ids'] for r in results}
        unique_slides = filter_unique_images(image_paths, used_hashes)
        results = [r for r in results if r['ids'] in unique_slides.values()]

        # There are two modes - get the n best retrieved slides, or get the n most dissimilar retrieved slides
        # Uncomment the one that you want to use, and comment the other one.

        #best_result = find_farthest_slides(results,num_of_slides)
        best_result = results[:num_of_slides]

        best_result = sorted(best_result, key=lambda x: x['combined_score'], reverse=True)

        # Printing the results
        for i in range(len(best_result)):
          excluded_files.add(best_result[i]['ids'])
          filename = best_result[i]['metadata']['filename']
          slide_number = best_result[i]['metadata']['slide_number']
          print(f"\nResults {i+1} for query: '{query_text}'")
          print(f"Filename: {best_result[i]['metadata']['filename']}")
          print(f"Slide Number: {best_result[i]['metadata']['slide_number']}")
          print(f"Distance: {best_result[i]['distance']:.4f}")
          print(f"Length : {best_result[i]['length']}")
          print(f"Text Relevance Score: {best_result[i]['text_relevance_score']:.4f}")
          print(f"Table Relevance Score: {best_result[i]['table_relevance_score']:.4f}")
          print(f"Images Summary Relevance Score: {best_result[i]['images_summary_relevance_score']:.4f}")
          print(f"Relevance Score: {best_result[i]['relevance_score']:.4f}")
          print(f"Combined Score: {best_result[i]['combined_score']:.4f}")
          print(f"Content: {best_result[i]['document'][:100]}...")  # Print first 100 characters
          print("-" * 50)
          all_results.append(best_result[i])

    faiss_results = {
        'documents': [r['document'] for r in all_results],
        'metadatas': [r['metadata'] for r in all_results],
        'distances': [r['distance'] for r in all_results],
        'text_relevance_scores': [r['text_relevance_score'] for r in all_results],
        'table_relevance_scores': [r['table_relevance_score'] for r in all_results],
        'images_summary_relevance_scores': [r['images_summary_relevance_score'] for r in all_results],
        'relevance_scores': [r['relevance_score'] for r in all_results],
        'combined_scores': [r['combined_score'] for r in all_results]
    }

    # Print the results in a tabular format
    result_index = -1
    readme_content = []
    
    readme_content.append("The retrieval results of relevant slides based on the given queries.\n")
    


    number = 0
    # Table headers
    readme_content.append("| **No.** | **Slide** | **PPT Name**                                                   |")
    readme_content.append("|---------|-----------|----------------------------------------------------------------|")


    for query in queries:
        query_text = query.get("query_text")
        num_of_slides = int(query.get("num_of_slides", 1))  # Ensure num_of_slides is an integer
        
        title = f"**{str(query_text).strip()}**"
        readme_content.append(f"|Query name| {title:<50} |")
        
        # for query_text,num_of_slides in query.items():
        print(f"\nResults for query: '{query_text}'")
        print("-" * 150)
        print("{:<70} {:<15} {:<15} {:<20} {:<15}".format("Filename", "Slide No.", "Distance", "Relevance Score", "Combined Score"))
        print("-" * 150)
        for _ in range(num_of_slides):  # Print the results for each query
            result_index += 1
            if result_index < len(faiss_results['metadatas']):
                filename = faiss_results['metadatas'][result_index]['filename']
                slide_no = faiss_results['metadatas'][result_index]['slide_number']
                # distance = faiss_results['distances'][result_index]
                # relevance_score = faiss_results['relevance_scores'][result_index]
                # combined_score = faiss_results['combined_scores'][result_index]
                
                number += 1
                readme_content.append(f"| {number} | {slide_no:<13} | {filename:<60} |")

                print("{:<70} {:<15} {:<15.4f} {:<20.4f} {:<15.4f}".format(filename, slide_no, distance, relevance_score,combined_score))
        print("-" * 150)

    # Write the content to README.md
    # slide_composition_path = "D:\\AlgoAnalytics\\CC_Demo_App\\retrieval_v2\\README.md"
    
    with open(f"{output_files_path}/README.md", "w") as f:
        f.write("\n".join(readme_content))

    # print("README.md file has been created.")

    pdf = combine_pdf_slides(faiss_results, v1_base_dir, output_files_path)

    return pdf

def run_retrieval_pipeline_v1(queries):
    print("QUERIES::",queries)
    collection = initialize_chroma()

    if collection.count()== 0:
    # Main execution (From Scratch)
        for file in os.listdir(v1_json_files_path):
            file_path = os.path.join(v1_json_files_path, file)
            data = load_and_process_json(file_path)
            collection = store_in_chroma(collection, data)
    else:
        print(f"{v1_persist_directory} is not empty. Chromadb won't be Initialized.")
    
    pdf_path = query_chroma( collection, queries, use_hnsw=True, normalize=True)
    
    
    return pdf_path