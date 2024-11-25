import logging
import os
import tiktoken
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.callbacks.openai_info import OpenAICallbackHandler
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    filename='./backend/backend.log',
    filemode='a',
    format='%(asctime)s %(levelname)s:%(message)s'
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "data/chroma")

def get_source_from_metadata(metadata):
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


def truncate_history(messages, max_tokens=3000, model_name='gpt-3.5-turbo', reserved_tokens=500):
    encoding = tiktoken.encoding_for_model(model_name)
    total_tokens = reserved_tokens
    truncated_messages = []
    message_token_counts = []
    # Reverse the messages to start counting from the most recent
    for message in reversed(messages):
        # Calculate tokens for message content plus metadata tokens
        tokens = len(encoding.encode(message.content)) + 4
        total_tokens += tokens
        if total_tokens > max_tokens:
            break
        truncated_messages.insert(0, message)
        message_token_counts.insert(0, (message, tokens))
    # Log the token counts for each message
    for msg, token_count in message_token_counts:
        logging.info(f"Message from {type(msg).__name__}: {token_count} tokens")
    logging.info(f"Total tokens in request (including reserved for response): {total_tokens}")   
    return truncated_messages

def main(query_text, history):
    # Check if the Chroma directory exists
    if not os.path.exists(CHROMA_PATH):
        error_message = "Error: The knowledge base is missing. Please contact support."
        logging.error(error_message)
        return error_message

    try:
        # Prepare the DB
        embedding_function = OpenAIEmbeddings()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

        # Log database connectivity
        logging.info("Successfully connected to Chroma database.")

        # Search the DB
        results = db.similarity_search_with_relevance_scores(query_text, k=3)
        logging.info(f"Raw Chroma results: {results}")  # Debug raw results

        # Initialize context and sources
        context_text = ""
        sources = set()

        if len(results) == 0 or results[0][1] < 0.7:
            logging.warning("No relevant results found for the query.")
        else:
            for document, score in results:
                logging.info(f"Document content: {document.page_content}, Score: {score}")
                context_text += document.page_content + "\n\n---\n\n"
                source = get_source_from_metadata(document.metadata)
                source = " ".join(source.split())  # Normalize whitespace
                sources.add(source)  # Deduplicate

        # Convert the set to a sorted list
        sources = sorted(list(sources))

        # Log deduplicated sources
        logging.info(f"Unique sources after deduplication: {sources}")

        # Add system prompt with context and policies
        logging.info(f"Constructed context_text for system prompt: {context_text}")
        system_message = SystemMessage(content=(
            "You are a specialized assistant that helps developers create and troubleshoot Terraform configuration files.\n\n"
            "Instructions:\n"
            "- Use **only** the following provided context to answer the user's question.\n"
            "- If the answer is not contained within the context, politely inform the user that you cannot assist with that request.\n"
            "- Provide clear and concise explanations in markdown format.\n"
            "- Use bullet points for lists and triple backticks for code blocks, specifying 'hcl' as the language (e.g., ```hcl).\n"
            "- When applicable, reference the sources from the context in your response.\n"
            "- Do not provide information outside of Terraform configuration files.\n"
            f"{context_text}\n\n"
        ))

        messages = [system_message]

        # Append the conversation history
        for msg in history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))

        # Truncate history to fit within the token limit
        messages = truncate_history(messages, max_tokens=3000, reserved_tokens=500)
        logging.info(f"Truncated conversation history: {messages}")

        openai_callback = OpenAICallbackHandler()

        model = ChatOpenAI(
            model_name='gpt-3.5-turbo',
            temperature=0.7,
            max_tokens=500,
            callbacks=[openai_callback],
            verbose=True
        )

        response = model.invoke(messages)

        # Log token usage
        logging.info(f"Prompt tokens used: {openai_callback.prompt_tokens}")
        logging.info(f"Completion tokens used: {openai_callback.completion_tokens}")
        logging.info(f"Total tokens used: {openai_callback.total_tokens}")
        logging.info(f"Total cost (USD): {openai_callback.total_cost}")

        response_text = response.content.rstrip()

        # Add logging to inspect response_text before appending sources
        logging.info(f"Response text before checking for sources: {response_text}")

        # Conditionally format the response based on the presence of sources
        if sources:
            # Check if the AI's response already contains a "Sources" section
            if "Sources:" not in response_text and "Source:" not in response_text:
                formatted_response = f"{response_text}\n\nSources:\n" + "\n".join(f"- {source}" for source in sources)
            else:
                # If the response already contains "Sources", use it as-is
                formatted_response = response_text
        else:
            formatted_response = response_text

        # Log the final formatted response
        logging.info(f"Formatted response being returned: {formatted_response}")

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
        return "An error occurred while processing your request."
