const mongoose = require('mongoose');
const Conversation = require('./models/Conversation');

async function main() {
  await mongoose.connect(process.env.MONGO_URI);
  const conversations = await Conversation.find({});
  console.log(conversations);
  await mongoose.disconnect();
}

main();