import pymongo
import os
from dotenv import load_dotenv
from pymongo import IndexModel

# Load Cosmos DB connection string from .env
load_dotenv()

# Connection and DB name
MONGO_URI = os.getenv("COSMOSDB_URI")
DB_NAME = os.getenv("COSMOSDB_NAME", "townsense")

# MongoDB client setup (CosmosDB-friendly)
client = pymongo.MongoClient(
    MONGO_URI,
    retryWrites=False,
    tls=True,
    tlsAllowInvalidCertificates=True,
    directConnection=True
)

# Connect to DB
db = client[DB_NAME]

# Collections
users_collection = db["users"]
reports_collection = db["reports"]
feedback_collection = db["feedback"]  # New collection for storing feedback

reports_collection.create_index("username")
reports_collection.create_index("timestamp")


print("✅ MongoDB connected to database:", DB_NAME)

