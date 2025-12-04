from typing import Optional
from core.db.mongodb import MongoDBClient
from core.db.elastic import ElasticClient

from core.logger import Logger
logger = Logger(__name__)

class BaseDatabase:
    mongodb: Optional[MongoDBClient] = None
    elastic: Optional[ElasticClient] = None

    @classmethod
    def init_databases(cls, mongodb: MongoDBClient, elastic: ElasticClient):
        logger.info("Initializing databases..")
        cls.mongodb = mongodb
        cls.elastic = elastic
