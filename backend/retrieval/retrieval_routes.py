from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Tuple
import os
import asyncio
import traceback
from fastapi import BackgroundTasks, Query
from starlette.background import BackgroundTask
from fastapi.responses import StreamingResponse,PlainTextResponse,JSONResponse,FileResponse
# from retrieval.version1.retrieval_pipeline_v1 import run_retrieval_pipeline_v1
from retrieval.version2.retrieval_pipeline_v2 import run_retrieval_pipeline_v2, run_retrieval_pipeline_v4
from .helpers import get_readme_file, convert_pdf_to_pptx
import win32com.client as win32
# from utils.auth import get_current_active_user #For Authentification
from modules.query_rewrite import process_query_to_format
from modules.tagGeneration import extract_tags
from datetime import datetime,date
import json
from collections import defaultdict
import sys
from pathlib import Path
from fastapi import Request
import shutil
import gc
import pythoncom
from PyPDF2 import PdfReader, PdfWriter
import math
import uuid
import shutil

# Get the value of USER_AUTHENTICATION from the environment variable
# ALGOCREATOR_USER_AUTHENTICATION = os.getenv("ALGOCREATOR_USER_AUTHENTICATION", "false").lower() == "true"

# Conditionally set dependencies
# dependencies = [Depends(get_current_active_user)]

# Create the router
# router = APIRouter(dependencies=dependencies)  #For Authentification
router = APIRouter()

# router = APIRouter(dependencies = [Depends(get_current_active_user)])

# --- Constants ---
PPTX_ROOT_FOLDER = "retrieval/version2/AlgoOrgPPTs" 


class SlideResult(BaseModel):
    id: int
    slideNumber: int
    pptName: str

class QuerySlides(BaseModel):
    query: str
    results: List[SlideResult]

# --- Pydantic Models ---
class SlideSelection(BaseModel):
    pptx_path: str
    slide_numbers: List[int]

class PPTDownloadRequest(BaseModel):
    selections: List[SlideSelection]

class SelectionRequest(BaseModel):
    selected_items: List[str]

# Date Selection
class DateRange(BaseModel):
    creation_start:datetime
    creation_end:datetime
    modification_start:datetime
    modification_end:datetime

class SlideQuery(BaseModel):
    query_text: str = Field(..., )
    num_of_slides: int = Field(..., )

class QueriesRequest(BaseModel):
    queries: List[SlideQuery]  
    tags: List[List[str]]      
    folder_names: List[str]
    date_range: DateRange
    file_name: Optional[str] = None

class reorderRequest(BaseModel):
    file_name: str
    new_order: List[int]

###########################################################################

# Query Rewriting  
class myQuery(BaseModel):
    txt: str=Field(...,)


# Tag Generation
class myTag(BaseModel):
    txt:str=Field(...,)


# paragraph
class QueriesRequestPara(BaseModel):
    txt: str 
    folder_names: List[str]
    date_range: DateRange
      

# Folder selection
class LevelRequest(BaseModel):
   #selected_folders:List[str]
    level: int                     # level 1 or level 2
    

#For PDF Modification using selection
class PDFSelectionRequest(BaseModel):
    selected_ids: List[int]

#For Downloading PPT
class downloadPPT(BaseModel):
    file_name: str

# For listing all output files
class FileMetadata(BaseModel):
    id: str
    file_name: str
    file_path: str
    creation_date: str
    file_size: str
    file_type: str

#################################################################################  

@router.get("/")
async def root():
    return {"message": "Hello Retrieval"}

@router.get("/list_pdfs", response_model=List[FileMetadata])
async def get_all_files_metadata():
    FILE_FOLDER = "./static/outputs"
    ALLOWED_EXTENSIONS = [".pdf", ".pptx"]
    files_limit = 10
    if not os.path.isdir(FILE_FOLDER):
        raise HTTPException(
            status_code=404, 
            detail="File folder not found. Please create a folder named 'files'."
        )
    files_metadata = []

    for file_name in os.listdir(FILE_FOLDER):
        if file_name.endswith(tuple(ALLOWED_EXTENSIONS)):
            file_path = os.path.join(FILE_FOLDER, file_name)
            
            creation_timestamp = os.path.getctime(file_path)
            creation_date = datetime.fromtimestamp(creation_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            
            file_size = os.path.getsize(file_path)
            file_type = file_name.split('.')[-1].upper()

            file_info = {
                "id": uuid.uuid4().hex[:8],
                "file_name": file_name,
                "file_path": file_path,
                "creation_date": creation_date,
                "file_size": get_file_size(file_size),
                "file_type": file_type
            }
            files_metadata.append(file_info)
    files_metadata.sort(key=lambda item: item['creation_date'], reverse=True)
    return files_metadata[:files_limit]

def get_file_size(size_bytes: int) -> str:
    """
    Converts a file size from bytes to a human-readable string (e.g., KB, MB, GB).
    """
    if size_bytes == 0:
        return "0 B"
    size_units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    
    if i >= len(size_units):
        i = len(size_units) - 1
        
    size_value = round(size_bytes / (1024 ** i), 2)
    
    return f"{size_value} {size_units[i]}"


@router.post("/v4/retrieve_slides")
async def api_retrieve_slides_v2(request: QueriesRequest):

    try:
        print("Retrieval parameters start\n")
        print("Query: ", request.queries)
        print("Tags: ", request.tags)
        print("Date filter: ", request.date_range)
        print("Folder names: ", request.folder_names)
        print("File name: ", request.file_name)
        print("\nRetrieval parameters end\n")  
        queries = [{item.query_text: item.num_of_slides} for item in request.queries]
        tags = request.tags
        folder_names = request.folder_names

        date_filter = {
            "creation_start": request.date_range.creation_start,
            "creation_end": request.date_range.creation_end,
            "modification_start": request.date_range.modification_start,
            "modification_end": request.date_range.modification_end,
        } if request.date_range else None

        # Run the slide retrieval pipeline
        pdf_file_path = run_retrieval_pipeline_v2(
            queries=queries,
            tags=tags,
            folder_names=folder_names,
            date_filter=date_filter
        )

        if not pdf_file_path or not os.path.exists(pdf_file_path):
            raise HTTPException(status_code=404, detail="PDF file not found.")

        # Move to static directory
        os.makedirs("static/outputs", exist_ok=True)
        base_name = request.file_name if request.file_name else "retrieved_slides"
        file_name = f"{base_name}_{uuid.uuid4().hex[:8]}.pdf"
        static_path = os.path.join("static/outputs", file_name)
        # os.rename(pdf_file_path, static_path)
        shutil.copy2(pdf_file_path, static_path)

        retrieved_json_path = r"C:\\Users\\Administrator\\Desktop\\AlgoCreator_Chatbot\\AlgoCreator_Chatbot\\RAG\\tools\\JSON's\\retrieved_slides.json"
        with open(retrieved_json_path, "r", encoding="utf-8") as f:
            retrieved_data = json.load(f)

        compositions_path = "./retrieval/compositions.json"
        os.makedirs(os.path.dirname(compositions_path), exist_ok=True)

        if os.path.exists(compositions_path):
            with open(compositions_path, "r", encoding="utf-8") as f:
                compositions_data = json.load(f)
        else:
            compositions_data = {}
        
        compositions_data[file_name] = retrieved_data

        with open(compositions_path, "w", encoding="utf-8") as f:
            json.dump(compositions_data, f, indent=4)

        # Construct full download URL (adjust IP/port as needed)
        host = "http://216.48.180.247:8000"
        download_url = f"{host}/static/outputs/{file_name}"

        return {
            "pdf_url": download_url 
        }

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
    

@router.post('/reorder_slides')
async def reorder_slides(request: reorderRequest):
    pdf_path = './retrieval/Output_files/retrieved_slides.pdf'
    output_folder = './static/outputs'
    print("reorder request received")
    print("new order: ", request.new_order)

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Source PDF not found")
    
    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF: {str(e)}")
    
    num_pages = len(reader.pages)
    writer = PdfWriter()

    try:
        for idx in request.new_order:
            if not isinstance(idx, int):
                raise HTTPException(status_code=400, detail=f"Invalid index type: {idx} (must be int)")
            if idx < 0 or idx >= num_pages:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid page index {idx}. PDF has {num_pages} pages (0–{num_pages-1})."
                )
            writer.add_page(reader.pages[idx])
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while reordering: {str(e)}")
    
    unique_id = str(uuid.uuid4().hex[:8])
    new_filename = f"reordered_{request.file_name}_{unique_id}.pdf"
    new_filepath = os.path.join(output_folder, new_filename)
    try:
        with open(new_filepath, "wb") as f:
            writer.write(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write output PDF: {str(e)}")
    
    retrieved_json_path = r"C:\\Users\\Administrator\\Desktop\\AlgoCreator_Chatbot\\AlgoCreator_Chatbot\\RAG\\tools\\JSON's\\retrieved_slides.json"
    with open(retrieved_json_path, "r", encoding="utf-8") as f:
        retrieved_data = json.load(f)

    compositions_path = "./retrieval/compositions.json"
    os.makedirs(os.path.dirname(compositions_path), exist_ok=True)

    if os.path.exists(compositions_path):
        with open(compositions_path, "r", encoding="utf-8") as f:
            compositions_data = json.load(f)
    else:
        compositions_data = {}
    
    compositions_data[new_filename] = retrieved_data

    with open(compositions_path, "w", encoding="utf-8") as f:
        json.dump(compositions_data, f, indent=4)

    return {
        "message": "PDF reordered successfully",
    }


@router.get("/v4/download_pdf")
async def download_pdf_v4(file_path: str):
    fp = file_path
    if not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="File not found")
    stream = open(fp, "rb")
    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=generated_pdf.pdf"},
        background=BackgroundTask(stream.close),
    )

@router.post("/v2/retrieve_slides")
async def api_retrieve_slides_v2(request: QueriesRequest):
    # Unpack parameters from the request model
    queries = [{item.query_text: item.num_of_slides} for item in request.queries]
    tags = request.tags
    folder_names = request.folder_names

    print(queries)
    print("queries:",queries,"tags:",tags, "folder names:",folder_names)

    try:
        date_filter = None
        if request.date_range:
            date_filter = {
                "creation_start": request.date_range.creation_start,
                "creation_end": request.date_range.creation_end,
                "modification_start": request.date_range.modification_start,
                "modification_end": request.date_range.modification_end,
            }
            print("Date filter provided:", date_filter)
        else:
            print("No date filter provided.")
        #pdf_file_path = "D:\\AlgoAnalytics\\algocreator_fastapi\\retrieval\\retrieval_v2\\Outputs\\OUTPUT_PDF\\retrieved_slides.pdf"
        pdf_file_path = run_retrieval_pipeline_v2(queries=queries, tags=tags, folder_names=folder_names,date_filter=date_filter) 
        if not pdf_file_path:
            raise HTTPException(status_code=404, detail="No pdf file generated.")
        
        if os.path.exists(pdf_file_path):
            # Use context manager to open the file
            file_stream = open(pdf_file_path, "rb")

            close_file_task = BackgroundTask(file_stream.close)

            # # Define a custom close function to ensure the file is closed after response
            # def close_file():
            #     file_stream.close()
            #     os.remove(pdf_file_path)  # Optionally remove the file after it's served
            
            return StreamingResponse(
                file_stream,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=generated_pdf.pdf"},
                background=close_file_task  # Close file after streaming
            )
        
    except HTTPException:
        raise  # re-raise HTTPException to let FastAPI handle it

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

    

@router.get("/slide_composition")
async def api_get_readme_file():
    try:
        content = get_readme_file()
        if content is None:
            raise FileNotFoundError
        return JSONResponse(content={"slide_composition": content})
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="slide_composition.json not found")

    
    
#################################################################


@router.post("/query_rewrite")
async def funRewrite(q:myQuery):
    print(q.txt)
    finalOutput=process_query_to_format(q.txt)
    print(finalOutput)
    return {
        "rewritten query":finalOutput
    }


@router.post("/tag_generation")
async def funTagGenerataion(t:myTag):
    print(t.txt)
    tagOutput= extract_tags(t.txt)
    print(tagOutput)
    return {
        "Generated Tags are": tagOutput
    }


#For Paragraph based query retriever
@router.post("/v2/retrieve_slides_paragraph")
async def api_retrieve_slides_v2_para(mrequest: QueriesRequestPara):
    # Unpack parameters from the request model
    txt = mrequest.txt
    folder_names = mrequest.folder_names

    print("input txt is:", txt, folder_names)

    try:
        # Process input query
        newinput = process_query_to_format(txt)
        print("new input is:", newinput, "tags:", [], "folder names:", folder_names)

        # Prepare date filter if date_range is provided
        date_filter = None
        if mrequest.date_range:
            date_filter = {
                "creation_start": mrequest.date_range.creation_start,
                "creation_end": mrequest.date_range.creation_end,
                "modification_start": mrequest.date_range.modification_start,
                "modification_end": mrequest.date_range.modification_end,
            }
            print("Date filter provided:", date_filter)
        else:
            print("No date filter provided.")

        # Run pipeline with date filter if present
        pdf_file_path = run_retrieval_pipeline_v2(
            queries=newinput,
            tags=[],
            folder_names=folder_names,
            date_filter=date_filter  # Pass to your pipeline function
        )

        if not pdf_file_path:
            raise HTTPException(status_code=404, detail="No pdf file generated.")

        if os.path.exists(pdf_file_path):
            file_stream = open(pdf_file_path, "rb")
            close_file_task = BackgroundTasks()
            close_file_task.add_task(file_stream.close)

            return StreamingResponse(
                file_stream,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=generated_pdf.pdf"},
                background=close_file_task
            )
        else:
            return {"error": "File not found"}

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


LOCAL_PPTX_ROOT = Path("retrieval/version2/AlgoOrgPPTs").resolve()

def convert_drive_path_to_local(drive_path: str, anchor_folder: str = "Algo_Org_PPTs") -> Path:
    """Convert Google Drive-style path to local path rooted at anchor."""
    parts = Path(drive_path).parts
    if anchor_folder not in parts:
        raise ValueError(f"'{anchor_folder}' not found in path: {drive_path}")
    anchor_index = parts.index(anchor_folder)
    return LOCAL_PPTX_ROOT.joinpath(*parts[anchor_index + 1:])

def combine_selected_pptx_slides(
    source_pptx_paths: List[str],
    slide_selections: List[Tuple[int, List[int]]],
    output_pptx_path: str,
    debug_flag: bool = True,
    alert_flag: bool = False
):
    """Combines selected slides from given PPTX files into a new presentation."""
    pythoncom.CoInitialize()
    powerpoint = win32.Dispatch("PowerPoint.Application")
    powerpoint.Visible = debug_flag
    powerpoint.DisplayAlerts = alert_flag

    new_presentation = powerpoint.Presentations.Add()
    output_dir = os.path.dirname(output_pptx_path)
    os.makedirs(output_dir, exist_ok=True)

    try:
        for file_idx, slides in slide_selections:
            if file_idx < 0 or file_idx >= len(source_pptx_paths):
                print(f"[WARN] Invalid index {file_idx}")
                continue

            src_path = os.path.abspath(source_pptx_paths[file_idx]).replace("/", "\\")
            if not os.path.exists(src_path):
                print(f"[WARN] Source not found: {src_path}")
                continue

            source_prs = None
            try:
                print(f"[INFO] Opening: {src_path}")
                source_prs = powerpoint.Presentations.Open(src_path, ReadOnly=True, WithWindow=False)

                for slide_num in slides:
                    if 1 <= slide_num <= source_prs.Slides.Count:
                        try:
                            source_prs.Slides(slide_num).Copy()
                            new_presentation.Slides.Paste(-1)
                            print(f"[INFO] Copied slide {slide_num} from {os.path.basename(src_path)}")
                        except Exception as err:
                            print(f"[ERROR] Copy failed for slide {slide_num}: {err}")
                    else:
                        print(f"[WARN] Slide {slide_num} out of range in {src_path}")
            except Exception as err:
                print(f"[ERROR] Failed to open: {src_path}: {err}")
            finally:
                if source_prs:
                    try:
                        source_prs.Close()
                        print(f"[INFO] Closed: {src_path}")
                    except Exception as err:
                        print(f"[ERROR] Error closing {src_path}: {err}")
                gc.collect()

        if new_presentation.Slides.Count:
            new_presentation.SaveAs(os.path.abspath(output_pptx_path))
            print(f"[SUCCESS] Saved: {output_pptx_path}")
        else:
            print("[INFO] No slides to save.")
    finally:
        try:
            if new_presentation and not new_presentation.Saved:
                new_presentation.Close()
        except Exception as err:
            print(f"[ERROR] Closing new presentation: {err}")
        try:
            powerpoint.Quit()
            print("[INFO] PowerPoint quit.")
        except Exception as err:
            print(f"[ERROR] Quitting PowerPoint: {err}")
        gc.collect()

async def safe_delete(file_path: str, max_retries: int = 5, delay: float = 0.5):
    """Asynchronously delete a file with retries."""
    for _ in range(max_retries):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except PermissionError:
            await asyncio.sleep(delay)
    return False

@router.post("/download_pptx")
async def ppt_download_from_json(request: downloadPPT, background_tasks: BackgroundTasks):
    """API endpoint to download a merged PPTX from slide selections in JSON."""
    try:
        # json_path = Path("retrieval/Output_files/slide_composition.json")
        json_path = "./retrieval/compositions.json"
        if not os.path.exists(json_path):
            raise HTTPException(status_code=400, detail="JSON input not found.")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or not data:
            raise HTTPException(status_code=400, detail="Expected non-empty list in JSON.")

        ppt_to_index = {}
        source_paths = []
        slide_data = []

        for query_group in data[request.file_name]:
            for item in query_group.get("results", []):
                local_path = str(convert_drive_path_to_local(item["pptName"]))
                if local_path not in ppt_to_index:
                    ppt_to_index[local_path] = len(source_paths)
                    source_paths.append(local_path)
                file_index = ppt_to_index[local_path]
                slide_data.append((file_index, [item["slideNumber"]]))

        # Merge slides by file index
        merged = defaultdict(list)
        for file_index, slides in slide_data:
            merged[file_index].extend(slides)

        merged_slide_data = [(k, v) for k, v in merged.items()]
        output_path = Path("retrieval/Output_files/temp_combined.pptx").resolve()

        print(f"[DEBUG] Files: {source_paths}")
        print(f"[DEBUG] Slides: {merged_slide_data}")

        combine_selected_pptx_slides(source_paths, merged_slide_data, str(output_path))

        background_tasks.add_task(safe_delete, str(output_path))
        # return FileResponse(
        #     path=output_path,
        #     media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        #     filename="generated_ppt.pptx"
        # )
        from fastapi.responses import StreamingResponse

        def file_iterator(file_path, chunk_size=1024*1024):
            with open(file_path, mode="rb") as file:
                while chunk := file.read(chunk_size):
                    yield chunk
        import time
        time.sleep(10)  # Wait to ensure COM process is flushed

        return StreamingResponse(
            file_iterator(str(output_path)),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": "attachment; filename=generated_ppt.pptx"}
        )


    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PPT merge failed: {e}")



@router.post("/select_date")
async def funSelectDate(dates:DateRange):
    if dates.creation_start > dates.creation_end:
        raise HTTPException(status_code=400,detail="creation_start date must be before creation_end date")
    if dates.modification_start > dates.modification_end:
        raise HTTPException(status_code=400,detail="modification_start date must be before modification_end date")
    
    return {
       "message": "file date range selected successfully",
       "creation_start": dates.creation_start,
       "creation_end": dates.creation_end,
       "modification_start": dates.modification_start,
       "modification_end": dates.modification_end
   }


ROOT_FOLDER = "Algo_Org_PPTs"

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None

def is_date_within_range(date: Optional[datetime], start: datetime, end: datetime) -> bool:
    if not date:
        return False
    return start <= date <= end

def load_json_data(file_path: str) -> dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"JSON file not found at {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1]
    mapping = {
        'pptx': 'Presentation file',
        'ppt': 'Presentation file',
        'pdf': 'PDF file',
        'docx': 'Document',
        'doc': 'Document',
        'xlsx': 'Excel file',
        'csv': 'CSV file',
        'txt': 'Text file'
    }
    return mapping.get(ext, 'File')

def find_summary(summaries_data: Dict[str, str], folder_path_parts: List[str]) -> Optional[str]:
    """
    Given a list of path parts, try to find the most specific summary in summaries_data.
    """
    base_prefix = "/content/drive/MyDrive/GenAI (UI UX)"
    for i in range(len(folder_path_parts), 0, -1):
        candidate_path = base_prefix + "/" + "/".join(folder_path_parts[:i])
        if candidate_path in summaries_data:
            return summaries_data[candidate_path]
    return None

def insert_file(root: Dict[str, Any], path_parts: List[str], summaries_data: Dict[str, str], file_name: str):
    """
    Recursively insert file into the nested folder structure.
    """
    node = root
    folder_path_parts = [ROOT_FOLDER]
    for part in path_parts:
        folder_path_parts.append(part)
        # Check if subfolder exists
        found = False
        for sub in node['subfolders']:
            if sub['name'] == part:
                node = sub
                found = True
                break
        if not found:
            # Add new subfolder
            summary = find_summary(summaries_data, folder_path_parts)
            new_folder = {
                "name": part,
                "description": summary if summary else f"Description for {part}.",
                "subfolders": [],
                "files": []
            }
            node['subfolders'].append(new_folder)
            node = new_folder
    # Add the file
    node['files'].append({
        "name": file_name,
        "type": get_file_type(file_name)
    })

@router.get("/pptx_paths")
async def pptx_paths(
    creation_start: Optional[str] = Query(None),
    creation_end: Optional[str] = Query(None),
    modification_start: Optional[str] = Query(None),
    modification_end: Optional[str] = Query(None),
):
    try:
        JSON_PATH = "./retrieval/version2/JSON/new_combined_content_V3.json"
        SUBFOLDER_SUMMARY_PATH = "./retrieval/version2/JSON/subfolder_summaries.json"
        
        data = load_json_data(JSON_PATH)
        summaries_data = load_json_data(SUBFOLDER_SUMMARY_PATH)

        # Parse dates
        creation_start_dt = parse_date(creation_start)
        creation_end_dt = parse_date(creation_end)
        modification_start_dt = parse_date(modification_start)
        modification_end_dt = parse_date(modification_end)

        # Root summary (use the exact key from your summaries file)
        root_summary = summaries_data.get(
            "/content/drive/MyDrive/GenAI (UI UX)/Algo_Org_PPTs",
            "Root folder containing various technology-related projects."
        )
        root_node = {
            "name": ROOT_FOLDER,
            "description": root_summary,
            "subfolders": [],
            "files": []
        }

        # Process each PPTX file
        for item in data:
            pptx_path = item.get("pptx_path")
            if pptx_path is None or ROOT_FOLDER not in pptx_path:
                continue

            # Date filtering
            creation_date = parse_date(item.get("creation_date"))
            modification_date = parse_date(item.get("modification_date"))
            if creation_start_dt and creation_end_dt:
                if not (creation_date and is_date_within_range(creation_date, creation_start_dt, creation_end_dt)):
                    continue
            if modification_start_dt and modification_end_dt:
                if not (modification_date and is_date_within_range(modification_date, modification_start_dt, modification_end_dt)):
                    continue

            # Make path relative to ROOT_FOLDER
            root_index = pptx_path.find(ROOT_FOLDER)
            relative_path = pptx_path[root_index + len(ROOT_FOLDER) + 1:]  # skip the root and "/"
            if not relative_path:
                continue
            parts = relative_path.split("/")
            if len(parts) < 1:
                continue
            file_name = parts[-1]
            folder_parts = parts[:-1]
            insert_file(root_node, folder_parts, summaries_data, file_name)

        # ---- First-level folder extraction ----
        first_level_folders_set = set()

        for item in data:
            pptx_path = item.get("pptx_path")
            if pptx_path is None or ROOT_FOLDER not in pptx_path:
                continue

            creation_date = parse_date(item.get("creation_date"))
            modification_date = parse_date(item.get("modification_date"))
            if creation_start_dt and creation_end_dt:
                if not (creation_date and is_date_within_range(creation_date, creation_start_dt, creation_end_dt)):
                    continue
            if modification_start_dt and modification_end_dt:
                if not (modification_date and is_date_within_range(modification_date, modification_start_dt, modification_end_dt)):
                    continue

            root_index = pptx_path.find(ROOT_FOLDER)
            relative_path = pptx_path[root_index + len(ROOT_FOLDER) + 1:]  # skip the root and "/"
            if not relative_path:
                continue
            parts = relative_path.split("/")
            if len(parts) < 1:
                continue
            # ---- Collect first-level folder ----
            if len(parts) > 1:
                first_level_folders_set.add(parts[0])
            file_name = parts[-1]
            folder_parts = parts[:-1]
            insert_file(root_node, folder_parts, summaries_data, file_name)

        first_level_folders = list(first_level_folders_set)


        # ---- Return both root_node and first_level_folders ----
        return {
            "root_node": root_node,
            "first_level_folders": first_level_folders
        }

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")



####################################################################

@router.post("/edit_pdf_by_selection")
async def edit_pdf_by_selection(selection: PDFSelectionRequest):
    # File paths
    composition_path = "retrieval/Output_files/slide_composition.json"
    pdf_path = "retrieval/Output_files/retrieved_slides.pdf"
    output_pdf_path = "retrieval/Output_files/selected_pages.pdf"

    # 1. Ensure necessary files exist
    if not os.path.exists(composition_path) or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Required files not found.")

    # 2. Load composition
    with open(composition_path, "r", encoding="utf-8") as f:
        composition = json.load(f)

    # 3. Flatten all results to map result ID -> index (PDF page number)
    flat_results = []
    for group in composition:
        flat_results.extend(group.get("results", []))

    id_to_page_index = {
        result["id"]: idx for idx, result in enumerate(flat_results)
    }

    # 4. Determine pages to extract (0-based)
    selected_pages = sorted(set(
        id_to_page_index[id_] for id_ in selection.selected_ids if id_ in id_to_page_index
    ))

    if not selected_pages:
        raise HTTPException(status_code=400, detail="No valid selections found.")

    # 5. Extract selected pages from PDF
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    total_pages = len(reader.pages)

    for page_num in selected_pages:
        if 0 <= page_num < total_pages:
            writer.add_page(reader.pages[page_num])
        else:
            print(f"Warning: page number {page_num} is out of range.")

    # 6. Save output PDF
    with open(output_pdf_path, "wb") as out_f:
        writer.write(out_f)

    # 7. Overwrite the main working PDF with the updated one for cumulative edts
    shutil.copy(output_pdf_path, pdf_path)

    # 8. Update composition: keep only selected results, refresh IDs, preserve group/query structure
    selected_id_set = set(selection.selected_ids)
    new_id = 1
    new_composition = []
    for group in composition:
        new_group = {"query": group.get("query"), "results": []}
        for result in group.get("results", []):
            if result["id"] in selected_id_set:
                # Copy and assign new ID
                new_result = result.copy()
                new_result["id"] = new_id
                new_group["results"].append(new_result)
                new_id += 1
        if new_group["results"]:
            new_composition.append(new_group)

    with open(composition_path, "w", encoding="utf-8") as f:
        json.dump(new_composition, f, indent=4)

    # 9. Return the selected PDF
    return StreamingResponse(
        open(output_pdf_path, "rb"),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=selected_pages.pdf"}
    )




# @router.post("/v1/retrieve_slides")
# async def api_retrieve_slides(queries: List[SlideQuery]):
#     queries = [query.model_dump() for query in queries]

#     try:     
#         pdf_file_path = run_retrieval_pipeline_v1(queries) 
#         print(pdf_file_path)
#         # pdf_file_path = "retrieval_v2\\Output_files\\v2_generated_pdf.pdf"
#         if not pdf_file_path:
#             raise HTTPException(status_code=404, detail="No pdf file generated.")
        
#         if os.path.exists(pdf_file_path):
#             # Use context manager to open the file
#             file_stream = open(pdf_file_path, "rb")
            
#             # Define a custom close function to ensure the file is closed after response
#             def close_file():
#                 file_stream.close()
#                 os.remove(pdf_file_path)  # Optionally remove the file after it's served
            
#             return StreamingResponse(
#                 file_stream,
#                 media_type="application/pdf",
#                 headers={"Content-Disposition": "attachment; filename=generated_pdf.pdf"},
#                 background=close_file  # Close file after streaming
#             )
#         else:
#             return {"error": "File not found"}

#     except Exception as e:
#         print(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
