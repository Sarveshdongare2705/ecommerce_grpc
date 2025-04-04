const readline = require("readline");
const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");
const path = require("path");

const PROTO_PATH = path.join(__dirname, "notification_service.proto");

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const notificationProto = grpc.loadPackageDefinition(packageDefinition).notification;

const client = new notificationProto.NotificationService(
  "localhost:50055",
  grpc.credentials.createInsecure()
);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

rl.question("Enter User ID: ", (userId) => {
  rl.question("Enter Message to send: ", (message) => {
    const payload = {
      user_id: userId.trim(),
      message: message.trim(),
    };

    client.SendNotification(payload, (err, response) => {
      if (err) {
        console.error("Error:", err.message);
      } else {
        console.log("Response:", response.status);
      }
      rl.close();
    });
  });
});
