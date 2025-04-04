import os
import grpc
from concurrent import futures
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import order_service_pb2
import order_service_pb2_grpc
from dotenv import load_dotenv

load_dotenv()

class OrderService(order_service_pb2_grpc.OrderServiceServicer):
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("DATABASE_NAME")]
        self.orders = self.db["orders"]
        self.carts = self.db["carts"]
        self.products = self.db["products"]

    def CreateOrder(self, request, context):
        try:
            user_id = request.user_id
            cart = self.carts.find_one({"user_id": user_id})

            if not cart or not cart.get("items"):
                return order_service_pb2.CreateOrderResponse(message="Cart is empty", order_id="")

            items = cart["items"]
            total_price = 0
            order_items = []

            for item in items:
                product = self.products.find_one({"_id": ObjectId(item["product_id"])})
                if not product:
                    continue
                total_price += product["price"] * item["quantity"]
                order_items.append(order_service_pb2.OrderItem(
                    product_id=item["product_id"],
                    quantity=item["quantity"]
                ))

            order_doc = {
                "user_id": user_id,
                "items": items,
                "total_price": total_price,
                "status": "pending",
                "created_at": datetime.utcnow()
            }

            inserted = self.orders.insert_one(order_doc)
            self.carts.delete_one({"user_id": user_id})  # Clear cart after order

            return order_service_pb2.CreateOrderResponse(message="Order created", order_id=str(inserted.inserted_id))

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return order_service_pb2.CreateOrderResponse(message="Internal error", order_id="")

    def GetOrderById(self, request, context):
        try:
            order = self.orders.find_one({"_id": ObjectId(request.order_id)})
            if not order:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Order not found")
                return order_service_pb2.Order()

            return order_service_pb2.Order(
                order_id=str(order["_id"]),
                user_id=order["user_id"],
                total_price=order["total_price"],
                status=order["status"],
                created_at=str(order["created_at"]),
                items=[order_service_pb2.OrderItem(
                    product_id=i["product_id"], quantity=i["quantity"]) for i in order["items"]]
            )

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return order_service_pb2.Order()

    def GetOrdersByUserId(self, request, context):
        try:
            user_orders = self.orders.find({"user_id": request.user_id})
            order_list = []

            for order in user_orders:
                order_list.append(order_service_pb2.Order(
                    order_id=str(order["_id"]),
                    user_id=order["user_id"],
                    total_price=order["total_price"],
                    status=order["status"],
                    created_at=str(order["created_at"]),
                    items=[order_service_pb2.OrderItem(
                        product_id=i["product_id"], quantity=i["quantity"]) for i in order["items"]]
                ))

            return order_service_pb2.OrderList(orders=order_list)

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return order_service_pb2.OrderList(orders=[])

    def CancelOrder(self, request, context):
        try:
            result = self.orders.update_one(
                {"_id": ObjectId(request.order_id)},
                {"$set": {"status": "cancelled"}}
            )
            if result.modified_count == 1:
                return order_service_pb2.GenericResponse(message="Order cancelled")
            return order_service_pb2.GenericResponse(message="Order not found or already cancelled")
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return order_service_pb2.GenericResponse(message="Internal error")

    def UpdateOrderStatus(self, request, context):
        try:
            result = self.orders.update_one(
                {"_id": ObjectId(request.order_id)},
                {"$set": {"status": request.status}}
            )
            if result.modified_count == 1:
                return order_service_pb2.GenericResponse(message="Order status updated")
            return order_service_pb2.GenericResponse(message="Order not found")
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return order_service_pb2.GenericResponse(message="Internal error")

    def DeleteOrder(self, request, context):
        try:
            result = self.orders.delete_one({"_id": ObjectId(request.order_id)})
            if result.deleted_count == 1:
                return order_service_pb2.GenericResponse(message="Order deleted")
            return order_service_pb2.GenericResponse(message="Order not found")
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return order_service_pb2.GenericResponse(message="Internal error")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_service_pb2_grpc.add_OrderServiceServicer_to_server(OrderService(), server)
    server.add_insecure_port("[::]:50052")
    server.start()
    print("Order Service Server started on port 50052")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
