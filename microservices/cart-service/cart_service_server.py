import os
import grpc
import json
from concurrent import futures
from pymongo import MongoClient
from bson import ObjectId
import cart_service_pb2
import cart_service_pb2_grpc
from dotenv import load_dotenv
import redis

load_dotenv()

class CartService(cart_service_pb2_grpc.CartServiceServicer):
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("DATABASE_NAME")]
        self.carts = self.db["carts"]
        self.products = self.db["products"]
        
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True
        )
        self.cache_ttl = int(os.getenv("REDIS_CACHE_TTL", 3600))

    def _get_product(self, product_id):
        """Get product from cache or database"""
        cache_key = f"product:{product_id}"
        cached_product = self.redis_client.get(cache_key)
        
        if cached_product:
            return json.loads(cached_product)
        
        product = self.products.find_one({"_id": ObjectId(product_id)})
        if product:
            product['_id'] = str(product['_id'])
            self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(product))
        
        return product

    def _get_cart(self, user_id):
        """Get cart from cache or database"""
        cache_key = f"cart:{user_id}"
        cached_cart = self.redis_client.get(cache_key)
        
        if cached_cart:
            return json.loads(cached_cart)
        
        cart = self.carts.find_one({"user_id": user_id})
        if cart:
            cart['_id'] = str(cart['_id'])
            self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(cart))
        
        return cart

    def _invalidate_cart_cache(self, user_id):
        """Invalidate cart cache for a user"""
        self.redis_client.delete(f"cart:{user_id}")

    def _invalidate_product_cache(self, product_id):
        """Invalidate product cache"""
        self.redis_client.delete(f"product:{product_id}")

    def AddToCart(self, request, context):
        try:
            user_id = request.user_id
            product_id = request.product_id
            quantity = request.quantity

            product = self._get_product(product_id)
            if not product:
                return cart_service_pb2.CartResponse(success=False, message="Product not found")

            if product["stock"] < quantity:
                return cart_service_pb2.CartResponse(success=False, message="Not enough stock available")

            self.products.update_one({"_id": ObjectId(product_id)}, {"$inc": {"stock": -quantity}})
            
            self._invalidate_product_cache(product_id)

            self.carts.update_one(
                {"user_id": user_id},
                {"$push": {"items": {"product_id": product_id, "quantity": quantity}}},
                upsert=True
            )
            
            self._invalidate_cart_cache(user_id)

            return cart_service_pb2.CartResponse(success=True, message="Product added to cart")

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return cart_service_pb2.CartResponse(success=False, message=str(e))

    def RemoveFromCart(self, request, context):
        try:
            user_id = request.user_id
            product_id = request.product_id

            cart = self._get_cart(user_id)
            if not cart:
                return cart_service_pb2.CartResponse(success=False, message="Cart not found")

            item = next((item for item in cart["items"] if item["product_id"] == product_id), None)
            if not item:
                return cart_service_pb2.CartResponse(success=False, message="Product not in cart")

            self.products.update_one({"_id": ObjectId(product_id)}, {"$inc": {"stock": item["quantity"]}})
            
            self.carts.update_one({"user_id": user_id}, {"$pull": {"items": {"product_id": product_id}}})
            
            self._invalidate_product_cache(product_id)
            self._invalidate_cart_cache(user_id)

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

            cart = self._get_cart(user_id)
            if not cart:
                return cart_service_pb2.CartResponse(success=False, message="Cart not found")

            item = next((item for item in cart["items"] if item["product_id"] == product_id), None)
            if not item:
                return cart_service_pb2.CartResponse(success=False, message="Product not in cart")

            product = self._get_product(product_id)
            stock_change = new_quantity - item["quantity"]

            if product["stock"] < stock_change:
                return cart_service_pb2.CartResponse(success=False, message="Not enough stock available")

            self.products.update_one({"_id": ObjectId(product_id)}, {"$inc": {"stock": -stock_change}})

            self.carts.update_one(
                {"user_id": user_id, "items.product_id": product_id},
                {"$set": {"items.$.quantity": new_quantity}}
            )
            
            self._invalidate_product_cache(product_id)
            self._invalidate_cart_cache(user_id)

            return cart_service_pb2.CartResponse(success=True, message="Cart updated successfully")

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return cart_service_pb2.CartResponse(success=False, message=str(e))

    def GetCartItems(self, request, context):
        cart = self._get_cart(request.user_id)
        if not cart:
            return cart_service_pb2.GetCartItemsResponse(items=[])

        return cart_service_pb2.GetCartItemsResponse(
            items=[cart_service_pb2.CartItem(product_id=item["product_id"], quantity=item["quantity"]) for item in cart["items"]]
        )

    def ClearCart(self, request, context):
        try:
            user_id = request.user_id
            
            cart = self._get_cart(user_id)
            if not cart:
                return cart_service_pb2.CartResponse(success=False, message="Cart not found")

            for item in cart["items"]:
                self.products.update_one({"_id": ObjectId(item["product_id"])}, {"$inc": {"stock": item["quantity"]}})
                self._invalidate_product_cache(item["product_id"])

            self.carts.delete_one({"user_id": user_id})
            
            self._invalidate_cart_cache(user_id)

            return cart_service_pb2.CartResponse(success=True, message="Cart cleared successfully")

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return cart_service_pb2.CartResponse(success=False, message=str(e))

    def CalculateTotalPrice(self, request, context):
        cache_key = f"cart:total:{request.user_id}"
        cached_total = self.redis_client.get(cache_key)
        
        if cached_total:
            return cart_service_pb2.TotalPriceResponse(total_price=float(cached_total))
        
        cart = self._get_cart(request.user_id)
        if not cart:
            return cart_service_pb2.TotalPriceResponse(total_price=0)

        total_price = 0
        for item in cart["items"]:
            product = self._get_product(item["product_id"])
            if product:
                total_price += product["price"] * item["quantity"]
        
        self.redis_client.setex(cache_key, self.cache_ttl, str(total_price))

        return cart_service_pb2.TotalPriceResponse(total_price=total_price)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cart_service_pb2_grpc.add_CartServiceServicer_to_server(CartService(), server)
    server.add_insecure_port("[::]:50053")
    server.start()
    print("Cart Service Server with Redis Cache started on port 50053")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()