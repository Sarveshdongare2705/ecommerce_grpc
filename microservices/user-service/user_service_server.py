import grpc
import user_service_pb2
import user_service_pb2_grpc
from concurrent import futures
import bcrypt
import pymongo
import redis
import uuid
from bson.objectid import ObjectId
from config import MONGO_URI, DATABASE_NAME, REDIS_HOST, REDIS_PORT

# MongoDB setup
client = pymongo.MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
users_collection = db["users"]

# Redis setup
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

class UserService(user_service_pb2_grpc.UserServiceServicer):

    def RegisterUser(self, request, context):
        if users_collection.find_one({"email": request.email}):
            return user_service_pb2.UserResponse(message="User already exists", user_id="")
        
        hashed_password = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt())
        user_data = {
            "full_name": request.full_name,
            "email": request.email,
            "password": hashed_password.decode(),
            "address": request.address,
            "phone_number": request.phone_number
        }

        inserted = users_collection.insert_one(user_data)
        return user_service_pb2.UserResponse(message="User registered successfully", user_id=str(inserted.inserted_id))

    def LoginUser(self, request, context):
        user = users_collection.find_one({"email": request.email})
        if not user or not bcrypt.checkpw(request.password.encode(), user["password"].encode()):
            return user_service_pb2.LoginResponse(message="Invalid email or password", session_token="")
        
        session_token = str(uuid.uuid4())
        redis_client.set(session_token, str(user["_id"]), ex=3600)  # expires in 1 hour
        return user_service_pb2.LoginResponse(message="Login successful", session_token=session_token)

    def GetUserProfile(self, request, context):
        user_id = redis_client.get(request.session_token)
        if not user_id:
            return user_service_pb2.UserProfileResponse()

        user = users_collection.find_one({"_id": ObjectId(user_id)}, {"_id": 0, "password": 0})
        if not user:
            return user_service_pb2.UserProfileResponse()

        return user_service_pb2.UserProfileResponse(**user)

    def UpdateUserProfile(self, request, context):
        user_id = redis_client.get(request.session_token)
        if not user_id:
            return user_service_pb2.UserResponse(message="Invalid session", user_id="")

        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "full_name": request.full_name,
                "address": request.address,
                "phone_number": request.phone_number
            }}
        )
        return user_service_pb2.UserResponse(message="Profile updated", user_id=user_id)

    def LogoutUser(self, request, context):
        if redis_client.delete(request.session_token):
            return user_service_pb2.UserResponse(message="Logout successful", user_id="")
        return user_service_pb2.UserResponse(message="Invalid session", user_id="")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_service_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("User Service running on port 50051...")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
