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
# from langchain_community.document_loaders import DirectoryLoader  # Commenting out local loader
from langchain.text_splitter import TextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# AWS S3 SETUP: Provide your bucket name and optional AWS region here
# ─────────────────────────────────────────────────────────────────────────────
S3_BUCKET_NAME = "nick-terraform-test-docs"
S3_RAW_PREFIX = "data/raw"     # S3 prefix/folder for raw MD docs
S3_CHROMA_PREFIX = "data/chroma"  # S3 prefix/folder for the Chroma DB

# Create S3 client
s3_client = boto3.client("s3")

# ─────────────────────────────────────────────────────────────────────────────
# LOCAL PATHS (Comment out if you do not need local approach)
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # One level up from 'preprocessing'
DATA_PATH = os.path.join(BASE_DIR, "data/raw")
CHROMA_PATH = os.path.join(BASE_DIR, "data/chroma")

paths = [DATA_PATH, CHROMA_PATH]
for path in paths:
    os.makedirs(path, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log"),
    filemode="w"
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS FOR S3
# ─────────────────────────────────────────────────────────────────────────────

def download_s3_folder(bucket_name: str, s3_prefix: str, local_dir: str):
    """
    Download all objects under a prefix from S3 into a local directory.
    """
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
    """
    for root, dirs, files in os.walk(local_dir):
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
            sections = re.split(r"(\n#{1,6} .*)", content)

            for i in range(1, len(sections), 2):
                heading = sections[i].strip()
                section_content = sections[i + 1] if i + 1 < len(sections) else ""

                # Keep code blocks intact
                section_chunks = self.split_by_code_blocks(f"{heading}\n{section_content}")

                for chunk in section_chunks:
                    chunk_metadata = {**doc.metadata}
                    chunk_metadata["heading"] = heading.strip("# ")
                    chunks.append(Document(page_content=chunk, metadata=chunk_metadata))

        return chunks

    def split_by_code_blocks(self, text: str):
        # Regex to match code blocks like ```terraform or other generic code blocks
        code_block_pattern = r"(```[\w]*[\s\S]*?```|`[^`\n]+`)"
        parts = re.split(code_block_pattern, text)

        chunks = []
        current_chunk = ""

        for part in parts:
            # If it's a code block (starts with ```), treat it as a single chunk
            if part.startswith("```"):
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.append(part.strip())  # Keep code block intact
            else:
                current_chunk += part
                if len(current_chunk) > self._chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION TO EXTRACT METADATA FROM YAML FRONTMATTER
# ─────────────────────────────────────────────────────────────────────────────
def extract_metadata(content):
    if content.startswith("---"):
        frontmatter_end = content.find("---", 3)
        if frontmatter_end != -1:
            frontmatter = content[3:frontmatter_end].strip()
            logging.info(f"Extracted frontmatter: {frontmatter}")

            # Format the frontmatter
            pairs = re.findall(
                r'(\w+):\s*("[^"]*"|\|[-\s]*\w+.*?)(?=\s+\w+:|$)',
                frontmatter,
            )
            formatted_lines = []
            for key, value in pairs:
                if value.startswith("|"):
                    formatted_lines.append(f"{key}: |")
                    for line in value.strip().split("\n"):
                        formatted_lines.append(f"  {line.strip()}")
                else:
                    formatted_lines.append(f"{key}: {value}")

            formatted_frontmatter = "\n".join(formatted_lines)
            metadata = yaml.safe_load(formatted_frontmatter)
            content = content[frontmatter_end + 3 :].strip()  # Clean remaining content
            return metadata, content

    logging.error("No valid YAML frontmatter found.")
    return {}, content  # Return empty metadata if there's an error


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DOCUMENTS
# Option A: Local DirectoryLoader (comment out if using S3)
# Option B: Download from S3 then use local DirectoryLoader
# ─────────────────────────────────────────────────────────────────────────────

def load_documents_from_local():
    """
    ORIGINAL: Local approach using DirectoryLoader
    """
    from langchain_community.document_loaders import DirectoryLoader
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


def load_documents_from_s3():
    from langchain_community.document_loaders import DirectoryLoader
    
    temp_dir = Path("temp_s3_raw")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Download from S3
        download_s3_folder(S3_BUCKET_NAME, S3_RAW_PREFIX, str(temp_dir))

        # Load documents with DirectoryLoader
        loader = DirectoryLoader(str(temp_dir), glob=["*.md", "*.markdown"])
        raw_documents = loader.load()
        documents = []
        for doc in raw_documents:
            metadata, content = extract_metadata(doc.page_content)
            documents.append(Document(page_content=content, metadata=metadata))
        
        num_loaded = len(documents)
        logging.info(f"Loaded {num_loaded} documents from S3 prefix: {S3_RAW_PREFIX}")
        return documents

    except Exception as e:
        logging.error(f"Error loading documents from S3: {e}")
        return []

    finally:
        # Cleanup: remove temp_s3_raw (only if it exists)
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logging.info("Removed temporary directory for S3 raw documents.")


# ─────────────────────────────────────────────────────────────────────────────
# SPLIT TEXT
# ─────────────────────────────────────────────────────────────────────────────
def split_text(documents: list[Document]):
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
    ORIGINAL: Saves the Chroma DB to a local folder
    """
    # Delete existing folder
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        logging.info(f"Deleted existing Chroma database at {CHROMA_PATH}")

    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        db = Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
        db.persist()
        logging.info(f"Saved {len(chunks)} chunks to Chroma database at {CHROMA_PATH}")
    except Exception as e:
        logging.error(f"Error saving to Chroma: {e}")

def empty_s3_prefix(bucket_name: str, prefix: str):
    """
    Deletes all objects under the given S3 prefix.
    """
    continuation_token = None
    while True:
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

        if 'Contents' not in response:
            break

        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        s3_client.delete_objects(
            Bucket=bucket_name,
            Delete={'Objects': objects_to_delete}
        )

        if response.get('NextContinuationToken'):
            continuation_token = response['NextContinuationToken']
        else:
            break

def save_to_chroma_s3(chunks: list[Document]):
    temp_chroma_dir = Path("temp_s3_chroma")
    if temp_chroma_dir.exists():
        shutil.rmtree(temp_chroma_dir)
    temp_chroma_dir.mkdir(parents=True, exist_ok=True)

    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        db = Chroma.from_documents(
            chunks,
            embeddings,
            persist_directory=str(temp_chroma_dir)
        )
        db.persist()
        logging.info(f"Saved {len(chunks)} chunks to a local temp Chroma db at {temp_chroma_dir}")

        # **Empty existing S3 'chroma' folder** so we can replace it
        empty_s3_prefix(S3_BUCKET_NAME, S3_CHROMA_PREFIX)
        logging.info(f"Deleted all objects in s3://{S3_BUCKET_NAME}/{S3_CHROMA_PREFIX}")

        # Now upload fresh files
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
    By default (use_s3=False), we'll load documents from local and save locally.
    If use_s3=True, we'll load from S3 and save to S3.
    """
    logging.info("Starting document preprocessing...")

    if not use_s3:
        logging.info("Using LOCAL mode for load and save.")
        documents = load_documents_from_local()
        if documents:
            chunks = split_text(documents)
            save_to_chroma_local(chunks)

    else:
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
