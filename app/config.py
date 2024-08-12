import os

BASE_URL = "https://mate.academy/"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED_DATA_DIR = os.path.join(PROJECT_ROOT, "extracted_data")

os.makedirs(EXTRACTED_DATA_DIR, exist_ok=True)

JSON_RESULT_FILE = os.path.join(EXTRACTED_DATA_DIR, "courses_data.json")
EXCEL_RESULT_FILE = os.path.join(EXTRACTED_DATA_DIR, "courses_data.xlsx")
