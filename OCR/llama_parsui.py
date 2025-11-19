from llama_parse import LlamaParse
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import MarkdownElementNodeParser
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
import os
from dotenv import load_dotenv  
load_dotenv()

# 1. PARSE PDFs with LlamaParse (preserves table structure)
parser = LlamaParse(
    api_key=os.environ['LLAMA_CLOUD_API_KEY'],
    result_type="markdown",  # Critical for tables
    parsing_instruction="""Parse Material Test Certificates with these requirements:
    - Preserve all table structures (chemical analysis, mechanical properties)
    - Keep numerical values exact with all decimals
    - Maintain relationships between headers and values
    - Extract metadata: MTR number, heat number, order number, dates, grades
    - Keep units associated with values (MPa, %, HB, etc.)"""
)

# Parse all MTCs
file_extractor = {".pdf": parser}
documents = SimpleDirectoryReader(
    input_dir="./mtc_documents/",
    file_extractor=file_extractor
).load_data()

print(f"Loaded {len(documents)} MTC documents")

# 2. TABLE-AWARE CHUNKING (Critical for RAG with tables)
# Use MarkdownElementNodeParser - it understands table boundaries
node_parser = MarkdownElementNodeParser(
    llm=OpenAI(model="gpt-4o",api_key=os.environ['OPEN_API_KEY']),
    num_workers=8
)

nodes = node_parser.get_nodes_from_documents(documents)
base_nodes, objects = node_parser.get_nodes_and_objects(nodes)

print(f"Created {len(base_nodes)} base nodes and {len(objects)} table objects")

# 3. BUILD RECURSIVE RETRIEVER (handles tables + text)
from llama_index.core.retrievers import RecursiveRetriever
from llama_index.core.query_engine import RetrieverQueryEngine

# Create index from base nodes
base_index = VectorStoreIndex(base_nodes)
base_retriever = base_index.as_retriever(similarity_top_k=5)

# Recursive retriever that can fetch full tables
recursive_retriever = RecursiveRetriever(
    "vector",
    retriever_dict={"vector": base_retriever},
    node_dict={node.node_id: node for node in objects},
    verbose=True
)

# 4. CREATE QUERY ENGINE
query_engine = RetrieverQueryEngine.from_args(
    recursive_retriever,
    llm=OpenAI(model="gpt-4o",api_key=os.environ['OPEN_API_KEY']),
)

# 5. QUERY YOUR MTC DATABASE
response = query_engine.query(
    "What is the carbon content in heat number 795247?"
)
print(response)

response = query_engine.query(
    "Show me all mechanical properties for ASTM A182 F51 grade"
)
print(response)

response = query_engine.query(
    "Which MTCs have tensile strength above 620 MPa?"
)
print(response)
