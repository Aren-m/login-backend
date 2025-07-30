require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const authRoutes = require('./routes/auth');
const invoiceRoutes = require('./routes/invoices');
const poRoutes = require('./routes/purchaseOrders');
const chatRoutes = require('./routes/chat');
const reguRoutes = require('./routes/regu');

const app = express();

const path = require('path');
app.use('/Public', express.static(path.join(__dirname, 'Public')));


// Middleware
app.use(cors());
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/invoices', invoiceRoutes);
app.use('/api/pos', poRoutes);
app.use('/chat', chatRoutes);
app.use('/api/regu', reguRoutes);


// MongoDB connection
console.log("Connecting to MongoDB...");
mongoose.connect(process.env.MONGO_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true,
  serverSelectionTimeoutMS: 10000,
})
  .then(() => {
    console.log('✅ Connected to MongoDB');
    app.listen(process.env.PORT || 5000, () => {
      console.log(`🚀 Server is running on port ${process.env.PORT || 5000}`);
    });
  })
  .catch(err => {
    console.error('❌ MongoDB connection error:', err.message);
  });
