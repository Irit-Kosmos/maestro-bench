# maestro-bench

**MAESTRO Experiment Bench** - A complete experiment traceability system for scientific research with AI agents and LLM model evaluation.

## 📋 Overview

This project provides a comprehensive platform for managing and tracking scientific experiments involving AI agents, large language models (LLMs), and datasets. It includes a FastAPI backend with experiment management capabilities and a Nuxt frontend for visualization and interaction.

## 🏗️ Architecture

- **Frontend**: Nuxt application
- **Backend**: FastAPI-based REST API with SQLite database
- **Queue System**: Redis for background job processing
- **Containerization**: Docker Compose for easy deployment

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js (for frontend development)
- Python 3.11+ (for backend development)

### Running with Docker Compose
```bash
docker-compose up -d
```

This will start:
- Backend API on `http://localhost:8000`
- Frontend on `http://localhost:3000`
- Redis on `http://localhost:6380`

## 🔧 Configuration

The project uses environment variables for configuration. Key settings include:

- `MAESTRO_API_BASE_URL`: Base URL for MAESTRO API (default: `http://host.docker.internal:8001`)
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6380/0`)
- `API_HOST`: Backend host (default: `0.0.0.0`)
- `API_PORT`: Backend port (default: `8000`)
- `DATABASE_URL`: Database connection string (default: `sqlite:///./app.db`)

## 📊 Features

- **Experiment Management**: Create, track, and manage scientific experiments
- **Agent Teams**: Configure and deploy AI agent teams for experiments
- **Model Integration**: Support for multiple LLM providers (OpenAI, Anthropic, Mistral)
- **Prompt Management**: Store and version control prompts
- **Dataset Management**: Upload and manage experimental datasets
- **Execution Tracking**: Monitor experiment execution with detailed logging
- **Results Analysis**: View and analyze experiment results