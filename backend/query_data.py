import logging
import os
import tiktoken
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.callbacks.openai_info import OpenAICallbackHandler
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT SETUP
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()

# Load OpenAI API Key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

# Define constants for file paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "data/chroma")

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_source_from_metadata(metadata):
    """
    Extract and format the source from document metadata.

    Args:
        metadata (dict): Metadata dictionary.

    Returns:
        str: Formatted source string.
    """
    page_title = metadata.get('page_title', '').strip()
    subcategory = metadata.get('subcategory', '').strip()

    if page_title and subcategory:
        return f"{subcategory} - {page_title}"
    elif page_title:
        return page_title
    elif subcategory:
        return subcategory
    else:
        return "unknown source"


def truncate_history(messages, max_tokens=3000, model_name='gpt-4o-mini', reserved_tokens=500):
    """
    Truncate conversation history to fit within the token limit.

    Args:
        messages (list): List of message objects.
        max_tokens (int): Maximum allowed tokens.
        model_name (str): Model name for token encoding.
        reserved_tokens (int): Reserved tokens for the response.

    Returns:
        list: Truncated message list.
    """
    encoding = tiktoken.encoding_for_model(model_name)
    total_tokens = reserved_tokens
    truncated_messages = []

    # Reverse the messages to start counting from the most recent
    for message in reversed(messages):
        tokens = len(encoding.encode(message.content)) + 4  # Add metadata tokens
        total_tokens += tokens
        if total_tokens > max_tokens:
            break
        truncated_messages.insert(0, message)

    logging.info(f"Truncated history contains {len(truncated_messages)} messages, total tokens: {total_tokens}")
    return truncated_messages

# ─────────────────────────────────────────────────────────────────────────────
# MAIN QUERY FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def main(query_text, history):
    """
    Main function to process user queries and retrieve relevant responses.

    Args:
        query_text (str): User input query.
        history (list): Conversation history.

    Returns:
        dict: Response data including the AI's reply and relevant sources.
    """
    # Check if the Chroma directory exists
    if not os.path.exists(CHROMA_PATH):
        error_message = "Error: The knowledge base is missing. Please contact support."
        logging.error(error_message)
        return {"response": error_message, "sources": []}

    try:
        # Initialize the database
        embedding_function = OpenAIEmbeddings()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
        logging.info("Successfully connected to Chroma database.")

        # Perform a similarity search
        results = db.similarity_search_with_relevance_scores(query_text, k=3)
        logging.info(f"Search results: {results}")

        # Build context and collect sources
        context_text = ""
        sources = set()

        if not results or results[0][1] < 0.7:
            logging.warning("No relevant results found for the query.")
        else:
            for document, score in results:
                context_text += document.page_content + "\n\n---\n\n"
                sources.add(get_source_from_metadata(document.metadata))

        # Format sources
        sources = sorted(sources)
        logging.info(f"Collected sources: {sources}")

        # Construct system prompt
        system_message = SystemMessage(content=(
            "You are a specialized assistant that helps developers create and troubleshoot Terraform configuration files.\n\n"
            "Instructions:\n"
            "- Use **only** the following provided context to answer the user's question.\n"
            "- If the answer is not contained within the context, politely inform the user that you cannot assist with that request.\n"
            "- Provide clear and concise explanations in markdown format.\n"
            "- Use bullet points for lists and triple backticks for code blocks, specifying 'hcl' as the language.\n"
            f"{context_text}\n\n"
        ))

        # Prepare the message list
        messages = [system_message]
        for msg in history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))

        # Truncate history
        messages = truncate_history(messages, max_tokens=3000, reserved_tokens=500)

        # Call the OpenAI model
        openai_callback = OpenAICallbackHandler()
        model = ChatOpenAI(
            model_name='gpt-3.5-turbo',
            temperature=0.7,
            max_tokens=500,
            callbacks=[openai_callback],
            verbose=True
        )

        response = model.invoke(messages)
        response_text = response.content.strip()

        # Add sources if available
        if sources:
            response_text += f"\n\nSources:\n" + "\n".join(f"- {source}" for source in sources)

        logging.info(f"Response generated: {response_text}")

        return {"response": response_text, "sources": sources}

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        return {"response": "An error occurred while processing your request.", "sources": []}

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Example usage
    example_query = "How do I create an S3 bucket using Terraform?"
    example_history = []
    result = main(example_query, example_history)
    print(result)
