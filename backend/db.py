import pymongo
import os
from dotenv import load_dotenv

load_dotenv()  # Load Cosmos DB connection string from .env

MONGO_URI = os.getenv("COSMOSDB_URI")
DB_NAME = os.getenv("COSMOSDB_NAME", "townsense")

client = pymongo.MongoClient(
    MONGO_URI,
    retryWrites=False,
    tls=True,
    tlsAllowInvalidCertificates=True,
    directConnection=True
)

db = client[DB_NAME]

# Collections
users_collection = db["users"]
reports_collection = db["reports"]
