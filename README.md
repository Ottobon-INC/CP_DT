# Digital Twin Service

A standalone Python service built using **FastAPI** as the backend web framework and **LangGraph** as the agent orchestration framework, following Clean Architecture principles.

## Project Structure

The project has been organized with a separation of layers (clean architecture) to support maintainable growth as agentic nodes, database persistence, and schedulers are integrated:

```text
digital-twin/
├── app/
│   ├── api/          # FastAPI routers and route handlers (e.g., /health)
│   ├── graphs/       # LangGraph workflows and state definitions
│   ├── nodes/        # LangGraph individual node execution logic (agent actions, tools)
│   ├── services/     # Core domain business logic and use cases
│   ├── database/     # SQLAlchemy engine, session configurations, and db connections
│   ├── models/       # Database entities (SQLAlchemy) and DTOs (Pydantic)
│   ├── memory/       # LangGraph checkpointers (in-memory or postgres-based checkpointers)
│   ├── schedulers/   # Background jobs, cron jobs, and scheduler scripts
│   ├── prompts/      # System prompts, templates, and agent personalities
│   ├── utils/        # Shared utility functions and helpers
│   └── config/       # Pydantic Settings configuration parser
├── tests/            # Test suite (pytest)
├── main.py           # Application entry point and bootstrap
├── requirements.txt  # Python dependency list
├── Dockerfile        # Docker container image build instructions
├── docker-compose.yml# Multi-container local orchestration (App + PostgreSQL)
├── .env.example      # Environment variables template file
└── README.md         # Project documentation (this file)
```

---

## Getting Started

### Local Setup

1. **Create and Activate a Virtual Environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy the example configuration to a local `.env` file:
   ```bash
   cp .env.example .env
   ```

4. **Start the Service:**
   ```bash
   python main.py
   ```
   The service will start by default at `http://127.0.0.1:8000`. You can access the automatic documentation at `http://127.0.0.1:8000/docs`.

---

## Docker Setup

To orchestrate the service alongside a PostgreSQL database database instance locally:

1. **Build and Start Container Services:**
   ```bash
   docker compose up --build
   ```

2. **Verify Services:**
   - FastAPI: `http://localhost:8000/health`
   - PostgreSQL: standard port `5432`

---

## Testing

To run the unit tests:
```bash
python -m pytest
```
