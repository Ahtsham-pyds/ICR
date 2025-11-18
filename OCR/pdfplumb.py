import pdfplumber
from PIL import Image
import io
# Assume you have access to a local vision model in Cloudera

pdf_path = r"C:\Users\hahtsham\work\ICR\OCR\Flange MTC (First Case).pdf"

with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        # Convert page to image
        img = page.to_image(resolution=300)
        pil_image = img.original
        
        # Send to your local vision model with prompt
        prompt = """Extract all tables from this Material Test Certificate.
        
        Return the data in JSON format with these sections:
        1. Chemical Analysis table (elements, min, max, heat values)
        2. Mechanical Properties table (tensile strength, yield strength, elongation, hardness)
        3. Document metadata (MTR number, heat number, order number, date)
        
        Preserve exact numerical values."""
        
        # Call your local vision model
        response = your_vision_model.predict(pil_image, prompt)
        print(response)
