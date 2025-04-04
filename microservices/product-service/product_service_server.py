import os
import grpc
from concurrent import futures
import time
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import product_service_pb2
import product_service_pb2_grpc
from dotenv import load_dotenv

load_dotenv()

class ProductService(product_service_pb2_grpc.ProductServiceServicer):
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("DATABASE_NAME")]
        self.products = self.db.products

    def CreateProduct(self, request, context):
        try:
            product_data = {
                "name": request.name,
                "description": request.description,
                "price": request.price,
                "category": request.category,
                "brand": request.brand,
                "stock": request.stock,
                "attributes": dict(request.attributes),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            result = self.products.insert_one(product_data)
            product_data["id"] = str(result.inserted_id)

            return product_service_pb2.ProductResponse(
                success=True,
                message="Product created successfully",
                product=self._convert_to_proto_product(product_data),
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return product_service_pb2.ProductResponse(success=False, message=str(e))

    def GetProduct(self, request, context):
        try:
            product = self.products.find_one({"_id": ObjectId(request.product_id)})
            if not product:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Product not found")
                return product_service_pb2.ProductResponse(success=False, message="Product not found")

            product["id"] = str(product["_id"])
            return product_service_pb2.ProductResponse(
                success=True,
                message="Product retrieved successfully",
                product=self._convert_to_proto_product(product),
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return product_service_pb2.ProductResponse(success=False, message=str(e))

    def ListProducts(self, request, context):
        try:
            query = {}

            if request.category:
                query["category"] = request.category
            if request.brand:
                query["brand"] = request.brand

            price_filter = {}
            if request.min_price > 0:
                price_filter["$gte"] = request.min_price
            if request.max_price > 0:
                price_filter["$lte"] = request.max_price
            if price_filter:
                query["price"] = price_filter

            page = request.page if request.page > 0 else 1
            limit = request.limit if request.limit > 0 else 10
            skip = (page - 1) * limit

            cursor = self.products.find(query).skip(skip).limit(limit)

            for product in cursor:
                product["id"] = str(product["_id"])
                yield product_service_pb2.ProductResponse(
                    success=True,
                    message="Product retrieved successfully",
                    product=self._convert_to_proto_product(product),
                )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            yield product_service_pb2.ProductResponse(success=False, message=str(e))

    def UpdateProduct(self, request, context):
        try:
            update_data = {}
            if request.name:
                update_data["name"] = request.name
            if request.description:
                update_data["description"] = request.description
            if request.price > 0:
                update_data["price"] = request.price
            if request.category:
                update_data["category"] = request.category
            if request.brand:
                update_data["brand"] = request.brand
            if request.stock >= 0:
                update_data["stock"] = request.stock
            if request.attributes:
                update_data["attributes"] = request.attributes

            update_data["updated_at"] = datetime.utcnow().isoformat()

            result = self.products.update_one(
                {"_id": ObjectId(request.product_id)}, {"$set": update_data}
            )

            if result.modified_count == 0:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Product not found")
                return product_service_pb2.ProductResponse(success=False, message="Product not found")

            updated_product = self.products.find_one({"_id": ObjectId(request.product_id)})
            updated_product["id"] = str(updated_product["_id"])

            return product_service_pb2.ProductResponse(
                success=True,
                message="Product updated successfully",
                product=self._convert_to_proto_product(updated_product),
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return product_service_pb2.ProductResponse(success=False, message=str(e))

    def DeleteProduct(self, request, context):
        try:
            result = self.products.delete_one({"_id": ObjectId(request.product_id)})
            if result.deleted_count == 0:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Product not found")
                return product_service_pb2.DeleteProductResponse(success=False, message="Product not found")

            return product_service_pb2.DeleteProductResponse(
                success=True, message="Product deleted successfully"
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return product_service_pb2.DeleteProductResponse(success=False, message=str(e))

    def _convert_to_proto_product(self, product):
        return product_service_pb2.Product(
            id=product["id"],
            name=product["name"],
            description=product["description"],
            price=product["price"],
            category=product["category"],
            brand=product["brand"],
            stock=product["stock"],
            attributes=product["attributes"],
            created_at=product["created_at"],
            updated_at=product["updated_at"],
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    product_service_pb2_grpc.add_ProductServiceServicer_to_server(ProductService(), server)
    server.add_insecure_port("[::]:50052")
    server.start()
    print("Product Service Server started on port 50052")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()
