"""Index validation utilities for quality checks."""

from pathlib import Path
from typing import Dict, List, Optional, Set

from src.config import settings
from src.indexing.vector_store import VectorStore
from src.utils.logger import app_logger as logger


class IndexValidator:
    """Validate indexing quality and completeness."""

    def __init__(self, vector_store: Optional[VectorStore] = None):
        """Initialize the validator.

        Args:
            vector_store: VectorStore instance to validate
        """
        self.vector_store = vector_store or VectorStore()

    def validate_indexing(self, version: Optional[str] = None) -> Dict:
        """Validate indexing quality.

        Args:
            version: Optional version to validate

        Returns:
            Dictionary with validation results
        """
        logger.info(f"Validating index for version: {version or 'all'}")

        issues = []
        stats = {
            "total_documents": 0,
            "duplicates": 0,
            "missing_metadata": 0,
            "empty_chunks": 0,
            "invalid_embeddings": 0,
        }

        try:
            # Get all documents (including embeddings for validation)
            where = {"version": version} if version else None
            all_docs = self.vector_store.collection.get(
                where=where,
                include=["embeddings", "documents", "metadatas"]
            )

            if not all_docs.get("ids"):
                return {
                    "valid": False,
                    "issues": ["No documents found in index"],
                    "stats": stats,
                }

            stats["total_documents"] = len(all_docs["ids"])

            # Check for duplicates
            seen_ids: Set[str] = set()
            for doc_id in all_docs["ids"]:
                if doc_id in seen_ids:
                    stats["duplicates"] += 1
                    issues.append(f"Duplicate document ID: {doc_id}")
                seen_ids.add(doc_id)

            # Check metadata and content
            required_metadata_fields = ["version", "file", "section", "anchor"]
            for i, metadata in enumerate(all_docs.get("metadatas", [])):
                # Check required metadata fields
                for field in required_metadata_fields:
                    if field not in metadata or not metadata[field]:
                        stats["missing_metadata"] += 1
                        issues.append(f"Missing metadata field '{field}' in document {all_docs['ids'][i]}")

                # Check for empty chunks
                doc_content = all_docs.get("documents", [])[i] if i < len(all_docs.get("documents", [])) else ""
                if not doc_content or not doc_content.strip():
                    stats["empty_chunks"] += 1
                    issues.append(f"Empty document content for ID: {all_docs['ids'][i]}")

            # Check embeddings (basic validation - non-zero vectors)
            embeddings = all_docs.get("embeddings", [])
            if embeddings:
                for i, embedding in enumerate(embeddings):
                    if not embedding or all(v == 0.0 for v in embedding):
                        stats["invalid_embeddings"] += 1
                        issues.append(f"Invalid embedding (all zeros) for document {all_docs['ids'][i]}")
            else:
                logger.warning("Embeddings not returned by ChromaDB, skipping embedding validation")

            is_valid = len(issues) == 0

            logger.info(f"Validation complete: {len(issues)} issues found")

            return {
                "valid": is_valid,
                "issues": issues[:100],  # Limit to first 100 issues
                "stats": stats,
                "issue_count": len(issues),
            }

        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "stats": stats,
            }

    def check_index_health(self, version: Optional[str] = None) -> Dict:
        """Check overall index health.

        Args:
            version: Optional version to check

        Returns:
            Dictionary with health metrics
        """
        logger.info(f"Checking index health for version: {version or 'all'}")

        try:
            stats = self.vector_store.get_stats()

            # Get version distribution
            versions = stats.get("versions", {})
            if version:
                doc_count = versions.get(version, 0)
            else:
                doc_count = stats.get("total_documents", 0)

            # Check document distribution
            version_distribution = {}
            if not version:
                version_distribution = versions
            else:
                version_distribution = {version: doc_count}

            # Calculate health score (0-100)
            health_score = 100
            health_issues = []

            if doc_count == 0:
                health_score = 0
                health_issues.append("No documents indexed")
            elif doc_count < 10:
                health_score -= 20
                health_issues.append("Very few documents indexed")

            # Run validation to check for issues
            validation = self.validate_indexing(version)
            if not validation["valid"]:
                issue_count = validation.get("issue_count", 0)
                health_score -= min(issue_count * 2, 50)  # Deduct up to 50 points
                health_issues.extend(validation["issues"][:5])  # Include top 5 issues

            health_status = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy"

            return {
                "status": health_status,
                "score": health_score,
                "total_documents": doc_count,
                "version_distribution": version_distribution,
                "issues": health_issues,
                "validation": validation,
            }

        except Exception as e:
            logger.error(f"Error checking index health: {e}")
            return {
                "status": "error",
                "score": 0,
                "error": str(e),
            }

    def verify_index_completeness(
        self, expected_files: List[str], version: str
    ) -> Dict:
        """Verify that all expected files are indexed.

        Args:
            expected_files: List of expected file names
            version: Laravel version

        Returns:
            Dictionary with completeness report
        """
        logger.info(f"Verifying index completeness for version {version}")

        try:
            # Get all indexed documents for this version
            all_docs = self.vector_store.collection.get(where={"version": version})

            indexed_files: Set[str] = set()
            for metadata in all_docs.get("metadatas", []):
                file_name = metadata.get("file", "")
                if file_name:
                    indexed_files.add(file_name)

            expected_set = set(expected_files)
            missing_files = expected_set - indexed_files
            extra_files = indexed_files - expected_set

            completeness = (len(indexed_files & expected_set) / len(expected_set) * 100) if expected_set else 0

            return {
                "complete": len(missing_files) == 0,
                "completeness_percentage": round(completeness, 2),
                "expected_files": len(expected_set),
                "indexed_files": len(indexed_files),
                "missing_files": list(missing_files),
                "extra_files": list(extra_files),
            }

        except Exception as e:
            logger.error(f"Error verifying completeness: {e}")
            return {
                "complete": False,
                "error": str(e),
            }

    def validate_embeddings(self, version: Optional[str] = None) -> Dict:
        """Validate that all documents have valid embeddings.

        Args:
            version: Optional version to validate

        Returns:
            Dictionary with embedding validation results
        """
        logger.info(f"Validating embeddings for version: {version or 'all'}")

        try:
            where = {"version": version} if version else None
            all_docs = self.vector_store.collection.get(
                where=where,
                include=["embeddings"]
            )

            total = len(all_docs.get("ids", []))
            valid = 0
            invalid = 0
            zero_vectors = 0

            embeddings = all_docs.get("embeddings", [])
            if embeddings:
                for embedding in embeddings:
                    if not embedding:
                        invalid += 1
                    elif all(v == 0.0 for v in embedding):
                        zero_vectors += 1
                        invalid += 1
                    else:
                        valid += 1
            else:
                logger.warning("Embeddings not returned, cannot validate")
                return {
                    "total": total,
                    "valid": 0,
                    "invalid": 0,
                    "zero_vectors": 0,
                    "valid_percentage": 0.0,
                    "error": "Embeddings not available for validation"
                }

            return {
                "total": total,
                "valid": valid,
                "invalid": invalid,
                "zero_vectors": zero_vectors,
                "valid_percentage": round((valid / total * 100) if total > 0 else 0, 2),
            }

        except Exception as e:
            logger.error(f"Error validating embeddings: {e}")
            return {
                "error": str(e),
            }

    def check_metadata_integrity(self, version: Optional[str] = None) -> Dict:
        """Check metadata integrity for all documents.

        Args:
            version: Optional version to check

        Returns:
            Dictionary with metadata integrity report
        """
        logger.info(f"Checking metadata integrity for version: {version or 'all'}")

        try:
            where = {"version": version} if version else None
            all_docs = self.vector_store.collection.get(
                where=where,
                include=["metadatas"]
            )

            required_fields = ["version", "file", "section", "anchor"]
            field_counts = {field: 0 for field in required_fields}
            missing_fields = {field: [] for field in required_fields}

            for i, metadata in enumerate(all_docs.get("metadatas", [])):
                for field in required_fields:
                    if field in metadata and metadata[field]:
                        field_counts[field] += 1
                    else:
                        missing_fields[field].append(all_docs["ids"][i])

            total = len(all_docs.get("ids", []))
            integrity_percentage = (
                sum(field_counts.values()) / (len(required_fields) * total) * 100
                if total > 0
                else 0
            )

            return {
                "total_documents": total,
                "integrity_percentage": round(integrity_percentage, 2),
                "field_counts": field_counts,
                "missing_fields": {k: len(v) for k, v in missing_fields.items()},
                "sample_missing": {k: v[:5] for k, v in missing_fields.items() if v},
            }

        except Exception as e:
            logger.error(f"Error checking metadata integrity: {e}")
            return {
                "error": str(e),
            }

