const express = require('express');
const Invoice = require('../models/Invoice');
const authMiddleware = require('../middleware/auth');
const PDFDocument = require('pdfkit');


function generateInvoicePDF(invoice, res) {
  const doc = new PDFDocument({ size: 'A4', margin: 50 });
  doc.pipe(res);

  // HEADER
  doc
    .fontSize(20)
    .fillColor('#2C3E50')
    .text('INVOICE - GUROME HEALTH', { align: 'center' })
    .moveDown(0.5);

  doc
    .fontSize(10)
    .fillColor('#555')
    .text('Street Address Line 01')
    .text('Street Address Line 02')
    .text('+1 (999)-999-999')
    .text('Email Address')
    .moveDown();

  // INVOICE DETAILS
  doc
    .fontSize(12)
    .fillColor('#000')
    .text(`Invoice #: ${invoice.invoiceNumber}`)
    .text(`Purchase Order #: ${invoice.poNumber || 'N/A'}`)
    .text(`Date of Issue: ${new Date(invoice.createdAt).toLocaleDateString()}`)
    .text(`Due Date: ${new Date(invoice.dueDate).toLocaleDateString()}`)
    .moveDown();

  // BILL TO
  doc
    .font('Helvetica-Bold')
    .text('Bill To:')
    .font('Helvetica')
    .text(`${invoice.client}`)
    .text(invoice.clientAddressLine1 || '')
    .text(invoice.clientAddressLine2 || '')
    .moveDown();

  // ITEMS TABLE
  doc
    .font('Helvetica-Bold')
    .text('ITEM/SERVICE', 50, doc.y, { continued: true })
    .text('QTY', 200, doc.y, { continued: true })
    .text('RATE', 280, doc.y, { continued: true })
    .text('AMOUNT', 360, doc.y);

  doc.moveTo(50, doc.y + 5).lineTo(500, doc.y + 5).stroke();
  doc.moveDown();

  doc.font('Helvetica');
  invoice.items.forEach(item => {
    doc
      .text(item.description, 50, doc.y, { continued: true })
      .text(item.quantity.toString(), 200, doc.y, { continued: true })
      .text(`$${item.price.toFixed(2)}`, 280, doc.y, { continued: true })
      .text(`$${(item.quantity * item.price).toFixed(2)}`, 360, doc.y);
    doc.moveDown();
  });

  // TOTALS
  const addLine = (label, value) => {
    doc
      .font('Helvetica-Bold')
      .text(label, 300, doc.y, { continued: true })
      .font('Helvetica')
      .text(`$${value.toFixed(2)}`, 400, doc.y);
  };

  doc.moveDown();
  addLine('Shipping:', invoice.shipping || 0);
  addLine('Tax (5%):', invoice.tax || 0);
  addLine('GST:', invoice.gst || 0);
  addLine('Total:', invoice.total || 0);

  doc.moveDown();

  // FOOTER
  doc
    .fontSize(10)
    .fillColor('#666')
    .text('Thank you for your business.', 50, doc.page.height - 100, {
      align: 'center'
    });

  doc.end();
}

const router = express.Router();

// Protect all routes with auth middleware
router.use(authMiddleware);

// Create invoice: from logged-in user to another user
router.post('/', async (req, res) => {
  try {
    const { toUserId, client, items, total, dueDate, poNumber, shipping, tax, gst } = req.body;


    if (!toUserId) {
      return res.status(400).json({ error: 'Recipient (toUserId) is required' });
    }

    const invoice = new Invoice({
      fromUser: req.user.id,
      toUser: toUserId,
      client,
      items,
      total,
      dueDate,
      poNumber,
      shipping,
      tax,
      gst,
      invoiceNumber: `INV-${Date.now()}` // optional: generate simple invoice number
    });


    await invoice.save();

    // Broadcast to all connected dashboards via socket.io
    const io = req.app.get('io');
    io.emit('invoice:new', invoice);

    res.status(201).json(invoice);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});


/////
// Get all invoices (admin or personal)
router.get('/', async (req, res) => {
  try {
    let invoices;

    if (req.user.role === 'admin') {
      invoices = await Invoice.find().populate('toUser fromUser', 'email');
    } else {
      invoices = await Invoice.find({
        $or: [
          { fromUser: req.user.id },
          { toUser: req.user.id }
        ]
      }).populate('toUser fromUser', 'email');
    }

    const formatted = invoices.map(inv => ({
      orderNumber: inv.invoiceNumber || inv._id.toString().slice(-6),
      client: inv.client,
      product: inv.items?.[0]?.description || 'N/A',
      status: inv.status || 'Unpaid',
      orderDate: inv.createdAt.toISOString().split('T')[0],
      units: inv.items.reduce((sum, item) => sum + item.quantity, 0),
      totalCost: inv.total,
      invoiceUrl: `/api/invoices/${inv._id}/pdf`,
      poUrl: inv.poNumber ? `/api/purchaseorders/${inv.poNumber}/pdf` : null
    }));

    res.json(formatted);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Return invoice PDF
router.get('/:id/pdf', async (req, res) => {
  try {
    const invoice = await Invoice.findById(req.params.id)
      .populate('fromUser', 'email role')
      .populate('toUser', 'email role');

    if (!invoice) return res.status(404).json({ error: 'Invoice not found' });

    if (
      req.user.role !== 'admin' &&
      invoice.fromUser._id.toString() !== req.user.id &&
      invoice.toUser._id.toString() !== req.user.id
    ) {
      return res.status(403).json({ error: 'Not authorized' });
    }

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `inline; filename=invoice-${invoice._id}.pdf`);

    generateInvoicePDF(invoice, res);
  } catch (err) {
    console.error('PDF generation error:', err);
    res.status(500).json({ error: 'Failed to generate PDF' });
  }
});

module.exports = router;