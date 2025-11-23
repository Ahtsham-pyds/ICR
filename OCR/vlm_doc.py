
source_pdf = r"C:\Users\hahtsham\work\ICR\OCR\Flange MTC (First Case).pdf"
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

pipeline_options.do_ocr = False
pipeline_options.do_table_structure = False
pipeline_options.do_formula_enrichment = False
pipeline_options.do_code_enrichment =  False
pipeline_options.do_picture_classification = False
pipeline_options.do_picture_description =  False
pipeline_options.enable_remote_services =  False

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
