# Configuration Template
# IMPORTANT: Copy this file to config.py and fill in your actual API keys
# The config.py file will be ignored by git for security

# Neo4j Database (Local installation required)
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your-neo4j-password-here"  # Replace with your Neo4j password

# OpenRouter API (Alternative to OpenAI)
# Get your API key from: https://openrouter.ai/keys
OPENROUTER_API_KEY = "your-openrouter-api-key-here"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# OpenAI API (Optional - leave empty if using OpenRouter)
OPENAI_API_KEY = "your-openai-api-key-here"

# Pinecone API (Required for vector database)
# Get your API key from: https://app.pinecone.io/
PINECONE_API_KEY = "your-pinecone-api-key-here"
PINECONE_ENV = "us-east1-gcp"  # Check your Pinecone dashboard for correct environment
PINECONE_INDEX_NAME = "vietnam-travel"
PINECONE_VECTOR_DIM = 384  # For sentence-transformers all-MiniLM-L6-v2 model

# Instructions:
# 1. Sign up for OpenRouter: https://openrouter.ai/keys
# 2. Sign up for Pinecone: https://app.pinecone.io/
# 3. Install Neo4j Desktop: https://neo4j.com/download/
# 4. Fill in your actual API keys above