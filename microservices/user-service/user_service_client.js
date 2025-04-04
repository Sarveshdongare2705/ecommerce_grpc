const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");
const readline = require("readline");

// Load the proto file
const packageDefinition = protoLoader.loadSync("user_service.proto", {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const userProto = grpc.loadPackageDefinition(packageDefinition).user_service;

// Create gRPC client
const client = new userProto.UserService("localhost:50051", grpc.credentials.createInsecure());

// CLI Interface for user input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

// Function to interactively get user input
function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => resolve(answer));
  });
}

// Function to handle user choice
async function main() {
  console.log("\n1. Register User\n2. Login User\n3. Get User Profile\n4. Update User Profile\n5. Exit");
  
  const choice = await askQuestion("Enter your choice: ");

  switch (choice) {
    case "1":
      const fullName = await askQuestion("Enter full name: ");
      const email = await askQuestion("Enter email: ");
      const password = await askQuestion("Enter password: ");
      const address = await askQuestion("Enter address: ");
      const phoneNumber = await askQuestion("Enter phone number: ");

      client.RegisterUser({ full_name: fullName, email, password, address, phone_number: phoneNumber }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log(`${response.message}, User ID: ${response.user_id}`);
        main();
      });
      break;

    case "2":
      const loginEmail = await askQuestion("Enter email: ");
      const loginPassword = await askQuestion("Enter password: ");

      client.LoginUser({ email: loginEmail, password: loginPassword }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log(`${response.message}, User ID: ${response.user_id}`);
        main();
      });
      break;

    case "3":
      const userId = await askQuestion("Enter User ID: ");

      client.GetUserProfile({ user_id: userId }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else {
          console.log("\nUser Profile:");
          console.log(`  Name: ${response.full_name}`);
          console.log(`  Email: ${response.email}`);
          console.log(`  Address: ${response.address}`);
          console.log(`  Phone: ${response.phone_number}`);
        }
        main();
      });
      break;

    case "4":
      const updateEmail = await askQuestion("Enter your registered email: ");
      const newFullName = await askQuestion("Enter new full name: ");
      const newAddress = await askQuestion("Enter new address: ");
      const newPhoneNumber = await askQuestion("Enter new phone number: ");

      client.UpdateUserProfile({ email: updateEmail, full_name: newFullName, address: newAddress, phone_number: newPhoneNumber }, (error, response) => {
        if (error) console.error("Error:", error.message);
        else console.log(`${response.message}`);
        main();
      });
      break;

    case "5":
      console.log("Exiting...");
      rl.close();
      break;

    default:
      console.log("Invalid choice, try again.");
      main();
  }
}
main();
