from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from docling.document_converter import DocumentConverter
import tempfile, os
from fastapi.middleware.cors import CORSMiddleware
from docling import DoclingParser
from docling.vlm_connectors import VLMConnector, SupportedVLMs


app = FastAPI(title="Docling Text Extractor")

vlm_config = {
    "enabled": True,
    "model_name":'gpt-3.5-turbo',  # Or a local model name like "Docling-VLM-2B"
    "api_key_env": "open_api_key", # Environment variable for the key
    "extraction_strategy": "structured_markdown" # Request output in VLM-optimized format
}
converter = DocumentConverter()   # Configure OCR options if needed

origins = [
    "*", # In development, allow all origins. For production, restrict this to specific domains.
    # If running client on a specific local port, you can restrict it:
    "http://localhost:8080", 
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all standard methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)




@app.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    """
    Accepts a PDF or image upload and returns extracted Markdown text.
    """
    # Save to a temporary file since Docling works with file paths
    suffix = os.path.splitext(file.filename)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        result = converter.convert(tmp_path)
        
        #md_text = result.document.export_to_markdown()
        #return JSONResponse(content={"markdown": md_text})
        structured_data = result.document.export_to_dict() # Use the method that exports full structure
        #structural_data = result.document.export_to_html()
        structural_data = result.document.export_to_markdown()
        return JSONResponse(content={"document_structure": structural_data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    # This block is for running the script locally via 'python main.py'
    # In a typical setup, you use the 'uvicorn main:app' command instead.
    print("To run the API, please use the command: uvicorn main:app --reload")
    # uvicorn.run(app, host="0.0.0.0", port=8000) 
   