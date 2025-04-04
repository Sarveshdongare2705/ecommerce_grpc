const ProductServiceClient = require('./product_service_client');
const readline = require('readline');

const client = new ProductServiceClient();

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

function askQuestion(question) {
    return new Promise(resolve => {
        rl.question(question, answer => resolve(answer));
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

    try {
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
                    attributesStr.split(',').forEach(pair => {
                        const [key, value] = pair.split(':').map(s => s.trim());
                        attributes[key] = value;
                    });
                }

                const createResponse = await client.createProduct({
                    name, description, price, category, brand, stock, attributes
                });
                console.log("\nResponse:", createResponse);
                break;

            case "2":
                const productId = await askQuestion("Enter product ID: ");
                const getResponse = await client.getProduct(productId);
                console.log("\nProduct Details:");
                if (getResponse.success) {
                    console.log(JSON.stringify(getResponse.product, null, 2));
                } else {
                    console.log("Error:", getResponse.message);
                }
                break;

            case "3":
                const listCategory = await askQuestion("Enter category (optional): ");
                const listBrand = await askQuestion("Enter brand (optional): ");
                const minPrice = parseFloat(await askQuestion("Enter minimum price (optional): "));
                const maxPrice = parseFloat(await askQuestion("Enter maximum price (optional): "));
                const page = parseInt(await askQuestion("Enter page number (default 1): ") || "1");
                const limit = parseInt(await askQuestion("Enter items per page (default 10): ") || "10");

                const filters = {
                    category: listCategory,
                    brand: listBrand,
                    min_price: minPrice,
                    max_price: maxPrice,
                    page,
                    limit
                };

                const products = await client.listProducts(filters);
                console.log("\nProducts List:");
                products.forEach((product, index) => {
                    console.log(`\n--- Product ${index + 1} ---`);
                    console.log(JSON.stringify(product, null, 2));
                });
                break;

            case "4":
                const updateId = await askQuestion("Enter product ID to update: ");
                const updateName = await askQuestion("Enter new name (or press enter to skip): ");
                const updateDesc = await askQuestion("Enter new description (or press enter to skip): ");
                const updatePrice = parseFloat(await askQuestion("Enter new price (or press enter to skip): "));
                const updateCategory = await askQuestion("Enter new category (or press enter to skip): ");
                const updateBrand = await askQuestion("Enter new brand (or press enter to skip): ");
                const updateStock = parseInt(await askQuestion("Enter new stock quantity (or press enter to skip): "));

                const updateData = { product_id: updateId };
                if (updateName) updateData.name = updateName;
                if (updateDesc) updateData.description = updateDesc;
                if (!isNaN(updatePrice)) updateData.price = updatePrice;
                if (updateCategory) updateData.category = updateCategory;
                if (updateBrand) updateData.brand = updateBrand;
                if (!isNaN(updateStock)) updateData.stock = updateStock;

                const updateResponse = await client.updateProduct(updateId, updateData);
                console.log("\nResponse:", updateResponse);
                break;

            case "5":
                const deleteId = await askQuestion("Enter product ID to delete: ");
                const deleteResponse = await client.deleteProduct(deleteId);
                console.log("\nResponse:", deleteResponse);
                break;

            case "6":
                console.log("Exiting...");
                rl.close();
                process.exit(0);
                break;

            default:
                console.log("Invalid choice, try again.");
        }
    } catch (error) {
        console.error("Error:", error.message);
    }

    // Continue with the menu unless explicitly exited
    if (choice !== "6") {
        main();
    }
}

main(); 