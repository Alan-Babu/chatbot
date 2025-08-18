const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs');
const feedbackFile = path.join(__dirname, 'feedback.json');

const cors = require('cors');   

const corsOptions = {
    origin: 'http://localhost:4200', // Adjust this to your frontend URL
    methods: 'GET,HEAD,PUT,PATCH,POST,DELETE',
}
const app = express();
app.use(cors(corsOptions));
app.use(bodyParser.json());

const base_url = 'http://localhost:8000';

app.post('/api/chat', async (req, res) => {
    try{
        if (!req.body.query) {
            return res.status(400).json({ error: 'Missing query parameter' });
        }
        const {query,k} = req.body;
        const topK = k ?? 3;
        const response = await axios.post(`${base_url}/chat`, {
            query,
            k: topK
        },
        {responseType: 'stream'}); // Use stream to handle large responses
        res.setHeader('Content-Type', 'text/plain');
        response.data.pipe(res); // Pipe the response data directly to the client
    }catch (error) {
        console.error('Error in /chat:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.post('/api/ingest', async (req, res) => {
    try {
        const response = await axios.post(`${base_url}/ingest`);
        res.json(response.data);
    }catch (error) {
        console.error('Error in /api/ingest:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.get('/api/menu', async (req, res) => {
    try{
        const response = await axios.get(`${base_url}/menu`);
        res.json(response.data);
    }catch (error) {
        console.error('Error in /api/menu:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

function readFeedback() {
  if (!fs.existsSync(feedbackFile)) {
    return { messages: [], sessions: [] };
  }
  const data = fs.readFileSync(feedbackFile);
  return JSON.parse(data);
}

function writeFeedback(data) {
  fs.writeFileSync(feedbackFile, JSON.stringify(data, null, 2));
}

app.post('/api/feedback/message', (req, res) => {
  const { messageId, feedback } = req.body;
  if (!messageId || !feedback) {
    return res.status(400).send({ error: 'Missing messageId or feedback' });
  }

  const data = readFeedback();
  data.messages.push({ messageId, feedback, timestamp: new Date() });
  writeFeedback(data);

  res.send({ success: true });
});

// Save end-of-session feedback
app.post('/api/feedback/session', (req, res) => {
  const { rating } = req.body;
  if (!rating || rating < 1 || rating > 5) {
    return res.status(400).send({ error: 'Invalid rating' });
  }

  const data = readFeedback();
  data.sessions.push({ rating, timestamp: new Date() });
  writeFeedback(data);

  res.send({ success: true });
});

app.listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});