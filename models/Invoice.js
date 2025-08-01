const mongoose = require('mongoose');

const InvoiceSchema = new mongoose.Schema({
  invoiceNumber: { type: String, required: false, unique: true }, // You can generate this in the backend
  fromUser: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: false },
  toUser: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: false },
  client: { type: String, required: true },
  poNumber: { type: String }, // Links to PO
  items: [{
    description: { type: String, required: true },
    quantity: { type: Number, required: true },
    price: { type: Number, required: true }
  }],
  shipping: { type: Number, default: 0 },
  tax: { type: Number, default: 0 },
  gst: { type: Number, default: 0 },
  total: { type: Number, required: true },
  dueDate: { type: Date },
  status: { type: String, enum: ['unpaid', 'paid', 'cancelled'], default: 'unpaid' },
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('Invoice', InvoiceSchema);
