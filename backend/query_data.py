"""
Query Data Module
=================

This module handles querying a ChromaDB knowledge base to provide relevant
responses to user queries. It integrates with OpenAI for embedding and
chat completion and maintains conversation history to deliver context-aware
responses.

Dependencies:
- tiktoken
- langchain
- openai
- chromadb
- dotenv
"""

import os
import re
import logging
import tiktoken
from typing import List, Dict, Any
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.callbacks.openai_info import OpenAICallbackHandler
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# Environment Setup
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()

# Load OpenAI API Key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "data/chroma")

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────
def get_source_from_metadata(metadata: Dict[str, str]) -> str:
    """Extract a human-readable source string from metadata."""
    page_title = metadata.get('page_title', '').strip()
    subcategory = metadata.get('subcategory', '').strip()

    if page_title and subcategory:
        return f"{subcategory} - {page_title}"
    elif page_title:
        return page_title
    elif subcategory:
        return subcategory
    return "unknown source"

def truncate_history(messages: List[Dict[str, Any]], max_tokens: int = 3000, model_name: str = 'gpt-3.5-turbo', reserved_tokens: int = 500) -> List[Dict[str, Any]]:
    """Truncate the conversation history to fit within a token limit."""
    encoding = tiktoken.encoding_for_model(model_name)
    total_tokens = reserved_tokens
    truncated_messages = []

    for message in reversed(messages):
        tokens = len(encoding.encode(message.content)) + 4
        total_tokens += tokens
        if total_tokens > max_tokens:
            break
        truncated_messages.insert(0, message)

    logging.info(f"Truncated conversation history to {len(truncated_messages)} messages")
    return truncated_messages

# ─────────────────────────────────────────────────────────────────────────────
# Main Query Function
# ─────────────────────────────────────────────────────────────────────────────
def main(query_text: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main function to handle user query processing and provide a response.
    """
    if not os.path.exists(CHROMA_PATH):
        error_message = "Error: The knowledge base is missing. Please contact support."
        logging.error(error_message)
        return {"response": error_message, "sources": []}

    try:
        # Load the Chroma database
        embedding_function = OpenAIEmbeddings()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

        logging.info("Successfully connected to Chroma database.")

        # Perform similarity search
        results = db.similarity_search_with_relevance_scores(query_text, k=3)
        logging.info(f"Retrieved {len(results)} results from Chroma.")

        context_text = ""
        sources = set()

        for document, score in results:
            if score >= 0.7:
                context_text += document.page_content + "\n\n---\n\n"
                sources.add(get_source_from_metadata(document.metadata))

        sources = sorted(sources)
        logging.info(f"Context constructed with {len(sources)} sources.")

        # Construct the system message
        system_message = SystemMessage(content=(f"""
            You are a specialized assistant that helps developers create and troubleshoot Terraform configuration files.

            Instructions:
            - Use **only** the following provided context to answer the user's question.
            - If the answer is not contained within the context, politely inform the user that you cannot assist.
            - Provide clear and concise explanations in markdown format.
            - Use bullet points for lists and triple backticks for code blocks with 'hcl' as the language.
            - Reference the sources in your response when applicable.

            {context_text}
        """))

        # Prepare conversation messages
        messages = [system_message]
        for msg in history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))

        # Truncate messages to fit token limits
        messages = truncate_history(messages)

        # Generate AI response
        openai_callback = OpenAICallbackHandler()
        model = ChatOpenAI(
            model_name='gpt-3.5-turbo',
            temperature=0.7,
            max_tokens=500,
            callbacks=[openai_callback]
        )

        response = model.invoke(messages)
        response_text = response.content.strip()

        # Prepare a structured response with both the formatted response and sources
        response_data = {
            "response": response_text,  # The bot's response
            "sources": sorted(list(sources))  # Ensure sources are deduplicated and sorted
        }

        # Log the structured response
        logging.info(f"Response data being returned: {response_data}")

        return response_data  # Return the response as a dictionary

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        return {"response": "An error occurred while processing your request.", "sources": []}
