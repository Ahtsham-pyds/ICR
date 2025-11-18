#from docling.datamodel import vlm_model_specs
#from docling.datamodel.base_models import InputFormat
#from docling.datamodel.pipeline_options import VlmPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
#from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.datamodel.pipeline_options import PdfPipelineOptions
#from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend


print('Import done')


pipeline_options = PdfPipelineOptions()
#pipeline_options.do_ocr = False

converter = DocumentConverter(
    format_options={
        "pdf": PdfFormatOption(pipeline_options=pipeline_options)
    }
)


source_pdf = r"C:\Users\hahtsham\work\ICR\OCR\Flange.pdf"
doc = converter.convert(source=source_pdf).document
with open("output.md", "w", encoding="utf-8") as f:
    f.write(doc.export_to_markdown())