from llama_index.core import StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
#from llama_index.core.vector_stores.qdrant import QdrantVectorStore

from qdrant_client import QdrantClient
import qdrant_client
import os
from llama_parse import LlamaParse
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import MarkdownElementNodeParser
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.retrievers import RecursiveRetriever
from llama_index.core.query_engine import RetrieverQueryEngine

# 1. Setup Qdrant for metadata filtering
client = QdrantClient(path="./qdrant_db2")

vector_store = QdrantVectorStore(
    client=client,
    collection_name="mtc_collection"
)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

parser = MarkdownElementNodeParser(llm=OpenAI(model="gpt-4o"))

documents = SimpleDirectoryReader(
    input_dir="./mtc_documents/",
    file_extractor={".pdf": parser}
).load_data()


# parser = LlamaParse(
#     api_key=os.environ['LLAMA_CLOUD_API_KEY'],
#     result_type="markdown",
#     parsing_instruction="""Extract MTC data with metadata tagging:
    
#     For each document, identify and tag:
#     - mtr_number: MTR/certificate number
#     - heat_number: Heat/lot number
#     - grade: Material grade (e.g., ASTM A182 F51)
#     - order_number: Customer order number
#     - date: Certificate date
#     - material_spec: Full material specification
    
#     For each table:
#     - table_type: "chemical_analysis" or "mechanical_properties"
#     - Preserve all rows with their values"""
# )


from llama_index.core.schema import IndexNode

def create_table_summary_nodes(documents):
    """Create summary nodes for each table to improve retrieval"""
    
    all_nodes = []
    
    for doc in documents:
        # Parse document
        parser = MarkdownElementNodeParser(llm=OpenAI(model="gpt-4o"))
        base_nodes, table_objects = parser.get_nodes_and_objects([doc])
        
        # For each table, create a summary node
        for table_obj in table_objects:
            # Generate summary using LLM
            summary_prompt = f"""Summarize this table from an MTC document:

{table_obj.text}

Create a concise summary that includes:
1. What type of data this table contains
2. Key values and ranges
3. Material specifications if present
4. Any notable measurements or properties

Summary:"""
            
            llm = OpenAI(model="gpt-4o",api_key=os.environ['OPEN_API_KEY'])
            summary = llm.complete(summary_prompt).text
            
            # Create index node pointing to original table
            summary_node = IndexNode(
                text=summary,
                index_id=table_obj.node_id,
                metadata={
                    **table_obj.metadata,
                    "type": "table_summary",
                    "original_table_id": table_obj.node_id
                }
            )
            
            #all_nodes.append(summary_node)
            #all_nodes.append(table_obj)
        
        # Add text nodes
        all_nodes.extend(base_nodes)
        #print(base_nodes)
    
    return all_nodes

# Use in index creation
enriched_nodes = create_table_summary_nodes(documents)
index = VectorStoreIndex(enriched_nodes,storage_context=storage_context,embed_model=OpenAIEmbedding(api_key=os.environ['OPEN_API_KEY']))
query_engine=index.as_query_engine(llm=OpenAI(model="gpt-4o",api_key=os.environ['OPEN_API_KEY']))

q = ['q','quit']
# Technical queries
# queries = [
#     "What is the Chemical analysis",
#     "Can you summarize the Order No: 634728 Mechanical properties?"
# ]

# for query in queries:
#     response = query_engine.query(query)
#     print(f"\nQ: {query}")
#     print(f"A: {response}\n")
#     print(f"Sources: {[node.metadata.get('file_name') for node in response.source_nodes]}")

while True:
    query = input("Enter your query (or 'q' to quit): ")
    if query.lower() in q:
        break
    response = query_engine.query(query)
    print(f"\nA: {response}\n")
    print(f"Sources: {[node.metadata.get('file_name') for node in response.source_nodes]}\n")
