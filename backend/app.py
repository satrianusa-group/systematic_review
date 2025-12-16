from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import logging
import urllib.parse
from datetime import datetime
from openai import OpenAI
import numpy as np
import faiss
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from utils import (
    extract_pdf_text_from_url,
    split_text_into_chunks,
    create_embeddings,
    create_embeddings_with_tokens,
    save_faiss_and_metadata,
    load_faiss_and_metadata,
    upload_file_to_api,
    init_openai_client,
    count_tokens
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Setup
logging.basicConfig(level=logging.INFO)

# Initialize OpenAI client
try:
    client = init_openai_client()
    logging.info("OpenAI client initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize OpenAI client: {e}")
    client = None

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('indexes', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return jsonify({"status": "running", "message": "Systematic Review API"})

@app.route('/systematic-review/upload', methods=['POST'])
def upload_papers():
    """Upload and process PDF papers."""
    try:
        logging.info("=== Upload Request Received ===")
        logging.info(f"Files in request: {request.files}")
        logging.info(f"Form data: {request.form}")
        
        if 'files' not in request.files:
            logging.error("No 'files' field in request")
            return jsonify({"status": "error", "message": "No files provided"}), 400
        
        files = request.files.getlist('files')
        session_id = request.form.get('session_id', f'session_{int(datetime.now().timestamp())}')
        
        logging.info(f"Session ID: {session_id}")
        logging.info(f"Number of files: {len(files)}")
        
        if not files or len(files) == 0:
            logging.error("File list is empty")
            return jsonify({"status": "error", "message": "No files selected"}), 400
        
        # Check if files are valid
        valid_files = [f for f in files if f and f.filename != '']
        if not valid_files:
            logging.error("No valid files found")
            return jsonify({"status": "error", "message": "No valid files selected"}), 400
        
        logging.info(f"[Session {session_id}] Processing {len(valid_files)} file(s)")
        
        # Save uploaded files
        pdf_paths = []
        paper_names = []
        
        for file in valid_files:
            logging.info(f"Processing file: {file.filename}")
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
                logging.info(f"Saving to: {filepath}")
                file.save(filepath)
                pdf_paths.append(filepath)
                paper_names.append(filename.replace('.pdf', ''))
                logging.info(f"✓ Saved: {filename}")
            else:
                logging.warning(f"✗ Skipped (not PDF): {file.filename}")
        
        if not pdf_paths:
            logging.error("No valid PDF files after filtering")
            return jsonify({"status": "error", "message": "No valid PDF files"}), 400
        
        logging.info(f"Starting text extraction for {len(pdf_paths)} PDFs")
        
        # Process PDFs
        all_metadata = []
        total_text_tokens = 0
        
        for pdf_path, paper_name in zip(pdf_paths, paper_names):
            logging.info(f"Extracting text from: {paper_name}")
            
            pdf_text = extract_pdf_text_from_url(pdf_path)
            if not pdf_text:
                logging.warning(f"Failed to extract text from: {paper_name}")
                continue
            
            logging.info(f"✓ Extracted {len(pdf_text)} characters from {paper_name}")
            
            # Estimate tokens in original text
            text_tokens = len(pdf_text) // 4
            total_text_tokens += text_tokens
            
            chunks = split_text_into_chunks(pdf_text, max_tokens=1000)
            logging.info(f"✓ Created {len(chunks)} chunks from {paper_name}")
            
            for chunk_idx, chunk in enumerate(chunks):
                all_metadata.append({
                    "text": chunk,
                    "paper_name": paper_name,
                    "paper_path": pdf_path,
                    "chunk_index": chunk_idx,
                    "total_chunks": len(chunks)
                })
        
        if not all_metadata:
            logging.error("No metadata created - text extraction failed for all PDFs")
            return jsonify({"status": "error", "message": "Failed to process PDFs - no text extracted"}), 400
        
        logging.info(f"Total metadata entries: {len(all_metadata)}")
        
        # Create embeddings with token tracking
        logging.info(f"Creating embeddings for {len(all_metadata)} chunks")
        texts = [m["text"] for m in all_metadata]
        
        try:
            embeddings, embedding_tokens = create_embeddings_with_tokens(texts)
            logging.info(f"✓ Created embeddings, used {embedding_tokens} tokens")
        except Exception as e:
            logging.error(f"Failed to create embeddings: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return jsonify({"status": "error", "message": f"Failed to create embeddings: {str(e)}"}), 500
        
        # Calculate costs
        embedding_cost = (embedding_tokens / 1000) * 0.00013
        
        # Save index
        base_filename = f"{session_id}_index"
        logging.info(f"Saving FAISS index as: {base_filename}")
        index_path, metadata_path = save_faiss_and_metadata(embeddings, all_metadata, base_filename)
        
        # Token usage summary
        token_usage = {
            "embedding_tokens": embedding_tokens,
            "total_chunks": len(all_metadata),
            "estimated_text_tokens": total_text_tokens,
            "embedding_cost_usd": round(embedding_cost, 6)
        }
        
        logging.info(f"✓ Successfully processed {len(paper_names)} papers")
        logging.info(f"Token usage: {token_usage}")
        
        return jsonify({
            "status": "success",
            "message": f"Successfully processed {len(paper_names)} paper(s)",
            "session_id": session_id,
            "index_path": index_path,
            "metadata_path": metadata_path,
            "papers": paper_names,
            "total_papers": len(paper_names),
            "token_usage": token_usage
        }), 200
        
    except Exception as e:
        logging.error(f"CRITICAL ERROR in upload: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@app.route('/systematic-review/query', methods=['POST'])
def query_papers():
    """Query papers with a question."""
    try:
        data = request.json
        session_id = data.get('session_id')
        question = data.get('question')
        index_path = data.get('index_path')
        metadata_path = data.get('metadata_path')
        
        logging.info(f"Received query request: session_id={session_id}, question={question[:50] if question else 'None'}...")
        logging.info(f"Index path: {index_path}")
        logging.info(f"Metadata path: {metadata_path}")
        
        if not question:
            return jsonify({
                "status": "error",
                "message": "Question is required"
            }), 400
            
        if not index_path or not metadata_path:
            return jsonify({
                "status": "error",
                "message": "No papers uploaded yet. Please upload papers first."
            }), 400
        
        logging.info(f"[Session {session_id}] Processing question: {question[:50]}...")
        
        # Load index
        faiss_index, metadata, _, _ = load_faiss_and_metadata(index_path, metadata_path)
        
        # Get paper names
        paper_names = list(set([m['paper_name'] for m in metadata]))
        
        # Process question with token tracking
        answer, token_usage = process_question(question, faiss_index, metadata)
        
        logging.info(f"[Session {session_id}] Query completed successfully")
        logging.info(f"[Session {session_id}] Tokens used: {token_usage}")
        
        return jsonify({
            "status": "success",
            "answer": answer,
            "papers_analyzed": paper_names,
            "token_usage": token_usage
        }), 200
        
    except Exception as e:
        logging.error(f"Error in query: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

def process_question(question, faiss_index, metadata):
    """Process question and generate answer with token tracking."""
    global client
    
    # Initialize client if needed
    if client is None:
        client = init_openai_client()
    
    # Retrieve fewer chunks to avoid context overflow
    # Reduced from 30 to 15 chunks
    num_chunks = min(20, len(metadata))  # Increased to 20 to get better coverage
    query_embedding = create_embeddings([question])[0]
    D, I = faiss_index.search(np.array([query_embedding]), num_chunks)
    
    # Organize by paper
    paper_contexts = {}
    for idx in I[0]:
        if idx < len(metadata):
            meta = metadata[idx]
            paper_name = meta.get("paper_name", "Unknown")
            if paper_name not in paper_contexts:
                paper_contexts[paper_name] = []
            paper_contexts[paper_name].append(meta["text"])
    
    # Log which papers were found
    logging.info(f"Found content from {len(paper_contexts)} papers: {list(paper_contexts.keys())}")
    
    # Build context - limit to 3 chunks per paper max
    papers_context = ""
    for paper_name, chunks in paper_contexts.items():
        # Take only first 3 chunks per paper
        limited_chunks = chunks[:3]
        combined_text = "\n\n".join(limited_chunks)
        papers_context += f"\n\n{'='*60}\nPAPER: {paper_name}\n{'='*60}\n{combined_text}\n"
    
    # Count tokens to ensure we're under limit
    estimated_context_tokens = count_tokens(papers_context)
    logging.info(f"Estimated context tokens: {estimated_context_tokens}")
    
    # If still too large, truncate further
    if estimated_context_tokens > 10000:
        logging.warning(f"Context too large ({estimated_context_tokens} tokens), truncating...")
        # Reduce to 2 chunks per paper
        papers_context = ""
        for paper_name, chunks in paper_contexts.items():
            limited_chunks = chunks[:2]
            combined_text = "\n\n".join(limited_chunks)
            papers_context += f"\n\n{'='*40}\nPAPER: {paper_name}\n{'='*40}\n{combined_text}\n"
    
    # Shortened system prompt
    system_prompt = "You are an expert systematic review assistant. Create detailed comparison tables from research papers."
    
    # Shortened user prompt
    user_prompt = f"""Question: {question}

Papers excerpts:
{papers_context}

Instructions:
1. First, directly answer the user's question based on the excerpts
2. If creating a comparison table, ONLY include rows that have actual content - do NOT add empty rows
3. Make sure to include information from ALL papers in your response
4. Use "Not reported" for missing information, but never create empty rows with just dashes

Format:
## Answer
[Direct answer]

## Comparison Table
| Parameter | Paper 1 | Paper 2 | Paper 3 |
|-----------|---------|---------|---------|
| Param 1   | Value   | Value   | Value   |
| Param 2   | Value   | Value   | Not reported |

IMPORTANT: Do NOT add empty rows like:
| - | | | |

## Key Findings
- Finding 1

## Limitations
- Notes
"""

    # Count tokens
    input_tokens = count_tokens(system_prompt) + count_tokens(user_prompt)
    logging.info(f"Total input tokens: {input_tokens}")
    
    # Reduce max_tokens to fit within 16k limit
    # 16385 total - input_tokens - safety margin
    max_output_tokens = min(2000, 16385 - input_tokens - 500)
    
    if max_output_tokens < 500:
        raise ValueError(f"Context too large. Input: {input_tokens} tokens. Please upload fewer papers or ask a more specific question.")
    
    logging.info(f"Using max_tokens: {max_output_tokens}")
    
    # Call OpenAI
    logging.info("Calling OpenAI API...")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=max_output_tokens
    )
    
    answer = response.choices[0].message.content
    
    # Token usage from API
    usage = response.usage
    token_usage = {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "input_cost_usd": round((usage.prompt_tokens / 1000) * 0.0015, 6),
        "output_cost_usd": round((usage.completion_tokens / 1000) * 0.002, 6),
        "total_cost_usd": round(
            (usage.prompt_tokens / 1000) * 0.0015 + 
            (usage.completion_tokens / 1000) * 0.002, 6
        )
    }
    
    return answer, token_usage

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Systematic Review API Starting...")
    print("=" * 60)
    print(f"📂 Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"📂 Index folder: {os.path.abspath('indexes')}")
    print(f"🌐 Server: http://localhost:5001")
    print(f"🔑 OpenAI Key: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Missing'}")
    print("=" * 60)
    print("\nReady to accept requests!")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, host='0.0.0.0', port=5001)