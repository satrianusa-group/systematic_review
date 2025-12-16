import os
import tempfile
import pickle
import requests
import faiss
import numpy as np
from PyPDF2 import PdfReader
from textwrap import wrap
from openai import OpenAI
from dotenv import load_dotenv
import tiktoken

# Load environment variables
load_dotenv()

# Initialize OpenAI client (will be set in init function)
client = None
EMBEDDING_MODEL = "text-embedding-3-large"

# Token encoder for counting
encoding = None

def init_openai_client():
    """Initialize OpenAI client."""
    global client, encoding
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    client = OpenAI(api_key=api_key)
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return client

def count_tokens(text):
    """Count tokens in text using tiktoken."""
    global encoding
    if encoding is None:
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(text))

def extract_pdf_text_from_url(url):
    """
    Extract text from PDF URL or local file.
    
    Args:
        url: Either a URL (http/https) or local file path
        
    Returns:
        Extracted text as string, or None if extraction fails
    """
    try:
        if url.startswith('http'):
            # Download from URL
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                print(f"Failed to download PDF: HTTP {response.status_code}")
                return None
            content = response.content
        else:
            # Read local file
            if not os.path.exists(url):
                print(f"File not found: {url}")
                return None
            with open(url, 'rb') as f:
                content = f.read()
        
        # Save to temporary file for PyPDF2
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # Extract text
        reader = PdfReader(tmp_file_path)
        text = ""
        
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as e:
                print(f"Error extracting page {page_num}: {e}")
                continue

        # Cleanup
        os.remove(tmp_file_path)
        
        if not text.strip():
            print("No text extracted from PDF")
            return None
            
        return text
        
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return None

def split_text_into_chunks(text, max_tokens=1000):
    """
    Split text into chunks of approximately max_tokens.
    
    Args:
        text: Input text to split
        max_tokens: Maximum tokens per chunk (approximated as chars/4)
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    # Approximate: 1 token ≈ 4 characters
    max_chars = max_tokens * 4
    
    # Use textwrap to split intelligently
    chunks = wrap(
        text, 
        max_chars, 
        break_long_words=False, 
        break_on_hyphens=False
    )
    
    return chunks

def create_embeddings_with_tokens(text_list):
    """
    Create embeddings using OpenAI API with token tracking.
    
    Args:
        text_list: List of text strings to embed
        
    Returns:
        Tuple of (embeddings array, total_tokens_used)
    """
    global client
    
    try:
        if not text_list:
            return np.array([]).astype("float32"), 0
        
        # Initialize client if not already done
        if client is None:
            init_openai_client()
        
        # Count tokens
        total_tokens = sum([count_tokens(text) for text in text_list])
        
        # OpenAI API call
        response = client.embeddings.create(
            input=text_list,
            model=EMBEDDING_MODEL
        )
        
        # Extract embeddings
        embeddings = [item.embedding for item in response.data]
        
        # Get actual token usage from API
        actual_tokens = response.usage.total_tokens
        
        return np.array(embeddings).astype("float32"), actual_tokens
        
    except Exception as e:
        print(f"Error creating embeddings: {e}")
        raise

def create_embeddings(text_list):
    """
    Create embeddings using OpenAI API (without token tracking).
    For backward compatibility.
    
    Args:
        text_list: List of text strings to embed
        
    Returns:
        Numpy array of embeddings
    """
    embeddings, _ = create_embeddings_with_tokens(text_list)
    return embeddings

def save_faiss_and_metadata(embeddings, metadata, base_filename):
    """
    Save FAISS index and metadata to disk.
    
    Args:
        embeddings: Numpy array of embeddings
        metadata: List of metadata dictionaries
        base_filename: Base filename (without extension)
        
    Returns:
        Tuple of (index_path, metadata_path)
    """
    try:
        # Create FAISS index
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)

        # Create paths
        index_path = f"indexes/{base_filename}.index"
        metadata_path = f"indexes/{base_filename}_metadata.pkl"

        # Save index
        faiss.write_index(index, index_path)
        print(f"Saved FAISS index to: {index_path}")

        # Save metadata
        with open(metadata_path, "wb") as f:
            pickle.dump(metadata, f)
        print(f"Saved metadata to: {metadata_path}")

        return index_path, metadata_path
        
    except Exception as e:
        print(f"Error saving index and metadata: {e}")
        raise

def load_faiss_and_metadata(index_path, metadata_path):
    """
    Load FAISS index and metadata from disk.
    
    Args:
        index_path: Path to FAISS index file
        metadata_path: Path to metadata pickle file
        
    Returns:
        Tuple of (index, metadata, index_path, metadata_path)
    """
    try:
        # Load FAISS index
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"Index file not found: {index_path}")
        index = faiss.read_index(index_path)
        print(f"Loaded FAISS index from: {index_path}")
        
        # Load metadata
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        with open(metadata_path, "rb") as f:
            metadata = pickle.load(f)
        print(f"Loaded metadata from: {metadata_path}")
        
        return index, metadata, index_path, metadata_path
        
    except Exception as e:
        print(f"Error loading index and metadata: {e}")
        raise

def upload_file_to_api(file_path, file_name, file_type):
    """
    Mock upload function - returns local path for development.
    In production, implement actual upload to cloud storage.
    
    Args:
        file_path: Local file path
        file_name: Name of file
        file_type: MIME type
        
    Returns:
        File path/URL
    """
    # For local development, just return the path
    # In production, upload to S3/Azure/GCS and return URL
    return file_path

def query_faiss_index(question, faiss_index, metadata, top_k=30):
    """
    Query FAISS index with a question.
    
    Args:
        question: Question string
        faiss_index: FAISS index object
        metadata: List of metadata dictionaries
        top_k: Number of results to return
        
    Returns:
        List of relevant text chunks
    """
    try:
        # Create embedding for question
        query_embedding = create_embeddings([question])[0]
        
        # Search index
        D, I = faiss_index.search(
            np.array([query_embedding]), 
            min(top_k, len(metadata))
        )
        
        # Collect results
        results = []
        for idx in I[0]:
            if idx < len(metadata):
                results.append(metadata[idx]["text"])
        
        return results
        
    except Exception as e:
        print(f"Error querying index: {e}")
        raise

def extract_paper_name(pdf_url):
    """
    Extract a readable paper name from PDF URL or path.
    
    Args:
        pdf_url: URL or path to PDF
        
    Returns:
        Cleaned paper name
    """
    import urllib.parse
    
    # Get filename
    filename = pdf_url.split('/')[-1]
    
    # URL decode
    filename = urllib.parse.unquote(filename)
    
    # Remove .pdf extension
    if filename.lower().endswith('.pdf'):
        filename = filename[:-4]
    
    # Clean up
    filename = filename.replace('_', ' ').replace('-', ' ')
    
    return filename