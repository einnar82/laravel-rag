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

    SYSTEM_TEMPLATE = """You are a helpful Laravel framework documentation assistant. Your task is to answer questions about Laravel based ONLY on the provided documentation context.

CRITICAL RULES:
- You MUST ONLY use information from the provided context below
- DO NOT use any knowledge outside of the provided context
- DO NOT make up, invent, or hallucinate any information
- If the context does not contain enough information to answer the question, you MUST explicitly state: "I cannot answer this question based on the provided Laravel documentation context."
- When providing answers, you MUST cite the specific source sections (file names and section titles)
- If the context is empty or says "No relevant documentation found", you MUST respond with: "I cannot answer this question as no relevant Laravel documentation was found."

Guidelines:
- Answer questions accurately based ONLY on the provided context
- Provide code examples when available in the context
- Reference specific sections when helpful (file names and sections)
- Be concise but thorough
- If multiple Laravel versions are relevant, clarify version-specific information
- Always indicate which source(s) you used for your answer

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
        min_similarity: Optional[float] = None,
    ) -> tuple[str, List[Dict], bool]:
        """Retrieve relevant context for a query with similarity filtering.

        Args:
            query: User query
            version_filter: Filter by Laravel version
            min_similarity: Minimum similarity threshold (default: from settings)

        Returns:
            Tuple of (formatted_context, source_documents, cache_hit)
        """
        min_similarity = min_similarity or settings.min_similarity_threshold

        # Search vector store (caching handled internally)
        results = self.vector_store.search(
            query=query,
            top_k=self.top_k,
            version_filter=version_filter,
        )

        # Check if results came from cache (approximate - cache hit if results exist immediately)
        cache_hit = len(results) > 0  # Simplified check

        if not results:
            logger.warning("No relevant context found")
            return "No relevant documentation found.", [], cache_hit

        # Filter by similarity threshold
        filtered_results = []
        for result in results:
            similarity = result.get("similarity", 1.0 - result.get("distance", 1.0))
            if similarity >= min_similarity:
                filtered_results.append(result)
            else:
                logger.debug(f"Filtered out result with similarity {similarity:.3f} < {min_similarity}")

        if not filtered_results:
            logger.warning(f"No results meet similarity threshold {min_similarity}")
            return "No relevant documentation found that meets the similarity threshold.", [], cache_hit

        # Format context
        context_parts = []
        for i, result in enumerate(filtered_results, 1):
            metadata = result["metadata"]
            content = result["document"]
            similarity = result.get("similarity", 1.0 - result.get("distance", 1.0))

            context_part = f"""
[Source {i}] File: {metadata['file']}, Section: {metadata['section']}
Version: {metadata['version']}, Anchor: {metadata['anchor']}, Similarity: {similarity:.3f}

{content}
---
"""
            context_parts.append(context_part)

        formatted_context = "\n".join(context_parts)
        return formatted_context, filtered_results, cache_hit

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

    def verify_answer(self, answer: str, context: str, question: str) -> Dict[str, str]:
        """Verify that the answer is supported by the retrieved context.

        Args:
            answer: Generated answer
            context: Retrieved context
            question: Original question

        Returns:
            Dictionary with verification status and details
        """
        if not context or context.startswith("No relevant documentation found"):
            return {
                "status": "insufficient_context",
                "verified": False,
                "reason": "No relevant context was retrieved",
            }

        # Use LLM to verify answer is supported by context
        verification_prompt = f"""You are a verification assistant. Your task is to check if an answer is supported by the provided context.

Question: {question}

Answer to verify: {answer}

Context from documentation:
{context}

Instructions:
- Check if the answer is directly supported by information in the context
- Check if the answer contains any information NOT found in the context (hallucination)
- Respond with ONLY one word: "VERIFIED" if the answer is fully supported by context, or "UNVERIFIED" if it contains unsupported information or hallucination

Your response (VERIFIED or UNVERIFIED):"""

        try:
            response = self.ollama_client.chat(
                model=self.llm_model,
                messages=[{"role": "user", "content": verification_prompt}],
                options={"temperature": 0.1, "num_predict": 50},  # Low temperature for verification
            )

            verification_result = response["message"]["content"].strip().upper()
            is_verified = "VERIFIED" in verification_result

            return {
                "status": "verified" if is_verified else "unverified",
                "verified": is_verified,
                "reason": "Answer is supported by context" if is_verified else "Answer may contain unsupported information",
            }

        except Exception as e:
            logger.warning(f"Verification failed: {e}, defaulting to unverified")
            return {
                "status": "verification_failed",
                "verified": False,
                "reason": f"Verification process failed: {str(e)}",
            }

    def query(
        self,
        question: str,
        version_filter: Optional[str] = None,
        include_sources: bool = False,
        temperature: float = 0.7,
        min_similarity: Optional[float] = None,
        verify_answer: bool = True,
    ) -> Dict:
        """Execute a complete RAG query with verification.

        Args:
            question: User question
            version_filter: Filter by Laravel version
            include_sources: Include source documents in response
            temperature: LLM temperature parameter
            min_similarity: Minimum similarity threshold
            verify_answer: Whether to verify the answer against context

        Returns:
            Dictionary with answer, verification status, and optional sources
        """
        logger.info(f"Processing query: '{question}'")

        # Retrieve context with similarity filtering
        context, sources, cache_hit = self.retrieve_context(
            query=question,
            version_filter=version_filter,
            min_similarity=min_similarity,
        )

        # Check if we have valid context
        if not sources or context.startswith("No relevant documentation found"):
            logger.warning("No valid context found, skipping LLM generation")
            return {
                "question": question,
                "answer": "I cannot answer this question as no relevant Laravel documentation was found that meets the similarity threshold.",
                "version_filter": version_filter,
                "verified": False,
                "verification_status": "insufficient_context",
                "similarity_scores": [],
                "cache_hit": cache_hit,
            }

        # Generate response
        answer = self.generate_response(
            query=question,
            context=context,
            temperature=temperature,
        )

        # Verify answer if requested
        verification_result = None
        if verify_answer:
            verification_result = self.verify_answer(answer, context, question)

        # Extract similarity scores
        similarity_scores = [src.get("similarity", 1.0 - src.get("distance", 1.0)) for src in sources]

        # Prepare response
        response = {
            "question": question,
            "answer": answer,
            "version_filter": version_filter,
            "verified": verification_result["verified"] if verification_result else None,
            "verification_status": verification_result["status"] if verification_result else None,
            "similarity_scores": similarity_scores,
            "cache_hit": cache_hit,
        }

        if include_sources:
            response["sources"] = [
                {
                    "file": src["metadata"]["file"],
                    "section": src["metadata"]["section"],
                    "version": src["metadata"]["version"],
                    "anchor": src["metadata"]["anchor"],
                    "heading_path": src["metadata"]["heading_path"],
                    "distance": src.get("distance"),
                    "similarity": src.get("similarity", 1.0 - src.get("distance", 1.0)),
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

            # Check for exact match or with :latest tag
            model_found = False
            if self.llm_model in available_models:
                model_found = True
            elif f"{self.llm_model}:latest" in available_models:
                model_found = True
                logger.info(f"Model {self.llm_model} found as {self.llm_model}:latest")
            elif any(m.startswith(f"{self.llm_model}:") for m in available_models):
                # Check if model exists with any tag
                model_found = True
                matching = [m for m in available_models if m.startswith(f"{self.llm_model}:")]
                logger.info(f"Model {self.llm_model} found as {matching[0]}")

            if model_found:
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
