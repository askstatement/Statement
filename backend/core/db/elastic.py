import os
from elasticsearch import Elasticsearch

from core.logger import Logger
logger = Logger(__name__)

class ElasticClient:
    def __init__(self):
        self.client = Elasticsearch(
            [os.getenv("ELASTICSEARCH_HOSTS", "http://elasticsearch:9200")],
            basic_auth=(
                os.getenv("ELASTIC_USERNAME", ""),
                os.getenv("ELASTIC_PASSWORD", "")
            )
        )
        # ping the elasticsearch to ensure connection is established
        if self.client.ping():
            logger.info("Elasticsearch connection established successfully.")
        else:
            logger.error("Elasticsearch connection failed.")
            
    def verify_index(method):
        def wrapper(self, index: str, *args, **kwargs):
            if not self.client.indices.exists(index=index):
                logger.error(f"Index '{index}' does not exist.")
                raise ValueError(f"Index '{index}' does not exist.")
            return method(self, index, *args, **kwargs)
        return wrapper

    def create_index(self, index: str, body: dict):
        if not self.client.indices.exists(index=index):
            self.client.indices.create(index=index, body=body)
            logger.info(f"Created index: {index}")
        else:
            logger.info(f"Index already exists: {index}")
            
    def list_indices(self, pattern: str = "*"):
        indices = self.client.cat.indices(index=pattern, format="json")
        index_names = [idx["index"] for idx in indices]
        logger.info(f"Listed indices with pattern '{pattern}': {index_names}")
        return index_names
            
    @verify_index
    def index_document(self, index: str, document: dict, id: str = None):
        response = self.client.index(index=index, document=document, id=id)
        logger.info(f"Indexed document in {index} with id {response['_id']}")
        return response
    
    @verify_index
    def search(self, index: str, body: dict, scroll: str = None, size: int = None):
        if scroll and size:
            response = self.client.search(index=index, body=body, scroll=scroll, size=size)
        else:
            response = self.client.search(index=index, body=body)
        logger.info(f"Searched index {index} with body {body}")
        return response
    
    @verify_index
    def scroll(self, index: str, scroll_id: str, scroll: str):
        response = self.client.scroll(scroll_id=scroll_id, scroll=scroll)
        logger.info(f"Scrolled with scroll_id {scroll_id}")
        return response
    
    @verify_index
    def clear_scroll(self, scroll_id: str):
        response = self.client.clear_scroll(scroll_id=scroll_id)
        logger.info(f"Cleared scroll with scroll_id {scroll_id}")
        return response
        
    @verify_index
    def delete_document(self, index: str, id: str):
        response = self.client.delete(index=index, id=id)
        logger.info(f"Deleted document from {index} with id {id}")
        return response
    
    @verify_index
    def delete_by_query(self, index: str, body: dict):
        response = self.client.delete_by_query(index=index, body=body)
        logger.info(f"Deleted documents from {index} with query {body}")
        return response
    
