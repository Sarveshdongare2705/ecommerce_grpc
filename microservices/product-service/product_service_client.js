const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");
const readline = require("readline");

const packageDefinition = protoLoader.loadSync("product_service.proto", {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const productProto = grpc.loadPackageDefinition(packageDefinition).product;

const client = new productProto.ProductService("localhost:50052", grpc.credentials.createInsecure());

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

function listProducts() {
    const call = client.ListProducts({});
  
    call.on("data", (response) => {
      console.log("\nProduct:", JSON.stringify(response.product, null, 2));
    });
  
    call.on("end", () => {
      console.log("Product listing completed.");
      main();
    });
  
    call.on("error", (error) => {
      console.error("Error:", error.message);
      main();
    });
  }
  

async function main() {
  console.log("\n1. Create Product");
  console.log("2. Get Product");
  console.log("3. List Products");
  console.log("4. Update Product");
  console.log("5. Delete Product");
  console.log("6. Exit");
  
  const choice = await askQuestion("\nEnter your choice: ");

  switch (choice) {
    case "1":
      const name = await askQuestion("Enter product name: ");
      const description = await askQuestion("Enter product description: ");
      const price = parseFloat(await askQuestion("Enter price: "));
      const category = await askQuestion("Enter category: ");
      const brand = await askQuestion("Enter brand: ");
      const stock = parseInt(await askQuestion("Enter stock quantity: "));
      const attributesStr = await askQuestion("Enter attributes (key:value,key:value): ");
      const attributes = {};
      if (attributesStr) {
        attributesStr.split(",").forEach(pair => {
          const [key, value] = pair.split(":").map(s => s.trim());
          attributes[key] = value;
        });
      }
      
      client.CreateProduct({ name, description, price, category, brand, stock, attributes }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log("\nResponse:", response);
        main();
      });
      break;

    case "2":
      const productId = await askQuestion("Enter product ID: ");
      client.GetProduct({ product_id: productId }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log("\nProduct Details:", JSON.stringify(response.product, null, 2));
        main();
      });
      break;

    case "3":
      listProducts();
      break;

    case "4":
      const updateId = await askQuestion("Enter product ID to update: ");
      const updateData = { product_id: updateId };
      updateData.name = await askQuestion("Enter new name (or press enter to skip): ") || undefined;
      updateData.description = await askQuestion("Enter new description (or press enter to skip): ") || undefined;
      updateData.price = parseFloat(await askQuestion("Enter new price (or press enter to skip): ")) || undefined;
      updateData.category = await askQuestion("Enter new category (or press enter to skip): ") || undefined;
      updateData.brand = await askQuestion("Enter new brand (or press enter to skip): ") || undefined;
      updateData.stock = parseInt(await askQuestion("Enter new stock quantity (or press enter to skip): ")) || undefined;
      
      client.UpdateProduct(updateData, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log("\nResponse:", response);
        main();
      });
      break;

    case "5":
      const deleteId = await askQuestion("Enter product ID to delete: ");
      client.DeleteProduct({ product_id: deleteId }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log("\nResponse:", response);
        main();
      });
      break;

    case "6":
      console.log("Exiting...");
      rl.close();
      break;

    default:
      console.log("Invalid choice, try again.");
      main();
  }
}
main();
