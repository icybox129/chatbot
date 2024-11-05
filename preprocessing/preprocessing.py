import os
import shutil
import re
import yaml
import openai
import logging
from langchain.schema import Document
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import TextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # One level up from 'preprocessing'

DATA_PATH = os.path.join(BASE_DIR, "data/raw")
CHROMA_PATH = os.path.join(BASE_DIR, "data/chroma")

logging.basicConfig(level=logging.INFO, filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log'), filemode='w')

# Markdown Text Splitter
class MarkdownSplitter(TextSplitter):
    def split_text(self, text: str):
        # Wrap the text in a Document object and reuse split_documents method
        document = Document(page_content=text, metadata={})
        documents = [document]
        return self.split_documents(documents)

    def split_documents(self, documents: list[Document]):
        chunks = []
        for doc in documents:
            content = doc.page_content

            # Split based on Markdown headings (e.g., #, ##, ###)
            sections = re.split(r'(\n#{1,6} .*)', content)

            for i in range(1, len(sections), 2):
                heading = sections[i].strip()
                section_content = sections[i + 1] if i + 1 < len(sections) else ""

                # Keep code blocks intact
                section_chunks = self.split_by_code_blocks(f"{heading}\n{section_content}")

                for chunk in section_chunks:
                    chunk_metadata = {**doc.metadata}
                    chunk_metadata['heading'] = heading.strip('# ')
                    chunks.append(Document(page_content=chunk, metadata=chunk_metadata))
        
        return chunks

    def split_by_code_blocks(self, text: str):
        # Regex to match code blocks like ```terraform or other generic code blocks
        code_block_pattern = r'(```[\w]*[\s\S]*?```|`[^`\n]+`)'
        parts = re.split(code_block_pattern, text)

        chunks = []
        current_chunk = ""

        for part in parts:
            # If it's a code block (starts with ``` or ```terraform), treat it as a single chunk
            if part.startswith("```"):
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.append(part.strip())  # Keep code block intact
            else:
                current_chunk += part
                if len(current_chunk) > self._chunk_size:  # Access inherited chunk size
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
        
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

# Function to extract metadata from YAML frontmatter
def extract_metadata(content):
    if content.startswith("---"):
        frontmatter_end = content.find("---", 3)
        if frontmatter_end != -1:
            frontmatter = content[3:frontmatter_end].strip()
            logging.info(f"Extracted frontmatter: {frontmatter}")

            # Format the frontmatter
            pairs = re.findall(r'(\w+):\s*("[^"]*"|\|[-\s]*\w+.*?)(?=\s+\w+:|$)', frontmatter)
            formatted_lines = []
            for key, value in pairs:
                if value.startswith('|'):
                    formatted_lines.append(f"{key}: |")
                    for line in value.strip().split('\n'):
                        formatted_lines.append(f"  {line.strip()}")
                else:
                    formatted_lines.append(f"{key}: {value}")

            formatted_frontmatter = "\n".join(formatted_lines)
            metadata = yaml.safe_load(formatted_frontmatter)
            content = content[frontmatter_end + 3:].strip()  # Clean remaining content
            return metadata, content
    logging.error("No valid YAML frontmatter found.")
    return {}, content  # Return empty metadata if there's an error

# Function to load and process markdown documents
def load_documents():
    try:
        loader = DirectoryLoader(DATA_PATH, glob=["*.md", "*.markdown"])
        raw_documents = loader.load()
        documents = []

        for doc in raw_documents:
            metadata, content = extract_metadata(doc.page_content)
            documents.append(Document(page_content=content, metadata=metadata))
        
        num_loaded = len(documents)
        logging.info(f"Loaded {num_loaded} documents from {DATA_PATH}")
        return documents
    except Exception as e:
        logging.error(f"Error loading documents: {e}")
        return [] 

# Function to split the documents, using the custom splitter
def split_text(documents: list[Document]):
    text_splitter = MarkdownSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(documents)
    logging.info(f"Split {len(documents)} documents into {len(chunks)} chunks")
    return chunks

# Function to save chunks into Chroma vector store
def save_to_chroma(chunks: list[Document]):
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        logging.info(f"Deleted existing Chroma database at {CHROMA_PATH}")

    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        db = Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
        logging.info(f"Saved {len(chunks)} chunks to Chroma database at {CHROMA_PATH}")
    except Exception as e:
        logging.error(f"Error saving to Chroma: {e}")

# Main function to run the process
def main():
    logging.info("Starting document preprocessing...")
    documents = load_documents()
    if documents:
        chunks = split_text(documents)
        save_to_chroma(chunks)
    logging.info("Document preprocessing complete") 

if __name__ == "__main__":
    main()
