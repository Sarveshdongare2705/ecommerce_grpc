const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");
const readline = require("readline");

const packageDefinition = protoLoader.loadSync("cart_service.proto", {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const cartProto = grpc.loadPackageDefinition(packageDefinition).cart;

// Create gRPC client
const client = new cartProto.CartService("localhost:50053", grpc.credentials.createInsecure());

// CLI Interface for user input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => resolve(answer));
  });
}

async function main() {
  console.log("\n1. Add to Cart\n2. Remove from Cart\n3. Update Cart Item\n4. Get Cart Items\n5. Clear Cart\n6. Calculate Total Price\n7. Exit");
  
  const choice = await askQuestion("Enter your choice: ");

  switch (choice) {
    case "1":
      const userId = await askQuestion("Enter User ID: ");
      const productId = await askQuestion("Enter Product ID: ");
      const quantity = await askQuestion("Enter Quantity: ");

      client.AddToCart({ user_id: userId, product_id: productId, quantity: parseInt(quantity) }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log(response.message);
        main();
      });
      break;

    case "2":
      const removeUserId = await askQuestion("Enter User ID: ");
      const removeProductId = await askQuestion("Enter Product ID: ");

      client.RemoveFromCart({ user_id: removeUserId, product_id: removeProductId }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log(response.message);
        main();
      });
      break;

    case "3":
      const updateUserId = await askQuestion("Enter User ID: ");
      const updateProductId = await askQuestion("Enter Product ID: ");
      const updateQuantity = await askQuestion("Enter New Quantity: ");

      client.UpdateCartItem({ user_id: updateUserId, product_id: updateProductId, quantity: parseInt(updateQuantity) }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log(response.message);
        main();
      });
      break;

    case "4":
      const getUserId = await askQuestion("Enter User ID: ");

      client.GetCartItems({ user_id: getUserId }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else {
          console.log("\nCart Items:");
          console.table(response.items);
        }
        main();
      });
      break;

    case "5":
      const clearUserId = await askQuestion("Enter User ID: ");

      client.ClearCart({ user_id: clearUserId }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log(response.message);
        main();
      });
      break;

    case "6":
      const totalUserId = await askQuestion("Enter User ID: ");

      client.CalculateTotalPrice({ user_id: totalUserId }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log(`Total Price: ₹${response.total_price}`);
        main();
      });
      break;

    case "7":
      console.log("Exiting...");
      rl.close();
      break;

    default:
      console.log("Invalid choice, try again.");
      main();
  }
}

main();
