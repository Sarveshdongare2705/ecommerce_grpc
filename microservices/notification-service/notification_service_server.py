import grpc
from concurrent import futures
import time
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId, InvalidId
from pymongo import MongoClient
from twilio.rest import Client as TwilioClient

import notification_service_pb2
import notification_service_pb2_grpc

load_dotenv()

# Load env variables
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DATABASE_NAME")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
users_collection = db["users"]

# Twilio
twilio_client = TwilioClient(TWILIO_SID, TWILIO_AUTH_TOKEN)

class NotificationService(notification_service_pb2_grpc.NotificationServiceServicer):
    def SendNotification(self, request, context):
        print(f"Received user_id: '{request.user_id}'")
        user_id_str = request.user_id.strip()
        message = request.message.strip()

        if not user_id_str:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("User ID is empty")
            return notification_service_pb2.NotificationResponse(status="Failed")

        try:
            user_id = ObjectId(user_id_str)
        except InvalidId:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Invalid user ID format")
            return notification_service_pb2.NotificationResponse(status="Failed")

        user = users_collection.find_one({"_id": user_id})
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("User not found")
            return notification_service_pb2.NotificationResponse(status="User not found")

        phone_number = user.get("phone_number")
        if not phone_number:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("Phone number not found")
            return notification_service_pb2.NotificationResponse(status="Phone number not found")

        try:
            twilio_client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            return notification_service_pb2.NotificationResponse(status="Notification sent successfully")
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return notification_service_pb2.NotificationResponse(status="Failed to send SMS")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    notification_service_pb2_grpc.add_NotificationServiceServicer_to_server(NotificationService(), server)
    server.add_insecure_port("[::]:50055")
    print("Notification Service running on port 50055...")
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("Shutting down NotificationService")
        server.stop(0)

if __name__ == "__main__":
    serve()
