import logging
import os
# from langchain_chroma import Chroma
# from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = "data/chroma"

# PROMPT_TEMPLATE = """
# You are a specialized assistant that helps developers create and troubleshoot Terraform configuration files.
# Use only the following context to answer the question:

# {context}

# Answer the question based on the above context: {question}
# """

def get_source_from_metadata(metadata):
    page_title = metadata.get('page_title', '')
    subcategory = metadata.get('subcategory', '')
    if page_title and subcategory:
        return f"{subcategory} - {page_title}"
    elif page_title:
        return page_title
    elif subcategory:
        return subcategory
    else:
        return "Unknown source"

def truncate_history(messages, max_tokens=3000):
    total_tokens = 0
    truncated_messages = []
    for message in reversed(messages):
        tokens = len(message.content.split())
        total_tokens += tokens
        if total_tokens > max_tokens:
            break
        truncated_messages.insert(0, message)
    return truncated_messages

def main(query_text, history):
    # Set up logging
    logging.basicConfig(level=logging.INFO, filename='./backend/backend.log', filemode='w')

    # Check if the Chroma directory exists
    if not os.path.exists(CHROMA_PATH):
        logging.error(f"Chroma directory does not exist: {CHROMA_PATH}")
        return "Error: Knowledge base not found."

    try:
        # Prepare the DB
        embedding_function = OpenAIEmbeddings()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

        # Log database connectivity
        logging.info("Successfully connected to Chroma database.")

        # Search the DB
        results = db.similarity_search_with_relevance_scores(query_text, k=3)
        logging.info(f"Query '{query_text}' returned {len(results)} results.")

        if len(results) == 0 or results[0][1] < 0.7:
            logging.warning("No relevant results found for the query.")
            return "I am only a specialized assistant for Terraform configuration files. I am unable to answer your question."

        # Log the results for debugging
        context_text = ""
        sources = []
        for document, score in results:
            logging.info(f"Document content: {document.page_content}, Score: {score}")
            context_text += document.page_content + "\n\n---\n\n"
            source = get_source_from_metadata(document.metadata)
            if source not in sources:
                sources.append(source)

        messages = []

        # # Add system prompt with context
        # system_message = SystemMessage(content=(
        #     "You are a specialized assistant that helps developers create and troubleshoot Terraform configuration files."
        #     " Use only the following context to answer the question:\n\n"
        #     f"{context_text}"
        # ))
        # messages.append(system_message)

        # Add system prompt with context and policies
        system_message = SystemMessage(content=(
            "You are a specialized assistant that helps developers create and troubleshoot Terraform configuration files.\n\n"
            "Instructions:\n"
            "- Use **only** the following provided context to answer the user's question.\n"
            "- If the answer is not contained within the context, politely inform the user that you cannot assist with that request.\n"
            "- Provide clear and concise explanations in markdown format.\n"
            "- Use bullet points for lists and triple backticks for code blocks.\n"
            "- When applicable, reference the sources from the context in your response.\n"
            "- Do not provide information outside of Terraform configuration files.\n"
            # "- Adhere to the OpenAI policies below. Do not provide disallowed content. If unsure, refrain from providing the content.\n\n"
            # "Context:\n"
            f"{context_text}\n\n"
            # "OpenAI Policies:\n"
            # "1. **Disallowed Content**: Do not provide illegal, unethical, or harmful content.\n"
            # "2. **Privacy**: Do not share personal or sensitive information.\n"
            # "3. **Accuracy**: Ensure all information is accurate and based on the context.\n"
            # "[Add other relevant policies as needed.]"
        ))
        messages.append(system_message)


        # Append the conversation history
        for msg in history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))
        
        # Truncate history to fit within the token limit
        messages = truncate_history(messages)

        model = ChatOpenAI()

        response = model.invoke(messages)
        response_text = response.content

        # prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        # prompt = prompt_template.format(context=context_text, question=query_text)

        # logging.info("Generated prompt for model: %s", prompt)

        # model = ChatOpenAI()
        # response = model.invoke([HumanMessage(content=prompt)])
        # response_text = response.content

        formatted_response = f"{response_text}\n\nSources:\n" + "\n".join(f"- {source}" for source in sources)
        return formatted_response

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        return "An error occurred while processing your request."
