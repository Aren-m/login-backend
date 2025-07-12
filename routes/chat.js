// routes/chat.js
const express = require('express');
const path = require('path');
const fs = require('fs');
const OpenAI = require('openai');

require('dotenv').config();

const router = express.Router();

// ------------ OpenAI SDK (v4) ------------
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// ------------ Load reference file once ------------
let extraContent = '';
try {
  const filePath = path.join(__dirname, '../Public/GravityMedTech.rtf');
  extraContent = fs.readFileSync(filePath, 'utf8');
  console.log('✅ Loaded GravityMedTech.rtf for prompt context');
} catch (err) {
  console.warn('⚠️  Could not read GravityMedTech.rtf:', err.message);
}

// ------------ POST /chat ------------
router.post('/', async (req, res) => {
  const { message = '', history = [] } = req.body;

  // Build the system prompt with the reference file
  const SYSTEM_PROMPT =
    (process.env.SYSTEM_PROMPT || 'You are a helpful assistant.') +
    '\n\nReference File Content:\n' +
    extraContent;

  // Assemble chat history for OpenAI
  const chatHistory = [
    { role: 'system', content: SYSTEM_PROMPT },
    ...history.flatMap(([user, bot]) => [
      { role: 'user', content: user },
      { role: 'assistant', content: bot },
    ]),
    { role: 'user', content: message },
  ];

  try {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4.1',
      messages: chatHistory,
      temperature: 0.7,
      max_tokens: 400,
    });

    const reply = completion.choices[0].message.content.trim();
    res.json({ reply });
  } catch (err) {
    console.error('OpenAI error:', err.message);
    res.json({ reply: 'Sorry, there was an error contacting the AI service.' });
  }
});

module.exports = router;


