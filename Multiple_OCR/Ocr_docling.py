import pandas as pd
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.datamodel.document import InputDocument
from pathlib import Path
import json
from typing import List, Dict, Tuple
import re

pdf_path = r"c:\Users\hahtsham\work\ICR\Multiple_OCR\sample_with_tables.pdf"



pipeline_options_ = PdfPipelineOptions()
pipeline_options_.do_table_structure = True
pipeline_options_.do_ocr = False
pipeline_options_.table_structure_options.mode = TableFormerMode.ACCURATE
#pipeline = StandardPdfPipeline(pipeline_options=pipeline_options_)

converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options_)})

print('Import done')
import pprint


result = converter.convert(pdf_path)
doc = result.document

for table_ix, table in enumerate(doc.tables):
    table_df: pd.DataFrame = table.export_to_dataframe()
    
    page_number = table.prov[0].page_no if table.prov else 'N/A'
    
    print(f"--- Table {table_ix} (Page: {page_number}) ---")
    print(table_df.to_markdown()) # Display the table