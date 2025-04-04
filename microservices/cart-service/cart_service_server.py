import os
import grpc
from concurrent import futures
from pymongo import MongoClient
from bson import ObjectId
import cart_service_pb2
import cart_service_pb2_grpc
from dotenv import load_dotenv

load_dotenv()

class CartService(cart_service_pb2_grpc.CartServiceServicer):
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("DATABASE_NAME")]
        self.carts = self.db["carts"]
        self.products = self.db["products"]

    def AddToCart(self, request, context):
        try:
            user_id = request.user_id
            product_id = request.product_id
            quantity = request.quantity

            product = self.products.find_one({"_id": ObjectId(product_id)})
            if not product:
                return cart_service_pb2.CartResponse(success=False, message="Product not found")

            if product["stock"] < quantity:
                return cart_service_pb2.CartResponse(success=False, message="Not enough stock available")

            self.products.update_one({"_id": ObjectId(product_id)}, {"$inc": {"stock": -quantity}})

            self.carts.update_one(
                {"user_id": user_id},
                {"$push": {"items": {"product_id": product_id, "quantity": quantity}}},
                upsert=True
            )

            return cart_service_pb2.CartResponse(success=True, message="Product added to cart")

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return cart_service_pb2.CartResponse(success=False, message=str(e))

    def RemoveFromCart(self, request, context):
        try:
            user_id = request.user_id
            product_id = request.product_id

            cart = self.carts.find_one({"user_id": user_id})
            if not cart:
                return cart_service_pb2.CartResponse(success=False, message="Cart not found")

            item = next((item for item in cart["items"] if item["product_id"] == product_id), None)
            if not item:
                return cart_service_pb2.CartResponse(success=False, message="Product not in cart")

            self.products.update_one({"_id": ObjectId(product_id)}, {"$inc": {"stock": item["quantity"]}})
            self.carts.update_one({"user_id": user_id}, {"$pull": {"items": {"product_id": product_id}}})

            return cart_service_pb2.CartResponse(success=True, message="Product removed from cart")

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return cart_service_pb2.CartResponse(success=False, message=str(e))

    def UpdateCartItem(self, request, context):
        try:
            user_id = request.user_id
            product_id = request.product_id
            new_quantity = request.quantity

            cart = self.carts.find_one({"user_id": user_id})
            if not cart:
                return cart_service_pb2.CartResponse(success=False, message="Cart not found")

            item = next((item for item in cart["items"] if item["product_id"] == product_id), None)
            if not item:
                return cart_service_pb2.CartResponse(success=False, message="Product not in cart")

            product = self.products.find_one({"_id": ObjectId(product_id)})
            stock_change = new_quantity - item["quantity"]

            if product["stock"] < stock_change:
                return cart_service_pb2.CartResponse(success=False, message="Not enough stock available")

            self.products.update_one({"_id": ObjectId(product_id)}, {"$inc": {"stock": -stock_change}})
            self.carts.update_one(
                {"user_id": user_id, "items.product_id": product_id},
                {"$set": {"items.$.quantity": new_quantity}}
            )

            return cart_service_pb2.CartResponse(success=True, message="Cart updated successfully")

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return cart_service_pb2.CartResponse(success=False, message=str(e))

    def GetCartItems(self, request, context):
        cart = self.carts.find_one({"user_id": request.user_id})
        if not cart:
            return cart_service_pb2.GetCartItemsResponse(items=[])

        return cart_service_pb2.GetCartItemsResponse(
            items=[cart_service_pb2.CartItem(product_id=item["product_id"], quantity=item["quantity"]) for item in cart["items"]]
        )

    def ClearCart(self, request, context):
        try:
            user_id = request.user_id
            cart = self.carts.find_one({"user_id": user_id})

            if not cart:
                return cart_service_pb2.CartResponse(success=False, message="Cart not found")

            for item in cart["items"]:
                self.products.update_one({"_id": ObjectId(item["product_id"])}, {"$inc": {"stock": item["quantity"]}})

            self.carts.delete_one({"user_id": user_id})

            return cart_service_pb2.CartResponse(success=True, message="Cart cleared successfully")

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return cart_service_pb2.CartResponse(success=False, message=str(e))

    def CalculateTotalPrice(self, request, context):
        cart = self.carts.find_one({"user_id": request.user_id})
        if not cart:
            return cart_service_pb2.TotalPriceResponse(total_price=0)

        total_price = 0
        for item in cart["items"]:
            product = self.products.find_one({"_id": ObjectId(item["product_id"])})
            if product:
                total_price += product["price"] * item["quantity"]

        return cart_service_pb2.TotalPriceResponse(total_price=total_price)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cart_service_pb2_grpc.add_CartServiceServicer_to_server(CartService(), server)
    server.add_insecure_port("[::]:50053")
    server.start()
    print("Cart Service Server started on port 50053")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
