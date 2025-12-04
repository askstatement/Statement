import os
from urllib.parse import quote_plus
from motor.motor_asyncio import AsyncIOMotorClient

from core.logger import Logger
logger = Logger(__name__)

MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_HOST = os.getenv("MONGO_HOST", "")
MONGO_PORT = os.getenv("MONGO_PORT", "")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "")

class MongoDBClient:
    def __init__(self):
        MONGO_URI = f"mongodb://{quote_plus(MONGO_USER)}:{quote_plus(MONGO_PASSWORD)}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}?authSource={MONGO_DB_NAME}"
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        logger.info("MongoDB client initialized (async).")
        
    async def init(self):
        """Initialize async connection and verify database access."""
        try:
            await self.client.admin.command('ping')
            logger.info("MongoDB connection established successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        
    def verify_collection(method):
        async def wrapper(self, collection_name: str, *args, **kwargs):
            collections = await self.db.list_collection_names()
            if collection_name not in collections:
                logger.error(f"Collection '{collection_name}' does not exist in database '{MONGO_DB_NAME}'.")
                raise ValueError(f"Collection '{collection_name}' does not exist.")
            return await method(self, collection_name, *args, **kwargs)
        return wrapper

    def get_collection(self, name: str):
        return self.db[name]
    
    async def list_collections(self):
        return await self.db.list_collection_names()
    
    @verify_collection
    async def delete_document(self, collection_name: str, query: dict):
        collection = self.get_collection(collection_name)
        result = await collection.delete_one(query)
        logger.info(f"Deleted {result.deleted_count} document(s) from collection {collection_name} matching query {query}")
        return result.deleted_count
    
    async def update_one(self, collection_name: str, query: dict, update_values: dict, upsert: bool = False):
        collection = self.get_collection(collection_name)
        result = await collection.update_one(query, {'$set': update_values}, upsert=upsert)
        logger.info(f"Updated {result.modified_count} document(s) in collection {collection_name} matching query {query} with upsert={upsert}")
        return result.modified_count
    
    @verify_collection
    async def find_one(self, collection_name: str, query: dict):
        """Find a single document."""
        collection = self.get_collection(collection_name)
        return await collection.find_one(query)
    
    async def insert_one(self, collection_name: str, document: dict, upsert: bool = False):
        """Insert or update a single document."""
        collection = self.get_collection(collection_name)
        if upsert and "_id" in document:
            result = await collection.update_one(
                {"_id": document["_id"]},
                {"$set": document},
                upsert=True
            )
            return document["_id"]
        else:
            result = await collection.insert_one(document)
            return result.inserted_id
