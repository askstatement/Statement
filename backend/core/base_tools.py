from typing import Any, Dict, Optional, List
from core.db.mongodb import MongoDBClient
from core.db.elastic import ElasticClient
from core.logger import Logger

logger = Logger(__name__)


class BaseTool:
    """Base tool for services to interact with databases"""
    def __init__(self):
        self.mongodb_client = MongoDBClient()
        self.elastic_client = ElasticClient()
        
    def _query_elasticsearch(
        self,
        index: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        query: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, Any]]] = None,
        source: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generic function to query Elasticsearch with filters or custom query

        Args:
            index: Elasticsearch index name
            filters: List of filter conditions (used if query is not provided)
            query: Full Elasticsearch query body (takes precedence over filters)
            sort: Sorting criteria
            source: Fields to include in response

        Returns:
            List of documents matching the query

        Raises:
            Exception: If query fails
            ValueError: If invalid parameters provided
        """
        # Input validation
        if not index:
            raise ValueError("Index name is required")

        if not filters and not query:
            raise ValueError("Either filters or query must be provided")

        # Build query body
        if query:
            # Use the provided full query
            query_body = {"query": query}
        elif filters:
            # Build query from filters
            if not isinstance(filters, list):
                raise ValueError("Query Filters must be a list")
            query_body = {"query": {"bool": {"filter": filters}}}
        else:
            raise ValueError("Either filters or query must be provided")

        # Add optional parameters
        if sort:
            query_body["sort"] = sort

        if source is not None:  # Allow explicit empty list
            query_body["_source"] = source
        scroll_id = None
        try:
            # Initial search with scroll
            scroll_size = 10000
            scroll_timeout = "2m"
            result = self.elastic_client.search(
                index=index, body=query_body, scroll=scroll_timeout, size=scroll_size
            )
            scroll_id = result.get("_scroll_id")
            documents = result.get("hits", {}).get("hits", [])

            # Keep scrolling until no more results
            hard_scroll_limit = 10000  # prevent infinite loops
            scroll_iterations = 0
            while True:
                scroll_iterations += 1
                if scroll_iterations > hard_scroll_limit:
                    break
                if not documents or not scroll_id:
                    break

                next_scroll = self.elastic_client.scroll(index=index, scroll_id=scroll_id, scroll=scroll_timeout)
                hits = next_scroll.get("hits", {}).get("hits", [])
                if not hits:
                    break
                documents.extend(hits)
                scroll_id = next_scroll.get("_scroll_id")

            if not isinstance(documents, list):
                logger.warning("Unexpected format for Elasticsearch hits")
                documents = []

            return documents

        except Exception as e:
            logger.error(f"Elasticsearch query failed for index {index}: {str(e)}")
            return []
        finally:
            # Clear scroll to free resources
            if scroll_id:
                try:
                    self.elastic_client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    pass  # Ignore errors when clearing scroll
        
    
        
    
