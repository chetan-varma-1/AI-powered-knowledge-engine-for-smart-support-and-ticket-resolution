''' LLM engine module - allows us to interact with the llm and pass the context which we are going to get the the rag system  and based on the prompt + query + context  the llm will generate an optimized response''' 

import ollama 
import logging
import rag_engine

#Configure logging
logging.basicConfig(level=logging.INFO, format = '%(asctime)s - %(levelname)s - %(message)s')

MODEL_NAME = "llama3.2:1b"

def check_model_availability():
    """Checks if th model is avaliable locally, pulls if not."""
    try:
        #List available models
        models_response = ollama.list()

        #Robust parsins for differeent ollama versions
        model_names =[]
        if 'models' in models_response:
            for m in models_response['models']:
                if isinstance(m,dict):
                    model_names.append(m.get('name',''))
                    model_names.append(m.get('models',''))
        #Check against likely variations
        if MODEL_NAME not in model_name and f"{MODEL_NAME }:latest" not in model_names:
            logging.info(f"Model {MODEL_NAME} not found locally. Pulling...")
            ollama.pull(MODEL_NAME)
            logging.info(f"Model {MODEL_NAME} pulled successfully.")
        else:
            logging.info(f"Model {MODEL_NAME} is available locally.")
    except Exception as e:
        logging.error(f"Error checking model availability: {e}")

def analyze_ticket(title, description,priority, category):
    """Analyze the ticket and generate an optimized response using LLM"""

    #RAG Retrival
    logging.info("Retrieving relevant context...")
    context = rag_engine.get_revelant_context(f"{title} {description}")

    prompt = f"""
    Context:
    {context}

    Ticket: {title} ({description})

    Instruction:
    You are an automated support engine.
    Provide a resolution for the above ticket.
    - Be concise.
    - Use bullet points.
    - Do not mention "As an AI"  or "As a support agent".
    - Just give the comparison or solution.

    Resultion:
    """
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[
        {'role':'user','content':prompt}
        ])
        content = response['message']['content']
        return  category, content.strip()
    except Exception as e:
        error_msg = f"Error :{str(e)}"
        logging.error(f"LLM Error :{error_msg}")
        return "Error", f"Failed to generate resolution. Details :{error_msg}"

if __name__ == "__main__":
    cat, res = analyze_ticket("Internet down","My wifi is not connecting","low","software")
    print(f"Category:{cat}")
    print(f"Resolution{res}")