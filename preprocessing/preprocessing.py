"""
Preprocessing Module for ChromaDB Knowledge Base

This module processes markdown documents to create a searchable ChromaDB knowledge base.
It supports two modes of operation:
1. Local mode: Processes documents from the local filesystem and stores the ChromaDB locally.
2. S3 mode: Downloads documents from an S3 bucket, processes them, and uploads the resulting
   ChromaDB back to S3.

Key features:
- Downloads and uploads documents to/from S3.
- Splits documents into chunks using custom markdown splitting logic.
- Extracts metadata from YAML frontmatter.
- Supports saving ChromaDB locally or to S3.

Classes:
- MarkdownSplitter: Custom splitter for markdown documents, preserving code blocks and headings.

Functions:
- download_s3_folder: Downloads a folder from S3 to a local directory.
- upload_folder_to_s3: Uploads a local folder to S3 under a specified prefix.
- extract_metadata: Extracts metadata from YAML frontmatter in markdown files.
- load_documents_from_local: Loads markdown documents from the local filesystem.
- load_documents_from_s3: Downloads and loads markdown documents from S3.
- split_text: Splits loaded documents into smaller chunks for vectorization.
- save_to_chroma_local: Saves the ChromaDB locally.
- save_to_chroma_s3: Saves the ChromaDB to S3.
- main: Entry point to preprocess documents, supporting both local and S3 modes.

Dependencies:
- Boto3 for S3 interactions.
- LangChain for document and embedding management.
- OpenAI API for embeddings.
- PyYAML for metadata extraction.

Environment variables:
- OPENAI_API_KEY: Required for generating embeddings.
"""

import os
import shutil
import re
import yaml
import openai
import logging
import boto3
from langchain.schema import Document
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import TextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables (e.g. OPENAI_API_KEY)
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# AWS S3 SETUP
# ─────────────────────────────────────────────────────────────────────────────

# Specifying the S3 bucket name and folder paths for raw docs and Chroma data
S3_BUCKET_NAME = "nick-terraform-test-docs"
S3_RAW_PREFIX = "data/raw"     # S3 prefix/folder for raw MD docs
S3_CHROMA_PREFIX = "data/chroma"  # S3 prefix/folder for the Chroma DB

# Create S3 client to interact with S3 on AWS via the API
s3_client = boto3.client("s3")

# ─────────────────────────────────────────────────────────────────────────────
# LOCAL PATHS (For local processing, not used in S3 mode)
# ─────────────────────────────────────────────────────────────────────────────

# Set the base directory 'one level up' from the current file
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Define local paths for raw data and Chroma DB
DATA_PATH = os.path.join(BASE_DIR, "data/raw")
CHROMA_PATH = os.path.join(BASE_DIR, "data/chroma")

# Ensure these directories exist
paths = [DATA_PATH, CHROMA_PATH]
for path in paths:
    os.makedirs(path, exist_ok=True)

# Configure logging to write logs to app.log in the same directory
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log"), # Absolute path to app.log
    filemode="w"
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS FOR S3
# ─────────────────────────────────────────────────────────────────────────────

def download_s3_folder(bucket_name: str, s3_prefix: str, local_dir: str):
    """
    Download all objects under a prefix from S3 into a local directory.

    :param bucket_name: Name of the S3 bucket.
    :param s3_prefix: The folder path/prefix in S3 from which files will be downloaded.
    :param local_dir: The local directory where files will be saved.
    """

    # Lists all objects in the S3 bucket under the given prefix
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                # Skip "directories" in S3 (keys that end with "/")
                if key.endswith("/"):
                    continue

                relative_path = key[len(s3_prefix) :].lstrip("/")
                local_path = os.path.join(local_dir, relative_path)

                # Create local folder if it doesn't exist
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Download
                logging.info(f"Downloading s3://{bucket_name}/{key} to {local_path}")
                s3_client.download_file(bucket_name, key, local_path)

def upload_folder_to_s3(local_dir: str, bucket_name: str, s3_prefix: str):
    """
    Upload all files from a local directory to S3 under a given prefix.

    :param local_dir: Path to the local directory to upload.
    :param bucket_name: Name of the S3 bucket.
    :param s3_prefix: The folder path/prefix in S3 to which files will be uploaded.
    """
    # Scans the local directory and all subdirectories
    for root, dirs, files in os.walk(local_dir):
        # For every file, create a local path, a relative path, and an S3 key
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, start=local_dir)
            s3_key = os.path.join(s3_prefix, relative_path).replace("\\", "/")

            logging.info(f"Uploading {local_path} to s3://{bucket_name}/{s3_key}")
            s3_client.upload_file(local_path, bucket_name, s3_key)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM MARKDOWN SPLITTER
# ─────────────────────────────────────────────────────────────────────────────
class MarkdownSplitter(TextSplitter):
    """
    A custom text splitter that splits Markdown documents based on headings 
    and preserves code blocks.
    """
    # Split a single string of text into a list of documents
    def split_text(self, text: str):
        document = Document(page_content=text, metadata={})
        documents = [document]
        return self.split_documents(documents)
    
    # Split a list of documents into smaller chunks
    def split_documents(self, documents: list[Document]):
        chunks = []
        for doc in documents:
            content = doc.page_content

            # Split based on Markdown headings (e.g., #, ##, ###)
            sections = re.split(r"(\n#{1,6} .*)", content)

            # Process each heading and its content so we can keep code blocks intact
            for i in range(1, len(sections), 2):
                heading = sections[i].strip()
                section_content = sections[i + 1] if i + 1 < len(sections) else ""

                # Keep code blocks intact
                section_chunks = self.split_by_code_blocks(f"{heading}\n{section_content}")

                # Chunks documents by heading and preserves code blocks and its metadata
                for chunk in section_chunks:
                    chunk_metadata = {**doc.metadata}
                    chunk_metadata["heading"] = heading.strip("# ")
                    chunks.append(Document(page_content=chunk, metadata=chunk_metadata))

        return chunks

    def split_by_code_blocks(self, text: str):
        """
        Split the given text into chunks, treating code blocks as single units.
        Example: ```terraform code...``` or inline `code`.
        """
        # Regex to match full code blocks (```...```) or inline code (`...`)
        code_block_pattern = r"(```[\w]*[\s\S]*?```|`[^`\n]+`)"
        parts = re.split(code_block_pattern, text)

        chunks = []
        current_chunk = ""

        for part in parts:
            # If it's a code block (starts with ```), treat it as a single chunk
            if part.startswith("```"):
                # If there's accumulated text (not part of a code block), push it as a chunk first
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.append(part.strip())  # Keep code block intact
            else:
                # Accumulate text in current_chunk
                current_chunk += part
                # If the accumulated text exceeds the splitter's chunk size, flush it
                if len(current_chunk) > self._chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

        # Add any leftover text
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION TO EXTRACT METADATA FROM YAML FRONTMATTER
# ─────────────────────────────────────────────────────────────────────────────
def extract_metadata(content):
    """
    Extract YAML frontmatter from a markdown file and return it 
    as metadata along with the remaining content.
    """
    # Check if the content starts with the YAML frontmatter delimiter '---'
    if content.startswith("---"):
        # Find the ending delimiter '---' for the frontmatter, starting from character index 3
        frontmatter_end = content.find("---", 3)
        if frontmatter_end != -1:
            # Extract the frontmatter portion by skipping the starting '---' and trimming whitespace
            frontmatter = content[3:frontmatter_end].strip()
            
            # Use a regular expression to find key-value pairs in the frontmatter.
            pairs = re.findall(
                r'(\w+):\s*("[^"]*"|\|[-\s]*\w+.*?)(?=\s+\w+:|$)',
                frontmatter,
            )
            formatted_lines = []
            # Process each found key-value pair to format them as proper YAML lines.
            for key, value in pairs:
                # If the value indicates a literal block (starts with '|'), handle multi-line formatting.
                if value.startswith("|"):
                    # Add the key with a literal block indicator to the formatted lines.
                    formatted_lines.append(f"{key}: |")
                    # Split the literal block into individual lines and indent each line as required by YAML.
                    for line in value.strip().split("\n"):
                        formatted_lines.append(f"  {line.strip()}")
                else:
                    # Otherwise, simply add the key-value pair as a single line.
                    formatted_lines.append(f"{key}: {value}")

            # Combine all formatted YAML lines into a single string.
            formatted_frontmatter = "\n".join(formatted_lines)
            # Parse the YAML string into a Python dictionary safely.
            metadata = yaml.safe_load(formatted_frontmatter)
            # Remove the frontmatter from the original content and trim any excess whitespace.
            content = content[frontmatter_end + 3:].strip()
            return metadata, content

    logging.error("No valid YAML frontmatter found.")
    # Return an empty dictionary for metadata along with the original content.
    return {}, content


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DOCUMENTS
# Option A: Local DirectoryLoader (comment out if using S3)
# Option B: Download from S3 then use local DirectoryLoader
# ─────────────────────────────────────────────────────────────────────────────

def load_documents_from_local():
    """
    Load markdown files from the local DATA_PATH directory. 
    Extract metadata from each document, then return a list of Document objects.
    """
    # Import the necessary document loaders from LangChain.
    from langchain.document_loaders import DirectoryLoader, TextLoader
    try:
        # Create a DirectoryLoader that searches for markdown files in DATA_PATH
        loader = DirectoryLoader(
            DATA_PATH,
            glob=["*.md", "*.markdown"],
            loader_cls=TextLoader
        )

        raw_documents = loader.load()

        documents = []
        # Iterate over each raw document to extract metadata and clean content.
        for doc in raw_documents:
            # Call extract_metadata to separate YAML frontmatter (metadata) and the content.
            metadata, content = extract_metadata(doc.page_content)
            # Construct a Document object with the cleaned content and its metadata.
            documents.append(Document(page_content=content, metadata=metadata))
        # Return the list of processed Document objects.
        return documents
    except Exception as e:
        logging.error(f"Error loading documents: {e}")
        return []

def load_documents_from_s3():
    """
    Download markdown files from an S3 bucket, then load them 
    locally to extract metadata and create Document objects.
    """
    from langchain.document_loaders import DirectoryLoader, TextLoader

    temp_dir = Path("temp_s3_raw")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    # Recreate the temporary directory ensuring parent directories exist
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Download files from S3 to the temporary directory
        download_s3_folder(S3_BUCKET_NAME, S3_RAW_PREFIX, str(temp_dir))

        # Load the downloaded documents locally as text files
        loader = DirectoryLoader(
            str(temp_dir),
            glob=["*.md", "*.markdown"],
            loader_cls=TextLoader
        )

        raw_documents = loader.load()

        documents = []
        # Extract YAML frontmatter metadata and content from each document.
        for doc in raw_documents:
            metadata, content = extract_metadata(doc.page_content)
            # Create Document objects with cleaned content and corresponding metadata
            documents.append(Document(page_content=content, metadata=metadata))

        # Return the list of processed Document objects.
        return documents
    except Exception as e:
        logging.error(f"Error loading documents from S3: {e}")
        return []
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


# ─────────────────────────────────────────────────────────────────────────────
# SPLIT TEXT
# ─────────────────────────────────────────────────────────────────────────────
def split_text(documents: list[Document]):
    """
    Split documents into smaller chunks using the custom MarkdownSplitter.
    Each chunk can then be turned into a vector for indexing in Chroma.
    """
    text_splitter = MarkdownSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(documents)
    logging.info(f"Split {len(documents)} documents into {len(chunks)} chunks")
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# SAVE TO CHROMA
# Option A: Save locally
# Option B: Save to local, then upload to S3
# ─────────────────────────────────────────────────────────────────────────────

def save_to_chroma_local(chunks: list[Document]):
    """
    Save the generated document chunks to a local Chroma database.
    """
    # Delete existing folder, to avoid conflicts
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        logging.info(f"Deleted existing Chroma database at {CHROMA_PATH}")

    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        # Create Chroma DB from the document chunks
        db = Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
        db.persist() # Write the data to disk
        logging.info(f"Saved {len(chunks)} chunks to Chroma database at {CHROMA_PATH}")
    except Exception as e:
        logging.error(f"Error saving to Chroma: {e}")

def empty_s3_prefix(bucket_name: str, prefix: str):
    """
    Deletes all objects under the given S3 prefix before uploading new data.
    The token allows you to retrieve the next page of results.
    """
    continuation_token = None
    while True:
        # Make a call to list_objects_v2.
        # If continuation_token is set then it's used to retrieve the next page of results.
        if continuation_token:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name, 
                Prefix=prefix, 
                ContinuationToken=continuation_token
            )
        else:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name, 
                Prefix=prefix
            )

        # If no objects are found in the response, break out of the loop.
        if 'Contents' not in response:
            break

        # Create a list of object keys that will be deleted.
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        # Delete the current batch of objects.
        s3_client.delete_objects(
            Bucket=bucket_name,
            Delete={'Objects': objects_to_delete}
        )

        # Check if there is a continuation token indicating more objects to process.
        if response.get('NextContinuationToken'):
            continuation_token = response['NextContinuationToken']
        else:
            break

def save_to_chroma_s3(chunks: list[Document]):
    """
    Save the generated document chunks to Chroma in a local temporary 
    directory, then upload that directory to S3.
    """
    temp_chroma_dir = Path("temp_s3_chroma")
    if temp_chroma_dir.exists():
        shutil.rmtree(temp_chroma_dir)
    temp_chroma_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create Chroma DB from the document chunks in a temporary folder
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        db = Chroma.from_documents(
            chunks,
            embeddings,
            persist_directory=str(temp_chroma_dir)
        )
        db.persist()
        logging.info(f"Saved {len(chunks)} chunks to a local temp Chroma db at {temp_chroma_dir}")

        # Remove any old data from the S3 Chroma folder
        empty_s3_prefix(S3_BUCKET_NAME, S3_CHROMA_PREFIX)
        logging.info(f"Deleted all objects in s3://{S3_BUCKET_NAME}/{S3_CHROMA_PREFIX}")

        # Upload the new Chroma DB files to S3
        upload_folder_to_s3(str(temp_chroma_dir), S3_BUCKET_NAME, S3_CHROMA_PREFIX)
        logging.info(f"Uploaded Chroma DB to s3://{S3_BUCKET_NAME}/{S3_CHROMA_PREFIX}")

    except Exception as e:
        logging.error(f"Error saving to Chroma in S3: {e}")

    finally:
        if temp_chroma_dir.exists():
            shutil.rmtree(temp_chroma_dir)
            logging.info("Removed temporary directory for S3 Chroma.")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main(use_s3=True):
    """
    Main function to drive the entire preprocessing pipeline.
    By default, it uses S3 mode (use_s3=True) to load documents from S3 
    and save the Chroma DB back to S3. Set use_s3=False to use local mode.
    """
    logging.info("Starting document preprocessing...")

    if not use_s3:
        # LOCAL MODE
        logging.info("Using LOCAL mode for load and save.")
        documents = load_documents_from_local()
        if documents:
            chunks = split_text(documents)
            save_to_chroma_local(chunks)

    else:
        # S3 MODE
        logging.info("Using S3 mode for load and save.")
        documents = load_documents_from_s3()
        if documents:
            chunks = split_text(documents)
            save_to_chroma_s3(chunks)

    logging.info("Document preprocessing complete")


if __name__ == "__main__":
    # Toggle True/False to switch between S3 mode and local mode
    main(use_s3=True)
    # main(use_s3=False)