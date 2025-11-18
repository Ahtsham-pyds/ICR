
source_pdf = r"C:\Users\hahtsham\work\ICR\OCR\Flange MTC (First Case).pdf"
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
pipeline_options.do_table_structure = True

converter = DocumentConverter(
    format_options={
        "pdf": PdfFormatOption(
            pipeline_options=pipeline_options,
            backend=PyPdfiumDocumentBackend  # Backend goes here, not in DocumentConverter
        )
    }
)

#source_pdf = r"C:\Users\hahtsham\work\ICR\OCR\Flange.pdf"
result = converter.convert(source=source_pdf)
doc = result.document

print(f"Pages: {len(doc.pages)}, Tables: {len(doc.tables)}")

text = doc.export_to_markdown()
print("Markdown length:", len(text))

with open("output.md", "w", encoding="utf-8") as f:
    f.write(text)
