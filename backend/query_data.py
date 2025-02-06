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

# Load environment variables from a .env file if present
load_dotenv()

# Retrieve OpenAI API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# Define the path to the local Chroma database directory
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "data/chroma")

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────
def get_source_from_metadata(metadata: Dict[str, str]) -> str:
    """
    Extract a human-readable source string from metadata.
    Typically uses 'page_title' and/or 'subcategory' if available.
    """
    logging.info("Extracting source from metadata.")
    page_title = metadata.get('page_title', '').strip()
    subcategory = metadata.get('subcategory', '').strip()

    if page_title and subcategory:
        source = f"{subcategory} - {page_title}"
    elif page_title:
        source = page_title
    elif subcategory:
        source = subcategory
    else:
        source = "unknown source"

    logging.info(f"Extracted source: {source}")
    return source

def truncate_history(messages: List[Dict[str, Any]], max_tokens: int = 3000, model_name: str = 'gpt-3.5-turbo', reserved_tokens: int = 500) -> List[Dict[str, Any]]:
    """
    Truncate conversation history to keep total tokens within the specified limit.
    This ensures that the conversation does not exceed the model's maximum context length.
    """
    logging.info("Truncating conversation history.")
    encoding = tiktoken.encoding_for_model(model_name)
    total_tokens = reserved_tokens
    truncated_messages = []

    # Start from the end of the list (most recent messages) and move backward
    for message in reversed(messages):
        # Approximate token count for each message, including overhead
        tokens = len(encoding.encode(message.content)) + 4
        total_tokens += tokens

        # If adding this message exceeds the max limit, stop
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
    Main function to handle user queries. It uses the local ChromaDB 
    (populated with preprocessed documents) to find relevant context chunks, 
    then passes that context to an OpenAI Chat model. 
    """
    logging.info(f"Processing query: {query_text}")

    if not os.path.exists(CHROMA_PATH):
        error_message = "Error: The knowledge base is missing. Please contact support."
        logging.error(error_message)
        return {"response": error_message, "sources": []}

    try:
        # Connect to the local Chroma database
        logging.info("Connecting to Chroma database.")
        embedding_function = OpenAIEmbeddings()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

        logging.info("Successfully connected to Chroma database.")

        # Perform a similarity search for the user's query
        logging.info("Performing similarity search.")
        # 'k=3' means we retrieve up to 3 most relevant chunks
        results = db.similarity_search_with_relevance_scores(query_text, k=3)
        logging.info(f"Retrieved {len(results)} results from Chroma.")

        # Build a single context string from relevant chunks
        context_text = ""
        sources = set()

        for document, score in results:
            logging.info(f"Document content: {document.page_content[:100]}... (truncated), Score: {score}")

            # Only include chunks above a certain relevance threshold
            if score >= 0.7:
                context_text += document.page_content + "\n\n---\n\n"
                sources.add(get_source_from_metadata(document.metadata))

        # Sort and list the sources
        sources = sorted(sources)
        logging.info(f"Constructed context with {len(sources)} sources: {sources}")

        # Construct the system message
        logging.info("Constructing system message.")
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

        # Build the conversation for the chat model: system + user + assistant messages
        messages = [system_message]
        for msg in history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))

        # Truncate messages to fit token limits
        logging.info("Truncating messages for token limit.")
        messages = truncate_history(messages)

        # Generate AI response
        logging.info("Generating AI response.")
        openai_callback = OpenAICallbackHandler() # For logging token usage
        model = ChatOpenAI(
            model_name='gpt-3.5-turbo',
            temperature=0.7,
            max_tokens=500,             # The assistant’s max tokens for the reply
            callbacks=[openai_callback] # Callback to capture usage/cost
        )

        # Get the response from the model
        response = model.invoke(messages)
        response_text = response.content.strip()

        # Log token usage
        logging.info(f"Token usage: Prompt tokens = {openai_callback.prompt_tokens}, "
                     f"Completion tokens = {openai_callback.completion_tokens}, "
                     f"Total tokens = {openai_callback.total_tokens}, "
                     f"Total cost (USD) = {openai_callback.total_cost}")

        logging.info(f"Generated response: {response_text[:100]}... (truncated)")

        # Return the structured response data
        response_data = {
            "response": response_text,  # The bot's response
            "sources": sorted(list(sources))  # Ensure sources are deduplicated and sorted
        }

        # Log the structured response
        logging.info(f"Response data: {response_data}")

        return response_data  # Return the response as a dictionary

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        return {"response": "An error occurred while processing your request.", "sources": []}
