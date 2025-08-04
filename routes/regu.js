// routes/regu.js
const express = require('express');
const OpenAI = require('openai');
const Conversation = require('../models/Conversation');
require('dotenv').config();

const router = express.Router();

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const ASSISTANT_ID = process.env.OPENAI_ASSISTANT_ID;

// Helper: pull first assistant text from messages.list
function extractAssistantText(messages) {
  for (const msg of messages) {
    if (msg.role === 'assistant' && Array.isArray(msg.content)) {
      for (const part of msg.content) {
        if (part.type === 'text' && part.text?.value) return part.text.value;
      }
    }
  }
  return null;
}

/**
 * POST /regu
 * Body: { message: string, sessionId?: string, history?: Array<[string, string]> }
 * Returns: { reply: string, sessionId: string }
 */
router.post('/', async (req, res) => {
  const { message = '', sessionId = '', history = [] } = req.body;

  if (!message) return res.json({ reply: 'No message provided.' });
  if (!ASSISTANT_ID) return res.json({ reply: 'Assistant not configured.' });

  try {
    // 1) Create (or reuse) a thread. The threadId IS your conversational context.
    let threadId = sessionId;
    if (!threadId) {
      const thread = await openai.beta.threads.create();
      threadId = thread.id;
      console.log('🧵 Created new thread:', threadId);
    } else {
      // Optional: sanity log to verify reuse
      console.log('🧵 Reusing thread:', threadId);
    }

    // 2) Add the user message to the thread
    await openai.beta.threads.messages.create(threadId, {
      role: 'user',
      content: message,
    });

    // 3) Run the assistant on this thread
    const run = await openai.beta.threads.runs.create(threadId, {
      assistant_id: ASSISTANT_ID,
    });

    // 4) Poll for completion (simple polling loop)
    let replyText = '';
    const maxTries = 30; // ~15s at 500ms interval
    for (let i = 0; i < maxTries; i++) {
      const status = await openai.beta.threads.runs.retrieve(threadId, run.id);

      if (status.status === 'completed') {
        const list = await openai.beta.threads.messages.list(threadId, {
          order: 'desc',
          limit: 10,
        });
        replyText = extractAssistantText(list.data) || 'No reply.';
        break;
      }

      if (['failed', 'cancelled', 'expired'].includes(status.status)) {
        replyText = 'Sorry, the assistant run did not complete.';
        break;
      }

      await new Promise((r) => setTimeout(r, 500));
    }

    if (!replyText) replyText = 'Sorry, the assistant took too long to respond.';

    // 5) Save conversation (append this turn). If you prefer a single doc per session,
    // swap to findOneAndUpdate with $push (shown below).
    try {
      // EITHER: keep creating a new record each turn (your current behavior)
      await Conversation.create({
        sessionId: sessionId || threadId,      // use existing sessionId or the new threadId
        timestamp: new Date(),
        history: [...history, [message, replyText]],
      });
      console.log('✅ Conversation saved');
      
      // OR: (recommended) keep one doc per session and append history
      // await Conversation.findOneAndUpdate(
      //   { sessionId: sessionId || threadId },
      //   {
      //     $push: { history: [message, replyText] },
      //     $setOnInsert: { timestamp: new Date() }
      //   },
      //   { upsert: true, new: true }
      // );
    } catch (e) {
      console.warn('⚠️ Failed to save conversation:', e.message);
    }

    // 6) Return both the reply AND the sessionId (threadId). The client must reuse this.
    return res.json({ reply: replyText, sessionId: threadId });
  } catch (err) {
    console.error('OpenAI error:', err?.message || err);
    return res.json({ reply: 'Sorry, there was an error contacting the assistant.' });
  }
});

module.exports = router;
