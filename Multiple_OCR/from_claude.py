"""
Docling PDF Table Parser for Complex Layouts
Version: docling 2.54.0

Handles:
- Multiple tables in single large box
- Tables separated only by headings (row-wise, not column-wise)
- No OCR needed (digital PDFs)
- Complex table structures
"""

import pandas as pd
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from pathlib import Path
import json
from typing import List, Dict, Tuple
import re

# ============================================
# CONFIGURATION FOR COMPLEX TABLES
# ============================================

class DoclingTableExtractor:
    """
    Advanced table extraction with Docling
    Optimized for complex, nested table layouts
    """
    
    def __init__(
        self,
        table_mode: str = "accurate",  # or "fast"
        do_table_structure_recognition: bool = True,
        do_ocr: bool = False  # Disabled for digital PDFs
    ):
        """
        Initialize Docling converter with optimal settings
        
        Args:
            table_mode: "accurate" for complex tables, "fast" for simple ones
            do_table_structure_recognition: Enable for better table parsing
            do_ocr: False for digital PDFs (you don't need OCR)
        """
        
        # Configure pipeline for complex tables
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_table_structure = do_table_structure_recognition
        pipeline_options.do_ocr = do_ocr
        
        # Use accurate mode for complex tables
        if table_mode == "accurate":
            pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        else:
            pipeline_options.table_structure_options.mode = TableFormerMode.FAST
        
        # Initialize converter
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )
    
    def extract_tables_from_pdf(
        self, 
        pdf_path: str,
        split_by_headings: bool = True
    ) -> List[Dict]:
        """
        Extract all tables from PDF
        
        Args:
            pdf_path: Path to PDF file
            split_by_headings: Try to split tables based on heading detection
        
        Returns:
            List of dictionaries containing table data and metadata
        """
        # Convert PDF
        result = self.converter.convert(pdf_path)
        
        tables = []
        
        # Extract tables from document
        for idx, (table_element, table_data) in enumerate(result.document.iterate_items()):
            if table_element.label == "table":
                # Get table as DataFrame
                print("---------------\n"*3)
                print(table_data)
                df = table_data.export_to_dataframe()
                
                # Get table metadata
                metadata = {
                    "table_id": idx,
                    "page_number": table_element.prov[0].page_no if table_element.prov else None,
                    "bbox": table_element.prov[0].bbox.as_tuple() if table_element.prov else None,
                    "caption": self._extract_caption(table_element),
                }
                
                tables.append({
                    "dataframe": df,
                    "metadata": metadata,
                    "raw_data": table_data
                })
        
        # Try to split tables by headings if requested
        if split_by_headings:
            tables = self._split_tables_by_headings(tables, result)
        
        return tables
    
    def _extract_caption(self, table_element) -> str:
        """Extract table caption/heading"""
        if hasattr(table_element, 'caption') and table_element.caption:
            return table_element.caption.text
        return ""
    
    def _split_tables_by_headings(
        self, 
        tables: List[Dict], 
        result
    ) -> List[Dict]:
        """
        Split tables that are separated by headings within the same large box
        
        This handles the case where multiple logical tables exist in one physical table
        """
        split_tables = []
        
        for table_dict in tables:
            df = table_dict["dataframe"]
            
            # Find rows that look like headings (all bold, merged cells, etc.)
            heading_indices = self._detect_heading_rows(df)
            
            if len(heading_indices) > 0:
                # Split the table at heading rows
                sub_tables = self._split_dataframe_at_indices(df, heading_indices)
                
                for i, sub_df in enumerate(sub_tables):
                    split_table = table_dict.copy()
                    split_table["dataframe"] = sub_df
                    split_table["metadata"]["sub_table_id"] = i
                    split_table["metadata"]["heading"] = heading_indices[i] if i < len(heading_indices) else ""
                    split_tables.append(split_table)
            else:
                split_tables.append(table_dict)
        
        return split_tables
    
    def _detect_heading_rows(self, df: pd.DataFrame) -> List[int]:
        """
        Detect rows that are likely headings
        
        Heuristics:
        - Row with mostly NaN except first column
        - Row where first cell is bold/formatted differently
        - Row with keywords like "Table", "Section", etc.
        """
        heading_indices = []
        
        for idx, row in df.iterrows():
            # Check if row has mostly empty cells except first
            non_null_count = row.notna().sum()
            
            if non_null_count <= 2:  # Only 1-2 cells filled
                first_cell = str(row.iloc[0]).strip()
                
                # Check for heading keywords
                heading_keywords = [
                    'table', 'section', 'part', 'category', 
                    'summary', 'details', 'overview'
                ]
                
                if any(keyword in first_cell.lower() for keyword in heading_keywords):
                    heading_indices.append(idx)
                # Or if it's a short text (likely a heading)
                elif len(first_cell) < 50 and first_cell.isupper():
                    heading_indices.append(idx)
        
        return heading_indices
    
    def _split_dataframe_at_indices(
        self, 
        df: pd.DataFrame, 
        indices: List[int]
    ) -> List[pd.DataFrame]:
        """Split DataFrame at specified row indices"""
        if not indices:
            return [df]
        
        sub_dfs = []
        start_idx = 0
        
        for split_idx in indices:
            if split_idx > start_idx:
                sub_df = df.iloc[start_idx:split_idx].copy()
                if not sub_df.empty:
                    sub_dfs.append(sub_df)
            start_idx = split_idx + 1
        
        # Add remaining rows
        if start_idx < len(df):
            sub_df = df.iloc[start_idx:].copy()
            if not sub_df.empty:
                sub_dfs.append(sub_df)
        
        return sub_dfs
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean extracted DataFrame
        - Remove empty rows/columns
        - Handle merged cells
        - Fix headers
        """
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Remove completely empty columns
        df = df.dropna(axis=1, how='all')
        
        # Reset index
        df = df.reset_index(drop=True)
        
        # Try to detect if first row should be header
        if self._is_likely_header(df.iloc[0] if len(df) > 0 else None):
            df.columns = df.iloc[0]
            df = df.iloc[1:].reset_index(drop=True)
        
        # Remove duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    
    def _is_likely_header(self, row) -> bool:
        """Check if a row is likely a header"""
        if row is None:
            return False
        
        # Check if most cells are strings and non-numeric
        try:
            numeric_count = sum(1 for val in row if pd.notna(val) and str(val).replace('.', '').isdigit())
            return numeric_count < len(row) / 2
        except:
            return False
    
    def save_tables(
        self, 
        tables: List[Dict], 
        output_dir: str = "./extracted_tables"
    ):
        """
        Save extracted tables to CSV files
        
        Args:
            tables: List of table dictionaries
            output_dir: Directory to save CSV files
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for i, table_dict in enumerate(tables):
            df = table_dict["dataframe"]
            metadata = table_dict["metadata"]
            
            # Generate filename
            page = metadata.get("page_number", "unknown")
            heading = metadata.get("heading", "")
            heading_slug = re.sub(r'[^\w\s-]', '', heading)[:30]
            
            if heading_slug:
                filename = f"table_{i}_page{page}_{heading_slug}.csv"
            else:
                filename = f"table_{i}_page{page}.csv"
            
            filepath = Path(output_dir) / filename
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            print(f"✓ Saved: {filename}")
            
            # Also save metadata
            metadata_file = filepath.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)


# ============================================
# ADVANCED: Handle Large Encapsulating Box
# ============================================

class ComplexTableSplitter:
    """
    Specialized splitter for tables within a large encapsulating box
    """
    
    @staticmethod
    def split_by_visual_gaps(
        df: pd.DataFrame, 
        gap_threshold: int = 2
    ) -> List[pd.DataFrame]:
        """
        Split table by detecting visual gaps (multiple empty rows)
        
        Args:
            df: DataFrame to split
            gap_threshold: Number of consecutive empty rows to consider a gap
        """
        # Find rows that are completely empty
        empty_rows = df.isna().all(axis=1)
        
        # Find sequences of empty rows
        gaps = []
        current_gap_start = None
        current_gap_length = 0
        
        for idx, is_empty in empty_rows.items():
            if is_empty:
                if current_gap_start is None:
                    current_gap_start = idx
                current_gap_length += 1
            else:
                if current_gap_length >= gap_threshold:
                    gaps.append((current_gap_start, idx))
                current_gap_start = None
                current_gap_length = 0
        
        # Split at gaps
        if not gaps:
            return [df]
        
        sub_tables = []
        start = 0
        
        for gap_start, gap_end in gaps:
            if gap_start > start:
                sub_table = df.iloc[start:gap_start].copy()
                if not sub_table.empty:
                    sub_tables.append(sub_table)
            start = gap_end
        
        # Add remaining
        if start < len(df):
            sub_table = df.iloc[start:].copy()
            if not sub_table.empty:
                sub_tables.append(sub_table)
        
        return sub_tables
    
    @staticmethod
    def split_by_column_structure_change(df: pd.DataFrame) -> List[pd.DataFrame]:
        """
        Split tables where column structure changes
        (e.g., 3 columns → 5 columns = different tables)
        """
        # Analyze column usage patterns
        column_patterns = []
        
        for idx, row in df.iterrows():
            non_null_cols = row.notna().sum()
            column_patterns.append(non_null_cols)
        
        # Find significant changes in pattern
        split_points = []
        for i in range(1, len(column_patterns)):
            if abs(column_patterns[i] - column_patterns[i-1]) >= 2:
                split_points.append(i)
        
        # Split at change points
        if not split_points:
            return [df]
        
        sub_tables = []
        start = 0
        
        for split_point in split_points:
            sub_table = df.iloc[start:split_point].copy()
            if not sub_table.empty:
                sub_tables.append(sub_table)
            start = split_point
        
        # Add remaining
        if start < len(df):
            sub_table = df.iloc[start:].copy()
            if not sub_table.empty:
                sub_tables.append(sub_table)
        
        return sub_tables


# ============================================
# USAGE EXAMPLES
# ============================================

def example_basic_extraction():
    """Basic extraction example"""
    
    # Initialize extractor
    extractor = DoclingTableExtractor(
        table_mode="accurate",  # Use accurate mode for complex tables
        do_table_structure_recognition=True,
        do_ocr=False  # No OCR for digital PDFs
    )
    
    # Extract tables
    tables = extractor.extract_tables_from_pdf("your_file.pdf")
    
    print(f"✓ Extracted {len(tables)} tables")
    
    # Process each table
    for i, table_dict in enumerate(tables):
        df = table_dict["dataframe"]
        metadata = table_dict["metadata"]
        
        print(f"\n{'='*60}")
        print(f"Table {i + 1}")
        print(f"Page: {metadata['page_number']}")
        print(f"Caption: {metadata['caption']}")
        print(f"Shape: {df.shape}")
        print(f"{'='*60}")
        print(df.head())
    
    # Save all tables
    extractor.save_tables(tables, output_dir="./extracted_tables")
    
    return tables


def example_complex_nested_tables():
    """Example for complex nested tables in large box"""
    
    # Initialize extractor
    extractor = DoclingTableExtractor(table_mode="accurate")
    
    # Extract tables
    tables = extractor.extract_tables_from_pdf("complex_file.pdf", split_by_headings=True)
    
    # Further split by visual gaps
    splitter = ComplexTableSplitter()
    
    all_sub_tables = []
    for table_dict in tables:
        df = table_dict["dataframe"]
        
        # Try splitting by visual gaps
        sub_dfs = splitter.split_by_visual_gaps(df, gap_threshold=2)
        
        # If still too complex, try splitting by column structure
        if len(sub_dfs) == 1 and len(df) > 10:
            sub_dfs = splitter.split_by_column_structure_change(df)
        
        # Clean each sub-table
        for sub_df in sub_dfs:
            cleaned_df = extractor.clean_dataframe(sub_df)
            all_sub_tables.append({
                "dataframe": cleaned_df,
                "metadata": table_dict["metadata"]
            })
    
    print(f"✓ Extracted and split into {len(all_sub_tables)} tables")
    
    # Save
    extractor.save_tables(all_sub_tables)
    
    return all_sub_tables


def example_custom_splitting():
    """Example with custom splitting logic"""
    
    extractor = DoclingTableExtractor()
    tables = extractor.extract_tables_from_pdf("your_file.pdf")
    
    for table_dict in tables:
        df = table_dict["dataframe"]
        
        # Custom logic: Split where first column contains "SECTION"
        split_indices = []
        for idx, row in df.iterrows():
            if "SECTION" in str(row.iloc[0]).upper():
                split_indices.append(idx)
        
        if split_indices:
            sub_dfs = extractor._split_dataframe_at_indices(df, split_indices)
            print(f"Split into {len(sub_dfs)} sub-tables based on 'SECTION' keyword")
            
            for i, sub_df in enumerate(sub_dfs):
                print(f"\nSub-table {i+1}:")
                print(sub_df.head())


# ============================================
# COMPLETE PIPELINE
# ============================================

def complete_pipeline(pdf_path: str, output_dir: str = "./tables"):
    """
    Complete pipeline for complex table extraction
    """
    print(f"📄 Processing: {pdf_path}")
    print("="*60)
    
    # Step 1: Initialize extractor
    extractor = DoclingTableExtractor(
        table_mode="accurate",
        do_table_structure_recognition=True,
        do_ocr=False
    )
    
    # Step 2: Extract tables
    print("🔍 Extracting tables...")
    tables = extractor.extract_tables_from_pdf(pdf_path, split_by_headings=True)
    print(f"✓ Found {len(tables)} tables")
    
    # Step 3: Further split complex tables
    print("\n🔪 Splitting complex tables...")
    splitter = ComplexTableSplitter()
    final_tables = []
    
    for table_dict in tables:
        df = table_dict["dataframe"]
        
        # Try multiple splitting strategies
        sub_dfs = splitter.split_by_visual_gaps(df)
        
        if len(sub_dfs) == 1:
            sub_dfs = splitter.split_by_column_structure_change(df)
        
        for sub_df in sub_dfs:
            cleaned = extractor.clean_dataframe(sub_df)
            if len(cleaned) > 0:  # Only keep non-empty tables
                final_tables.append({
                    "dataframe": cleaned,
                    "metadata": table_dict["metadata"]
                })
    
    print(f"✓ Split into {len(final_tables)} final tables")
    
    # Step 4: Save results
    print(f"\n💾 Saving to {output_dir}...")
    extractor.save_tables(final_tables, output_dir)
    
    # Step 5: Summary
    print("\n" + "="*60)
    print("📊 EXTRACTION SUMMARY")
    print("="*60)
    for i, table_dict in enumerate(final_tables):
        df = table_dict["dataframe"]
        metadata = table_dict["metadata"]
        print(f"\nTable {i+1}:")
        print(f"  - Page: {metadata.get('page_number', 'N/A')}")
        print(f"  - Shape: {df.shape}")
        print(f"  - Columns: {list(df.columns)[:5]}...")  # First 5 columns
    
    return final_tables


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    # Example 1: Basic extraction
    # tables = example_basic_extraction()
    
    # Example 2: Complex nested tables
    # tables = example_complex_nested_tables()
    
    # Example 3: Complete pipeline
    tables = complete_pipeline(
        pdf_path=r"c:\Users\hahtsham\work\ICR\Multiple_OCR\sample_with_tables.pdf",
        output_dir="./extracted_tables"
    )
    
    # Access DataFrames
    for i, table_dict in enumerate(tables):
        df = table_dict["dataframe"]
        print(f"\nTable {i+1} DataFrame:")
        print(df.head())
        
        # You can now use these DataFrames for analysis
        # df.describe()
        # df.to_sql(...)
        # etc.