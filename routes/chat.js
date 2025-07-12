// routes/chat.js
const router = require('express').Router();
const { Configuration, OpenAIApi } = require('openai');

require('dotenv').config();

const configuration = new Configuration({
  apiKey: process.env.OPENAI_API_KEY,
});
const openai = new OpenAIApi(configuration);

const SYSTEM_PROMPT = process.env.SYSTEM_PROMPT || "You are a helpful assistant.";

router.post('/', async (req, res) => {
  const { message = '', history = [] } = req.body;

  // Rebuild message history for OpenAI
  const chat_history = [
    { role: 'system', content: SYSTEM_PROMPT },
    ...history.flatMap(([user, bot]) => [
      { role: 'user', content: user },
      { role: 'assistant', content: bot }
    ]),
    { role: 'user', content: message }
  ];

  try {
    const completion = await openai.createChatCompletion({
      model: "gpt-4.1",
      messages: chat_history,
      temperature: 0.7,
      max_tokens: 1000,
    });
    const reply = completion.data.choices[0].message.content.trim();
    res.json({ reply });
  } catch (err) {
    console.error(err);
    res.json({ reply: "Sorry, there was an error contacting the AI service." });
  }
});

module.exports = router;
