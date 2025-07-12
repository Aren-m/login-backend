const mongoose = require('mongoose');

const conversationSchema = new mongoose.Schema({
  sessionId: String,
  timestamp: { type: Date, default: Date.now },
  history: [[String]],
});

module.exports = mongoose.model('Conversation', conversationSchema);
