# FastAPI 
This project provides API endpoints for querying and retrieving data.



## Features
- Retrieve slide data based on user queries.
- Retrieves the README file as plain text.
- Download PowerPoint files dynamically.



## Contents
1. [Features](#features)
2. [Content](#contents)
3. [Project Structure](#project-structure)
4. [Getting Started](#getting-started)
5. [Endpoints](#endpoints)
6. [Constants](#constants)


## Project Structure 
```bash
.
├── extraction/               # Data extraction logic (future use)
├── notebooks/                # Jupyter notebooks for prototyping
├── retrieval/                # Main retrieval-related functionality
│   ├── output_files/         # Folder for generated output files
│   ├── version1/             # Version 1 of retrieval pipeline
│   │   └── retrieval_pipeline_v1
│   ├── version2/             # Version 2 of retrieval pipeline
│   │   ├── PPT_DATA/         # Folder to store PowerPoint files (manually created)
│   │   ├── PPT_DB_NEW/       # Persistent storage for database files (manually created)
│   │   └── retrieval_pipeline_v2
│   ├── helpers.py            # Utility functions for retrieval operations
│   └── retrieval_routes.py   # API routes for version 2 retrieval endpoints
├── utils/                    # Utility files and configurations
│   ├── auth.py               # Authentication logic
│   ├── constant.py           # Centralized constants (paths, etc.)
│   ├── user_data.csv         # User data in CSV format
│   └── users_csv_generator.py # Script to generate user data CSV
├── .gitignore                # Git ignore file             
├── main.py                   # Entry point for FastAPI application
├── README.md                 # Project documentation
├── requirements.txt          # Python dependencies
└── visionmodel.py            # Vision model or image processing logic

```
### **Explanation of Key Components**
1. **Folders**:
   - **`extraction/`**: Reserved for data extraction logic. Can include parsers or scripts for raw data extraction.  
   - **`notebooks/`**: Contains Jupyter notebooks for exploratory analysis or prototyping.
   - **`retrieval/`**: The core retrieval functionality, organized into versions and supporting files.  

2. **Files**:
   - **`retrieval_routes.py`**: Contains API routes for querying and retrieving slide data.
   - **`helpers.py`**: Includes utility functions to support retrieval pipelines.
   - **`constant.py`**: Stores paths and other constants.
   - **`auth.py`**: Handles authentication, such as validating user credentials.
   - **`users_csv_generator.py`**: Script to generate sample user data in `user_data.csv`.  

3. **Special Notes**:
   - **Folders like `PPT_DATA` and `PPT_DB_NEW` must be created manually** for the application to work correctly.
   - **`README.md`**: Comprehensive project documentation for usage, setup, and API details.



## Getting Started
### Prerequisites
- Python 3.10
- FastAPI
- Uvicorn 

### Installation 
**Step1. Clone the repository:**
```bash
gh repo clone Atripathi-Algo/algocreator_fastapi
cd algocreator_fastapi
```

**Step2. Create a virtual environment and activate it:**
```bash
python -m venv venv   
```

```bash
venv\Scripts\activate     # Windows  
```

```bash
source venv/bin/activate  # Linux/Mac 
```

**Step3. Install the dependencies:**
```bash
pip install -r requirements.txt
```

**Step4. Run the FastAPI server:** 
```bash
uvicorn main:app --reload
```



## Endpoints
### Base URL
`http://localhost:8000`

### Version 2 Routes
These routes are defined in `retrieval_routes.py`

**1. Retrieve Slides**
- **Endpoint:** `/v2/retrieve_slides`
- **Method:** `POST`
- **Description:** Retrieves slides matching the user query.
- **Input:** Query with Number of Slides, Tags, Folder Names.
- **Output:** PDF File which contains slide based on user query.

**2. Get Slide Composition (README)**
- **Endpoint:** `/get_readme`
- **Method:** `GET`
- **Description:** Retrieves the README file as plain text.
- **Output:** Contents of the README file.

**3. Download PowerPoint File**
- **Endpoint:** `/download_pptx`
- **Method:** `GET`
- **Description:** Allows downloading a specific PowerPoint file.
- **Output:** PowerPoint file as a downloadable response.



## Utilities 
Located in `utils/constants.py` 

**Note:**  You must manually create the PPT_DATA and PPT_DB_NEW folders at this path.

- v2_ppt_data_path: Path for Images of PPT (create)
```bash
v2_ppt_data_path = "./retrieval/version2/PPT_DATA"
```

- v2_persist_directory:persist directory to store vector database (create)
```bash
v2_persist_directory = "./retrieval/version2/PPT_DB_NEW"
```


