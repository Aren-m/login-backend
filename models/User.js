// models/User.js
const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  role: { 
    type: String, 
    enum: ['hospital', 'vendor', 'physician', 'admin'], 
    required: true 
  }
});

module.exports = mongoose.model('User', userSchema);