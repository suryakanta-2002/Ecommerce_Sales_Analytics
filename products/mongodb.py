from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["ecommerce_analytics"]

user_activity = db["user_activity"]