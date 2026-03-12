import os 
import shutil
import logging
import ollama
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
ollama.pull("tinyllama")
#Configure logging # INFO, ERROR, WARNING, DEBUG
logging.basicConfig(level=logging.INFO)

#Robust path handling
BASE_DIR = os.getcwd() #C:\Users\ChetanAtla\Desktop\backup\ai powered\app\data
#Try to find data directory
if os.path.exists(os.path.join(BASE_DIR, 'data')):
    DATA_DIR = os.path.join(BASE_DIR, 'data')
elif os.path.exists(os.path.join(BASE_DIR,"..","data")):  #C:\Users\ChetanAtla\Desktop\backup\ai powered\data
    DATA_DIR = os.path.join(BASE_DIR,"..","data")
else:
    DATA_DIR = "data" #Fallback

DATA_RAW_DIR = os.path.join(DATA_DIR, "raw")
DATA_PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
FAISS_INDEX_PATH = os.path.join(DATA_DIR,"processed","faiss_index")

from langchain_core.embeddings import Embeddings

#Disable htppx logs 
logging.getLogger("httpx").setLevel(logging.WARNING)

class OllamaEmbeddings(Embeddings):
    """Custom Embedding class to use ollama natively."""
    def __init__(self,model="tinyllama"):
        self.model = model
    def embed_documents(self, texts):
        embeddings = []
        for text in texts:
            #BATCHING could be added here for efficiency
            resp = ollama.embeddings(model=self.model,prompt = text)
            embeddings.append(resp['embedding'])
        return embeddings

    def embed_query(self, text):
        resp = ollama.embeddings(model=self.model,prompt = text)
        return resp['embedding']

def ingest_documents():
    """Ingests documents from data/raw directory, creates embeddings, and updates the FAISS index.
    Moves processed files to data/processed directory to avioud the re-processing """

    #Ensure dirs exist
    if not os.path.exists(DATA_RAW_DIR):
        try:
            os.makedirs(DATA_RAW_DIR)
        except OSError:
            pass  # Might exist
    if not os.path.exists(DATA_PROCESSED_DIR):
        os.makedirs(DATA_PROCESSED_DIR,exist_ok=True)

    files = [f for f in os.listdir(DATA_RAW_DIR) if os.path.isfile(os.path.join(DATA_RAW_DIR,f))]
    if not files:
        logging.info("No new documents found to ingest.")
        return
    logging.info(f"Found {len(files)} documents. Loading...")

    documents = []
    #Load PDFs
    for file in files:
        file_path = os.path.join(DATA_RAW_DIR, file)
        try:
            if file.lower().endswith(".pdf"):
                loader = PyPDFLoader(file_path)
                documents.extend(loader.load())
            elif file.lower().endswith(".txt"):
                loader = TextLoader(file_path)
                documents.extend(loader.load())
        except Exception as e:
            logging.warning(f"Failed to load {file}: {e}")

    if not documents:
        logging.warning("No valid documents found to ingest.")
        return
    
    #Split text 
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap = 200,
    )
    docs = text_splitter.split_documents(documents)
    logging.info(f"Split {len(documents)} documents into {len(docs)} chunks.")

    #Emded and store

    embeddings = OllamaEmbeddings(model="tinyllama")

    if os.path.exists(FAISS_INDEX_PATH):
        try:
            db = FAISS.load_local(FAISS_INDEX_PATH,embeddings,allow_dangerous_deserialization=True)
            db.add_documents(docs)
            logging.info("Loaded existing index.")
        except Exception as e:
            logging.error(f"Error  loading existing index.")
            db = FAISS.from_documents(docs,embeddings)
    else:
        db = FAISS.from_documents(docs,embeddings)
        logging.info("Create new FAISS index.")
    db.save_local(FAISS_INDEX_PATH)

    #Move processed files
    for file in files:
        src = os.path.join(DATA_RAW_DIR,file)
        dst = os.path.join(DATA_PROCESSED_DIR,file)
        try:
            shutil.move(src,dst)
        except Exception as e:
            logging.warning(f"Failed to move {file}: {e}")
    logging.info("Ingestion complete.")

def get_revelant_context(query, k=2):
    """Retrieves the most revelamt context chunkc for a given query.
    k=2 for efficency and speed."""
    if not os.path.exists(FAISS_INDEX_PATH):
        return " "
    embeddings = OllamaEmbeddings(model="tinyllama")
    try:
        db = FAISS.load_local(FAISS_INDEX_PATH,embeddings,allow_dangerous_deserialization=True)
        docs = db.similarity_search(query,k=k) # threshold - 0.8 
        return "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        logging.error(f"Error retreving context: {e}")
        return " "
    
if __name__ == "__main__":
    ingest_documents()



    
    

    
    
