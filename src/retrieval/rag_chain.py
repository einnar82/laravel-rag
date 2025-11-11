"""RAG chain implementation using LangChain and Ollama."""

from typing import Dict, List, Optional

import ollama
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.config import settings
from src.indexing.vector_store import VectorStore
from src.utils.logger import app_logger as logger


class RAGChain:
    """RAG (Retrieval-Augmented Generation) chain for Laravel documentation queries."""

    SYSTEM_TEMPLATE = """You are a helpful Laravel framework documentation assistant. Your task is to answer questions about Laravel based on the provided documentation context.

Guidelines:
- Answer questions accurately based ONLY on the provided context
- If the context doesn't contain enough information, say so clearly
- Provide code examples when available in the context
- Reference specific sections when helpful (file names and sections)
- Be concise but thorough
- If multiple Laravel versions are relevant, clarify version-specific information

Context from Laravel Documentation:
{context}

Question: {question}

Answer:"""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        llm_model: Optional[str] = None,
        ollama_host: Optional[str] = None,
        top_k: Optional[int] = None,
    ):
        """Initialize the RAG chain.

        Args:
            vector_store: VectorStore instance for retrieval
            llm_model: Name of the LLM model
            ollama_host: Ollama API host
            top_k: Number of documents to retrieve
        """
        self.vector_store = vector_store or VectorStore()
        self.llm_model = llm_model or settings.llm_model
        self.ollama_host = ollama_host or settings.ollama_host
        self.top_k = top_k or settings.top_k
        self.ollama_client = ollama.Client(host=self.ollama_host)

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template(self.SYSTEM_TEMPLATE)

        logger.info(f"Initialized RAG chain with model: {self.llm_model}")

    def retrieve_context(
        self,
        query: str,
        version_filter: Optional[str] = None,
    ) -> tuple[str, List[Dict]]:
        """Retrieve relevant context for a query.

        Args:
            query: User query
            version_filter: Filter by Laravel version

        Returns:
            Tuple of (formatted_context, source_documents)
        """
        # Search vector store
        results = self.vector_store.search(
            query=query,
            top_k=self.top_k,
            version_filter=version_filter,
        )

        if not results:
            logger.warning("No relevant context found")
            return "No relevant documentation found.", []

        # Format context
        context_parts = []
        for i, result in enumerate(results, 1):
            metadata = result["metadata"]
            content = result["document"]

            context_part = f"""
[Source {i}] File: {metadata['file']}, Section: {metadata['section']}
Version: {metadata['version']}, Anchor: {metadata['anchor']}

{content}
---
"""
            context_parts.append(context_part)

        formatted_context = "\n".join(context_parts)
        return formatted_context, results

    def generate_response(
        self,
        query: str,
        context: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate response using the LLM.

        Args:
            query: User query
            context: Retrieved context
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response
        """
        # Format prompt
        formatted_prompt = self.prompt.format(
            context=context,
            question=query,
        )

        logger.debug(f"Generating response for query: '{query}'")

        try:
            # Call Ollama
            response = self.ollama_client.chat(
                model=self.llm_model,
                messages=[
                    {
                        "role": "user",
                        "content": formatted_prompt,
                    }
                ],
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )

            answer = response["message"]["content"]
            logger.debug("Successfully generated response")
            return answer

        except Exception as e:
            error_msg = f"Error generating response: {e}"
            logger.error(error_msg)
            return f"Sorry, I encountered an error generating the response: {str(e)}"

    def query(
        self,
        question: str,
        version_filter: Optional[str] = None,
        include_sources: bool = False,
        temperature: float = 0.7,
    ) -> Dict:
        """Execute a complete RAG query.

        Args:
            question: User question
            version_filter: Filter by Laravel version
            include_sources: Include source documents in response
            temperature: LLM temperature parameter

        Returns:
            Dictionary with answer and optional sources
        """
        logger.info(f"Processing query: '{question}'")

        # Retrieve context
        context, sources = self.retrieve_context(
            query=question,
            version_filter=version_filter,
        )

        # Generate response
        answer = self.generate_response(
            query=question,
            context=context,
            temperature=temperature,
        )

        # Prepare response
        response = {
            "question": question,
            "answer": answer,
            "version_filter": version_filter,
        }

        if include_sources:
            response["sources"] = [
                {
                    "file": src["metadata"]["file"],
                    "section": src["metadata"]["section"],
                    "version": src["metadata"]["version"],
                    "anchor": src["metadata"]["anchor"],
                    "heading_path": src["metadata"]["heading_path"],
                    "distance": src["distance"],
                }
                for src in sources
            ]

        logger.info("Query completed successfully")
        return response

    def check_llm_availability(self) -> bool:
        """Check if the LLM model is available.

        Returns:
            True if model is available
        """
        try:
            models = self.ollama_client.list()
            available_models = [m["name"] for m in models.get("models", [])]

            if self.llm_model in available_models:
                logger.info(f"Model {self.llm_model} is available")
                return True
            else:
                logger.warning(f"Model {self.llm_model} not found. Available: {available_models}")
                return False

        except Exception as e:
            logger.error(f"Error checking LLM availability: {e}")
            return False

    def pull_model(self) -> bool:
        """Pull the LLM model if not available.

        Returns:
            True if successful
        """
        try:
            logger.info(f"Pulling model {self.llm_model}...")
            self.ollama_client.pull(self.llm_model)
            logger.info(f"Successfully pulled {self.llm_model}")
            return True
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False
