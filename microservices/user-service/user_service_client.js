const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");
const readline = require("readline");
const redis = require("redis");

const clientRedis = redis.createClient();
clientRedis.connect();

let sessionToken = "";

const packageDefinition = protoLoader.loadSync("user_service.proto", {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const userProto = grpc.loadPackageDefinition(packageDefinition).user_service;
const client = new userProto.UserService("localhost:50051", grpc.credentials.createInsecure());

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

function ask(question) {
  return new Promise(resolve => rl.question(question, resolve));
}

async function main() {
  console.log("\n1. Register\n2. Login\n3. Get Profile\n4. Update Profile\n5. Logout\n6. Exit");
  const choice = await ask("Enter choice: ");

  switch (choice) {
    case "1":
      const fullName = await ask("Full name: ");
      const email = await ask("Email: ");
      const password = await ask("Password: ");
      const address = await ask("Address: ");
      const phone = await ask("Phone: ");
      client.RegisterUser({ full_name: fullName, email, password, address, phone_number: phone }, (err, res) => {
        if (err) console.log("Error:", err.message);
        else console.log(res.message, res.user_id);
        main();
      });
      break;

    case "2":
      const loginEmail = await ask("Email: ");
      const loginPassword = await ask("Password: ");
      client.LoginUser({ email: loginEmail, password: loginPassword }, (err, res) => {
        if (err) console.log("Error:", err.message);
        else {
          sessionToken = res.session_token;
          console.log(res.message, "\nSession Token:", sessionToken);
        }
        main();
      });
      break;

    case "3":
      if (!sessionToken) return console.log("Please login first"), main();
      client.GetUserProfile({ session_token: sessionToken }, (err, res) => {
        if (err || !res.email) console.log("Session expired or invalid.");
        else console.log(`\nName: ${res.full_name}\nEmail: ${res.email}\nAddress: ${res.address}\nPhone: ${res.phone_number}`);
        main();
      });
      break;

    case "4":
      if (!sessionToken) return console.log("Please login first"), main();
      const newName = await ask("New name: ");
      const newAddress = await ask("New address: ");
      const newPhone = await ask("New phone: ");
      client.UpdateUserProfile({ session_token: sessionToken, full_name: newName, address: newAddress, phone_number: newPhone }, (err, res) => {
        console.log(res.message);
        main();
      });
      break;

    case "5":
      if (!sessionToken) return console.log("Not logged in."), main();
      client.LogoutUser({ session_token: sessionToken }, (err, res) => {
        console.log(res.message);
        sessionToken = "";
        main();
      });
      break;

    case "6":
      console.log("Goodbye!");
      rl.close();
      process.exit();
      break;

    default:
      console.log("Invalid choice.");
      main();
  }
}
main();
