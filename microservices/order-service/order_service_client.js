const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");
const readline = require("readline");

const packageDefinition = protoLoader.loadSync("order_service.proto", {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const orderProto = grpc.loadPackageDefinition(packageDefinition).order_service;
const client = new orderProto.OrderService("localhost:50052", grpc.credentials.createInsecure());

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function askQuestion(question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

async function main() {
  console.log(`\n1. Create Order\n2. Get Order by ID\n3. Get Orders by User\n4. Cancel Order\n5. Update Status\n6. Delete Order\n7. Exit`);
  const choice = await askQuestion("Enter your choice: ");

  switch (choice) {
    case "1":
      const userId = await askQuestion("Enter User ID: ");
      client.CreateOrder({ user_id: userId }, (err, res) => {
        if (err) console.error("Error:", err.message);
        else console.log(res.message, "Order ID:", res.order_id);
        main();
      });
      break;

    case "2":
      const orderId = await askQuestion("Enter Order ID: ");
      client.GetOrderById({ order_id: orderId }, (err, order) => {
        if (err) console.error("Error:", err.message);
        else console.log("Order:", order);
        main();
      });
      break;

    case "3":
      const user = await askQuestion("Enter User ID: ");
      client.GetOrdersByUserId({ user_id: user }, (err, res) => {
        if (err) console.error("Error:", err.message);
        else console.log("Orders:", res.orders);
        main();
      });
      break;

    case "4":
      const cancelId = await askQuestion("Enter Order ID: ");
      client.CancelOrder({ order_id: cancelId }, (err, res) => {
        if (err) console.error("Error:", err.message);
        else console.log(res.message);
        main();
      });
      break;

    case "5":
      const updateId = await askQuestion("Enter Order ID: ");
      const newStatus = await askQuestion("Enter New Status: ");
      client.UpdateOrderStatus({ order_id: updateId, status: newStatus }, (err, res) => {
        if (err) console.error("Error:", err.message);
        else console.log(res.message);
        main();
      });
      break;

    case "6":
      const delId = await askQuestion("Enter Order ID: ");
      client.DeleteOrder({ order_id: delId }, (err, res) => {
        if (err) console.error("Error:", err.message);
        else console.log(res.message);
        main();
      });
      break;

    case "7":
      rl.close();
      break;

    default:
      console.log("Invalid choice");
      main();
  }
}

main();
