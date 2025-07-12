// routes/chat.js
const router = require('express').Router();
const OpenAI = require('openai');

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const SYSTEM_PROMPT = process.env.SYSTEM_PROMPT || "You are a helpful assistant.";

router.post('/', async (req, res) => {
  const { message = '', history = [] } = req.body;

  // Build chat history for OpenAI
  const chat_history = [
    { role: 'system', content: SYSTEM_PROMPT },
    ...history.flatMap(([user, bot]) => [
      { role: 'user', content: user },
      { role: 'assistant', content: bot }
    ]),
    { role: 'user', content: message }
  ];

  try {
    const completion = await openai.chat.completions.create({
      model: "gpt-4.1",
      messages: chat_history,
      temperature: 0.7,
      max_tokens: 400,
    });
    const reply = completion.choices[0].message.content.trim();
    res.json({ reply });
  } catch (err) {
    console.error(err);
    res.json({ reply: "Sorry, there was an error contacting the AI service." });
  }
});

module.exports = router;

