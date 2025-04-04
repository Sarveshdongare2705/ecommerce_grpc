import grpc
import user_service_pb2
import user_service_pb2_grpc
from concurrent import futures
import bcrypt
import pymongo
from config import MONGO_URI, DATABASE_NAME
from bson.objectid import ObjectId

# Connect to MongoDB
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    users_collection = db["users"]
    client.server_info()  # Check connection
    print("Connected to MongoDB")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

class UserService(user_service_pb2_grpc.UserServiceServicer):
    
    def RegisterUser(self, request, context):
        existing_user = users_collection.find_one({"email": request.email})
        if existing_user:
            return user_service_pb2.UserResponse(message="User already exists", user_id="")

        hashed_password = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt())

        user_data = {
            "full_name": request.full_name,
            "email": request.email,
            "password": hashed_password.decode('utf-8'),
            "address": request.address,
            "phone_number": request.phone_number
        }
        
        insert_result = users_collection.insert_one(user_data)
        return user_service_pb2.UserResponse(message="User registered successfully", user_id=str(insert_result.inserted_id))

    def LoginUser(self, request, context):
        user = users_collection.find_one({"email": request.email})
        if not user or not bcrypt.checkpw(request.password.encode('utf-8'), user["password"].encode('utf-8')):
            return user_service_pb2.UserResponse(message="Invalid email or password", user_id="")

        return user_service_pb2.UserResponse(message="Login successful", user_id=str(user["_id"]))

    def GetUserProfile(self, request, context):
        user = users_collection.find_one({"_id": ObjectId(request.user_id)}, {"_id": 0, "password": 0})
        if not user:
            return user_service_pb2.UserProfileResponse(full_name="", email="", address="", phone_number="")

        return user_service_pb2.UserProfileResponse(
            full_name=user["full_name"],
            email=user["email"],
            address=user["address"],
            phone_number=user["phone_number"]
        )

    def UpdateUserProfile(self, request, context):
        user = users_collection.find_one({"email": request.email})
        if not user:
            return user_service_pb2.UserResponse(message="User not found", user_id="")

        users_collection.update_one(
            {"email": request.email},
            {"$set": {
                "full_name": request.full_name,
                "address": request.address,
                "phone_number": request.phone_number
            }}
        )
        return user_service_pb2.UserResponse(message="Profile updated successfully", user_id=str(user["_id"]))

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_service_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("User Service running on port 50051...")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
