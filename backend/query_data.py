import argparse
import logging
import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

Answer the question based on the above context: {question}
"""

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

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO, filename='backend.log', filemode='w')

    # Check if the Chroma directory exists
    if not os.path.exists(CHROMA_PATH):
        logging.error(f"Chroma directory does not exist: {CHROMA_PATH}")
        return  # Exit the function if the directory doesn't exist

    # Create CLI
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text")
    args = parser.parse_args()
    query_text = args.query_text

    try:
        # Prepare the DB
        embedding_function = OpenAIEmbeddings()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

        # Log database connectivity
        logging.info("Successfully connected to Chroma database.")

        # Check the number of documents in the database
        total_docs = len(db.get()['ids'])  # Use get() method to retrieve all documents
        logging.info(f"Total documents in database: {total_docs}")

        # Search the DB
        results = db.similarity_search_with_relevance_scores(query_text, k=3)
        logging.info(f"Query '{query_text}' returned {len(results)} results.")

        if len(results) == 0 or results[0][1] < 0.7:
            logging.warning("No relevant results found for the query.")
            print("No relevant results found")
            return
        
        # Log the results for debugging
        context_text = ""
        sources = []
        for document, score in results:
            logging.info(f"Document content: {document.page_content}, Score: {score}")
            logging.info(f"Document metadata: {document.metadata}")
            
            context_text += document.page_content + "\n\n---\n\n"
            source = get_source_from_metadata(document.metadata)
            if source not in sources:
                sources.append(source)

        prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        prompt = prompt_template.format(context=context_text, question=query_text)

        logging.info("Generated prompt for model: %s", prompt)

        model = ChatOpenAI()
        response = model.invoke([HumanMessage(content=prompt)])
        response_text = response.content

        formatted_response = f"Response: {response_text}\n\nSources:\n" + "\n".join(f"- {source}" for source in sources)
        print(formatted_response)

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()