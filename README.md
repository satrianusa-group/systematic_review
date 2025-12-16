# 📚 Systematic Review Chatbot

An AI-powered systematic review assistant that analyzes multiple research papers and creates comprehensive comparison tables using OpenAI and FAISS vector search.

## ✨ Features

- 📄 **PDF Upload & Processing** - Upload multiple research papers
- 🔍 **FAISS Vector Search** - Fast semantic search across documents
- 📊 **Comparison Tables** - Automatic generation of comparison tables
- 💰 **Token Usage Tracking** - Real-time cost monitoring
- 🎨 **Beautiful UI** - Modern, responsive interface
- 🐳 **Docker Ready** - Single-container deployment

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/systematic-review-chatbot.git
   cd systematic-review-chatbot
   ```

2. **Create .env file**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-proj-your-key-here
   ```

3. **Build and run**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost
   - Backend API: http://localhost:5001

## 📁 Project Structure

```
systematic-review-chatbot/
├── Dockerfile                    # Multi-stage Docker build
├── docker-compose.yml            # Docker Compose configuration
├── nginx.conf                    # Nginx web server config
├── .env.example                  # Environment template
├── README.md                     # This file
├── backend/
│   ├── app.py                    # Flask API server
│   ├── utils.py                  # Helper functions
│   ├── requirements.txt          # Python dependencies
│   ├── uploads/                  # Uploaded PDFs (gitignored)
│   └── indexes/                  # FAISS indexes (gitignored)
└── frontend/
    ├── index.html                # Main UI
    └── app.js                    # Frontend logic
```

## 🛠️ Usage

### 1. Upload Papers
- Click "Choose PDF Files"
- Select one or more research papers (PDF format)
- Click "Upload Papers"
- Wait for processing (you'll see token usage stats)

### 2. Ask Questions
- Type your question in the input box
- Examples:
  - "What are the most important regulations mentioned?"
  - "Compare the methodology across all papers"
  - "What are the key findings in each paper?"

### 3. Get Results
- Receive formatted answers with comparison tables
- View token usage and costs
- Ask follow-up questions

## 💰 Cost Estimation

Based on OpenAI GPT-3.5-turbo-16k pricing:

| Operation | Tokens | Cost |
|-----------|--------|------|
| Upload 1 paper | ~2,800 | $0.0004 |
| Query (5 papers) | ~10,000 | $0.015 |
| **Typical session (5 papers, 10 queries)** | **~102,000** | **~$0.17** |

Very affordable for research purposes!

## 🔧 Development

### Run without Docker (Development)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Frontend:**
Open `frontend/index.html` in browser or use:
```bash
cd frontend
python -m http.server 8000
```

### Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `UPLOAD_API_KEY` - API key for uploads (optional)

## 🐳 Docker Commands

```bash
# Build and start
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart

# Enter container
docker-compose exec app bash
```

## 📊 Technical Details

### Backend Stack
- **Python 3.10**
- **Flask** - Web framework
- **OpenAI API** - GPT-3.5-turbo-16k for analysis
- **FAISS** - Vector similarity search
- **PyPDF2** - PDF text extraction
- **tiktoken** - Token counting

### Frontend Stack
- **Vanilla JavaScript** - No framework overhead
- **HTML5/CSS3** - Modern UI
- **Nginx** - Web server

### Architecture
- Single Docker container with Supervisor
- Nginx proxies frontend and routes `/api` to Flask
- FAISS stores document embeddings for fast retrieval
- Persistent volumes for uploads and indexes

## 🔒 Security Notes

- ⚠️ Never commit `.env` file to Git
- ⚠️ Keep your OpenAI API key secret
- ⚠️ Use HTTPS in production
- ⚠️ Implement authentication for production use

## 🚀 Deployment

### Deploy to Cloud

**AWS EC2 / Azure VM / GCP Compute:**
```bash
# On server
git clone https://github.com/yourusername/systematic-review-chatbot.git
cd systematic-review-chatbot
nano .env  # Add your API keys
docker-compose up -d --build
```

**Docker Hub:**
```bash
# Build and push
docker build -t yourusername/systematic-review:latest .
docker push yourusername/systematic-review:latest

# On server
docker pull yourusername/systematic-review:latest
docker run -d -p 80:80 -p 5001:5001 --env-file .env yourusername/systematic-review:latest
```

## 🐛 Troubleshooting

### Port already in use
Change ports in `docker-compose.yml`:
```yaml
ports:
  - "8080:80"    # Change 80 to 8080
```

### OpenAI API errors
- Check your API key is correct in `.env`
- Verify you have credits: https://platform.openai.com/usage
- Check rate limits

### Container won't start
```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose down
docker-compose up --build
```

## 📝 License

MIT License - feel free to use for research and commercial projects

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Contact

For questions or issues, please open an issue on GitHub.

## 🙏 Acknowledgments

- OpenAI for GPT-3.5 API
- Facebook AI for FAISS
- All the amazing open-source libraries used

---