# NOTSY - AI-Powered Personal Knowledge Management

Notsy is an AI-powered personal knowledge management app for students that lets you build your own "knowledge universe" with RAG-powered chat, branching conversations, and a study graph.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   React/Vue     │────▶│  Spring Boot    │
│   Frontend      │◀────│  Backend :8080  │
└─────────────────┘     └────────┬────────┘
                                 │ HTTP/WebClient
                                 ▼
                        ┌─────────────────┐
                        │  FastAPI AI     │
                        │  Service :8000  │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   ChromaDB      │
                        │   (Vectors)    │
                        └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │   PostgreSQL    │
                        │   (Relational)  │
                        └─────────────────┘
```

## Tech Stack

- **Backend**: Java 17, Spring Boot 3.2, PostgreSQL, JWT Auth, WebClient
- **AI Service**: Python 3.11, FastAPI, LangChain, ChromaDB, Groq API (llama3-70b)
- **File Storage**: Local filesystem (./uploads folder)
- **Orchestration**: Docker Compose

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Java 17+ (for local development)
- Python 3.11+ (for local AI service development)
- Groq API Key ([Get one here](https://console.groq.com/))

### Setup

1. **Clone and configure environment:**

```bash
# Create .env files from examples
cp backend/.env.example backend/.env
cp ai-service/.env.example ai-service/.env

# Edit both .env files and add your GROQ_API_KEY
```

2. **Get your Groq API Key:**
   - Sign up at [console.groq.com](https://console.groq.com/)
   - Create a new API key
   - Add it to `ai-service/.env`

3. **Start with Docker Compose:**

```bash
docker-compose up -d
```

4. **Access the services:**
   - Backend API: http://localhost:8080
   - AI Service: http://localhost:8000
   - AI Service Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Local Development

**Backend (Spring Boot):**

```bash
cd backend
./mvnw spring-boot:run
# Or with Maven:
mvn spring-boot:run
```

**AI Service:**

```bash
cd ai-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Database:**

```bash
# PostgreSQL runs via Docker Compose on port 5432
# Credentials: notsy/notsy123
```

## Project Structure

```
notsy/
├── backend/                    # Spring Boot application
│   ├── src/main/java/com/notsy/
│   │   ├── entity/            # JPA entities
│   │   ├── repository/        # Spring Data repositories
│   │   ├── service/           # Business logic
│   │   ├── controller/        # REST controllers
│   │   ├── dto/               # Request/Response DTOs
│   │   ├── security/          # JWT auth components
│   │   └── exception/         # Exception handling
│   ├── src/main/resources/
│   │   └── application.yml   # App configuration
│   ├── Dockerfile
│   └── pom.xml
├── ai-service/                 # FastAPI AI service
│   ├── app/
│   │   ├── api/              # API route handlers
│   │   ├── core/             # RAG engine, embeddings, etc.
│   │   ├── models/           # Pydantic schemas
│   │   └── services/         # ChromaDB wrapper
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── docker-compose.yml
├── uploads/                    # File storage (gitignored)
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `GET /api/auth/me` - Get current user

### Notebooks
- `GET /api/notebooks` - List notebooks
- `POST /api/notebooks` - Create notebook
- `GET /api/notebooks/{id}` - Get notebook
- `PUT /api/notebooks/{id}` - Update notebook
- `DELETE /api/notebooks/{id}` - Delete notebook

### Topics
- `GET /api/notebooks/{notebookId}/topics` - List topics
- `POST /api/notebooks/{notebookId}/topics` - Create topic
- `GET /api/notebooks/{notebookId}/topics/{topicId}` - Get topic
- `PUT /api/notebooks/{notebookId}/topics/{topicId}` - Update topic
- `DELETE /api/notebooks/{notebookId}/topics/{topicId}` - Delete topic
- `POST /api/notebooks/{notebookId}/topics/{topicId}/reorder` - Reorder topics

### Resources
- `GET /api/topics/{topicId}/resources` - List resources
- `POST /api/topics/{topicId}/resources/upload` - Upload file
- `POST /api/topics/{topicId}/resources/link` - Add URL link
- `DELETE /api/topics/{topicId}/resources/{resourceId}` - Delete resource
- `POST /api/topics/{topicId}/resources/{resourceId}/reembed` - Re-embed resource

### Conversations
- `GET /api/topics/{topicId}/conversations` - List conversations
- `POST /api/topics/{topicId}/conversations` - Create conversation
- `GET /api/topics/{topicId}/conversations/{conversationId}` - Get conversation
- `DELETE /api/topics/{topicId}/conversations/{conversationId}` - Delete conversation
- `POST /api/topics/{topicId}/conversations/{conversationId}/chat` - Send message
- `POST /api/topics/{topicId}/conversations/{conversationId}/branch` - Create branch
- `POST /api/topics/{topicId}/conversations/{conversationId}/merge` - Merge/discard branch
- `GET /api/topics/{topicId}/conversations/{conversationId}/branches` - List branches

### Knowledge Graph
- `GET /api/notebooks/{notebookId}/graph` - Get graph data
- `POST /api/notebooks/{notebookId}/graph/generate` - Generate relations
- `POST /api/notebooks/{notebookId}/graph/relations` - Add relation
- `DELETE /api/notebooks/{notebookId}/graph/relations/{relationId}` - Delete relation

## Learning Modes

Notsy offers 5 different AI learning modes:

1. **GO_CRAZY** - Exploratory mode for creative connections and lateral thinking
2. **DEV_MODE** - Technical expert for developers with code examples
3. **MASTER_THIS** - Comprehensive guide from fundamentals to advanced
4. **LAST_MINUTE** - Concise exam prep with bullet points
5. **TEACH_ME_TECH** - Beginner-friendly tech educator

## Features

### RAG-Powered Chat
All AI responses are grounded in your uploaded study materials using Retrieval-Augmented Generation.

### Branching Conversations
Explore tangents without polluting main conversations - like Git branches for your discussions.

### Study Graph
Visualize how topics connect to each other with AI-generated relationships.

### Multi-Format Support
Upload PDFs, images, videos, text files, and web links. All content is processed and made searchable.

## Environment Variables

### Backend (.env)
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=notsydb
DB_USER=notsy
DB_PASSWORD=notsy123
JWT_SECRET=your-super-secret-key-256-bits
JWT_EXPIRATION=86400000
AI_SERVICE_URL=http://localhost:8000
FILE_UPLOAD_DIR=./uploads
CORS_ORIGINS=http://localhost:3000
```

### AI Service (.env)
```env
GROQ_API_KEY=your_groq_api_key
SPRING_BOOT_CALLBACK_URL=http://localhost:8080
CHROMA_PERSIST_DIR=./chroma_db
UPLOAD_BASE_DIR=./uploads
```

## License

MIT
