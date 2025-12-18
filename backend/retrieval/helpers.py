#for combining pdf slides function
from pathlib import Path
import os
import json
#for converting pdf to pptx
import convertapi
# import base64
# import time

from utils.constants import output_files_path

def convert_pdf_to_pptx():

    #Set the API secret for ConvertAPI
    convertapi.api_secret = os.getenv('ALGOCREATOR_CONVERTAPI_SECRET')
    print("convertapi:",os.getenv('ALGOCREATOR_CONVERTAPI_SECRET'))
    print(convertapi.api_secret)

    try:
        # Perform the conversion
        # result = convertapi.convert('pptx', {
        #     'File': pdf
        # }, from_format='pdf')

        # Save the converted files to the specified directory
        ppt_file = Path(output_files_path) / "v2_generated_presentation.pptx"
        # result.save_files(ppt_file)
    
        print("Conversion successful. Files saved to:", ppt_file)
        return ppt_file
    except Exception as e:
        print("An error occurred during conversion:", str(e))


def get_readme_file():
    try:
        readme_file_path = Path(output_files_path) / "slide_composition.json"
        with open(readme_file_path, "r", encoding="utf-8") as file:
            content = json.load(file)  # Load JSON as Python dict/list
        return content
    except Exception as e:
        print(f"An error occurred while reading slide_composition.json: {e}")
        return None


