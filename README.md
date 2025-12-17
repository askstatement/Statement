
<p align="center">
  <img src="https://cdn.askstatement.com/images/statement-icon.png" alt="Image" width="400" />
</p>

# 👋 Welcome to Statement

Statement is a modern, open source financial intelligence platform powered by GPT. It connects directly to your financial tools and lets you explore your data through natural, conversational queries. Ask questions, review trends, or dive into specifics - all in plain language.

Our goal is to give founders and developers a reliable, well-structured foundation for understanding their finances. This monorepo includes everything behind Statement: the financial data models, the reasoning and NLP layers, the APIs and SDKs, and the web and upcoming mobile clients.

Learn more at http://askstatement.com.

## Features

| ![Image 1](https://cdn.askstatement.com/images/Image2-Github.gif) | ![Image 2](https://cdn.askstatement.com/images/Image3-Github.gif) |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |

- Unified Financial Data - Connect revenue, accounting, and revenue tools and get all your financial data structured in one place.
- Instant Insights - Receive clear, real-time answers about cash flow, spending, performance, and runway without touching spreadsheets.
- API and GPT Interface - Build with APIs or use the conversational interface to query your financials in plain language.
- Open-source and Self-hosted - Run Statement on your own infrastructure and tailor it to your security and compliance requirements.

## Tech Stack

### Backend
- **Framework**: FastAPI 0.111.0
- **Database**: MongoDB 8.0 (async via Motor), Elasticsearch 8.13.0
- **Language Models**: OpenAI API
- **Job Scheduling**: Croniter
- **Authentication**: Python-Jose, Passlib
- **Cloud Storage**: AWS S3 (via Boto3)

### Frontend
- **Framework**: Next.js 15.3.5 with React 19
- **Styling**: SASS
- **Authentication**: Azure MSAL
- **Charts**: D3.js
- **UI Components**: React Toastify
- **Financial Integrations**: Plaid Link, Stripe

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Server**: Uvicorn with Standard Extensions
- **Analytics**: PostHog

## Project Structure

```
Statement/
├── backend/                          # FastAPI backend
│   ├── agents/                       # AI agent implementations
│   │   ├── db/                       # Database query agents
│   │   ├── finaliser_agent.py        # Final response agent
│   │   ├── planner_agent.py          # Planning agent
│   │   └── prompts/                  # Agent prompt templates
│   ├── core/                         # Core functionality
│   │   ├── base_*.py                 # Base classes for API, DB, services, etc.
│   │   ├── db/                       # Database clients (MongoDB, Elasticsearch)
│   │   ├── decorators.py             # Auth & utility decorators
│   │   ├── loader.py                 # Dynamic module loader
│   │   ├── logger.py                 # Logging configuration
│   │   └── registry.py               # Service registry
│   ├── cron/                         # Scheduled jobs
│   │   ├── base_cron.py              # Base cron job class
│   │   ├── registry.py               # Cron registry
│   │   ├── runner.py                 # Cron executor
│   │   └── scheduler.py              # Job scheduler
│   ├── interfaces/                   # Public API interfaces
│   │   └── chat/                     # Chat completion API
│   ├── llm/                          # Language model abstraction
│   │   ├── agent.py                  # Base agent class
│   │   ├── provider.py               # LLM provider interface
│   │   ├── tool.py                   # Tool definitions
│   │   └── providers/                # Provider implementations
│   ├── modules/                      # Business logic modules
│   │   ├── auth/                     # Authentication
│   │   ├── chat/                     # Chat functionality
│   │   ├── settings/                 # User settings
│   │   ├── user/                     # User management
│   │   └── stripe/                   # Stripe payments
│   ├── services/                     # Third-party service integrations
│   │   └── stripe/                   # Stripe service
│   ├── server.py                     # FastAPI app initialization
│   ├── requirements.txt              # Python dependencies
│   └── Dockerfile                    # Backend container
│
├── frontend/                         # Next.js frontend
│   ├── components/                   # React components
│   │   ├── chat/                     # Chat UI components
│   │   ├── layout/                   # Layout components
│   │   ├── settings/                 # Settings UI
│   │   └── uiElements/               # Reusable UI elements
│   ├── containers/                   # Page containers
│   │   ├── chat/
│   │   ├── home/
│   │   ├── login/
│   │   ├── signup/
│   │   └── reset-password/
│   ├── context/                      # React context providers
│   │   ├── ProjectContext.js
│   │   └── SessionContext.js
│   ├── src/
│   │   ├── app/                      # Next.js app directory
│   │   └── middleware.js             # Middleware
│   ├── public/                       # Static assets
│   ├── style/                        # Global & component styles
│   ├── utils/                        # Utility functions
│   ├── package.json
│   └── Dockerfile                    # Frontend container
│
├── docker-compose.yml                # Multi-container orchestration
├── .env.example                      # Environment variables template
└── LICENSE
```

## Getting Started

### Prerequisites

- Docker & Docker Compose (for containerized setup)
- Python 3.9+ (for local backend development)
- Node.js 18+ (for local frontend development)
- MongoDB 8.0
- Elasticsearch 8.13.0

### Installation

#### Using Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/askstatement/Statement.git
   cd Statement
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables**
   ```bash
   # Edit .env with your configuration
   ELASTIC_PASSWORD=your_password
   OPENAI_API_KEY=your_key
   STRIPE_API_KEY=your_key
   # ... other variables
   ```

4. **Start services**
   ```bash
   docker-compose up -d
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8765
   - Elasticsearch: http://localhost:9200

#### Local Development Setup

##### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp ../.env.example ../.env
# Edit .env with your configuration

# Run server
python server.py
```

##### Frontend

```bash
cd frontend

# Install dependencies
yarn install

# Run development server
yarn dev
```

Access frontend at http://localhost:3000

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for full list):

```bash
# Database
MONGO_HOST=localhost
MONGO_USER=statement@25
MONGO_PASSWORD=kY2xUqkxGhJU
MONGO_PORT=27017
MONGO_DB_NAME=statementai
ELASTICSEARCH_HOSTS=http://localhost:9200
ELASTIC_USERNAME=elastic
ELASTIC_PASSWORD=your_password

# API Keys
OPENAI_API_KEY=sk-...
STRIPE_API_KEY=sk_live_...

# Server
ENABLE_CRON=true
LOG_LEVEL=INFO

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8765
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_...
```

## API Documentation

### Authentication

Protected endpoints require JWT token in Authorization header:
```
Authorization: Bearer <token>
```

### Chat Endpoints

- **POST** `/api/v1/chat/completions` - Create chat completion (API key auth)
- **WebSocket** `/ws/chat` - Real-time chat (project auth)

### Core Endpoints

- **GET** `/api/auth/login` - User login
- **POST** `/api/auth/register` - User registration
- **GET** `/api/user/profile` - Get user profile
- **PUT** `/api/settings` - Update user settings

Full API documentation available at `/docs` when server is running (Swagger UI).

## Architecture

### Agent System

The platform uses a multi-agent architecture:

1. **Agent Router** - Routes requests to appropriate agents
2. **Planner Agent** - Plans the approach to solve user queries
3. **Query Agent** - Executes Elasticsearch queries
4. **Finaliser Agent** - Synthesizes final response

### Data Pipeline

```
User Input
    ↓
Authentication & Authorization
    ↓
Agent Router
    ↓
Planner Agent (decide approach)
    ↓
Query Agent (execute search)
    ↓
Summariser Tools (process results)
    ↓
Finaliser Agent (format response)
    ↓
User Response
```

### WebSocket Communication

Real-time chat uses WebSocket for bidirectional communication:
```
Client → [authenticate] → Server
Server → [emit messages] → Client
```

## Development

### Code Style

- **Backend**: Follow PEP 8 guidelines
- **Frontend**: ESLint configuration in place

### Logging

Structured logging via `core.logger`:
```python
from core.logger import Logger

logger = Logger(__name__)
logger.info("Message")
logger.error("Error occurred")
```

## Troubleshooting

### Module Import Errors

If you encounter "No module named 'db'" errors:
- Ensure PYTHONPATH includes project root: `export PYTHONPATH="${PYTHONPATH}:/path/to/Statement/backend"`
- Check that all imports use absolute paths from project root

### Database Connection Issues

- **MongoDB**: Ensure MongoDB is running and credentials are correct
- **Elasticsearch**: Check Elasticsearch health at `http://localhost:9200/_cluster/health`

### WebSocket Connection Failures

- Verify project authentication token is valid
- Check CORS configuration in `server.py`

## Performance Optimization

- **Caching**: Query results cached via Elasticsearch
- **Async/Await**: FastAPI handles concurrent requests efficiently
- **Lazy Loading**: ML models loaded on-demand via transformers library
- **Document Processing**: PDF processing uses multi-page batching

## Security

- **Authentication**: JWT tokens with secure signing
- **Authorization**: Role-based access control via decorators
- **Secrets**: Sensitive data stored in environment variables
- **CORS**: Configured for frontend domain only
- **SQL Injection Prevention**: All queries use parameterized operations

## Deployment

### Docker Deployment

Services are containerized and orchestrated via Docker Compose:

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Production Considerations

- Set `DEBUG=false` in environment
- Use strong database passwords
- Configure proper CORS origins
- Enable HTTPS/SSL
- Set up monitoring and alerting
- Configure backup strategy for MongoDB

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Commit changes: `git commit -am 'feat: add feature details'`
3. Push to branch: `git push origin feature/my-feature`
4. Submit pull request

## License

This project is licensed under the LICENSE file.

## Support & Contact

For issues, questions, or contributions:
- GitHub Issues: [Statement/issues](https://github.com/askstatement/Statement/issues)
- Email: hello@askstatement.com

## Acknowledgments

- FastAPI framework
- OpenAI API
- Elasticsearch
- MongoDB
- Next.js team
