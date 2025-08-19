const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs');
require('dotenv').config();

const feedbackFile = path.join(__dirname, 'feedback.json');
const cors = require('cors');

const PORT = process.env.PORT || 3000;
const FRONTEND_ORIGIN = process.env.CORS_ORIGIN || 'http://localhost:4200';
const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

const corsOptions = {
	origin: FRONTEND_ORIGIN,
	methods: 'GET,HEAD,PUT,PATCH,POST,DELETE',
};

const app = express();
app.use(cors(corsOptions));
app.use(bodyParser.json());

// Shared axios client with sane defaults
const http = axios.create({
	baseURL: BASE_URL,
	timeout: 30000,
});

// Simple async feedback store with serialized writes
class FeedbackStore {
	constructor(filePath) {
		this.filePath = filePath;
		this.queue = Promise.resolve();
	}

	_readSafe() {
		try {
			if (!fs.existsSync(this.filePath)) {
				return { messages: [], sessions: [] };
			}
			const data = fs.readFileSync(this.filePath);
			return JSON.parse(data);
		} catch (_) {
			return { messages: [], sessions: [] };
		}
	}

	_writeSafe(data) {
		return fs.promises
			.writeFile(this.filePath, JSON.stringify(data, null, 2))
			.catch(() => void 0);
	}

	withLock(fn) {
		this.queue = this.queue.then(() => fn()).catch(() => void 0);
		return this.queue;
	}

	addMessageFeedback(messageId, feedback) {
		return this.withLock(async () => {
			const data = this._readSafe();
			data.messages.push({ messageId, feedback, timestamp: new Date() });
			await this._writeSafe(data);
		});
	}

	addSessionFeedback(rating) {
		return this.withLock(async () => {
			const data = this._readSafe();
			data.sessions.push({ rating, timestamp: new Date() });
			await this._writeSafe(data);
		});
	}
}

const feedbackStore = new FeedbackStore(feedbackFile);

app.post('/api/chat', async (req, res) => {
    try{
        if (!req.body.query) {
            return res.status(400).json({ error: 'Missing query parameter' });
        }
        const {query,k,session_id} = req.body;
        const topK = k ?? 3;
        const response = await http.post('/chat', { query, k: topK,session_id }, { responseType: 'stream' });
        res.setHeader('Content-Type', 'text/plain');
        response.data.pipe(res); // Pipe the response data directly to the client
    }catch (error) {
        const status = error?.response?.status || 500;
        const detail = error?.response?.data || error?.message || 'Internal Server Error';
        console.error('Error in /chat:', detail);
        res.status(status).json({ error: 'Upstream chat error', detail });
    }
});

app.post('/api/ingest', async (req, res) => {
    try {
        const response = await http.post('/ingest');
        res.json(response.data);
    }catch (error) {
        console.error('Error in /api/ingest:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.get('/api/menu', async (req, res) => {
    try{
        const response = await http.get('/menu');
        res.json(response.data);
    }catch (error) {
        console.error('Error in /api/menu:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.post('/api/feedback/message', (req, res) => {
  const { messageId, feedback } = req.body;
  if (!messageId || !feedback) {
    return res.status(400).send({ error: 'Missing messageId or feedback' });
  }

	// Persist locally for redundancy and forward to FastAPI for analysis
	feedbackStore
		.addMessageFeedback(messageId, feedback)
		.catch(() => void 0)
		.finally(async () => {
			try {
				const resp = await http.post('/feedback/message', { messageId, feedback });
				res.send(resp.data ?? { success: true });
			} catch {
				res.send({ success: true });
			}
		});
});

// Save end-of-session feedback
app.post('/api/feedback/session', (req, res) => {
  const { rating } = req.body;
  if (!rating || rating < 1 || rating > 5) {
    return res.status(400).send({ error: 'Invalid rating' });
  }

	feedbackStore
		.addSessionFeedback(rating)
		.catch(() => void 0)
		.finally(async () => {
			try {
				const resp = await http.post('/feedback/session', { rating });
				res.send(resp.data ?? { success: true });
			} catch {
				res.send({ success: true });
			}
		});
});

// Fetch chat history
app.get('/api/history/:sessionId', async (req, res) => {
  try {
    const response = await http.get(`/history/${encodeURIComponent(req.params.sessionId)}`);
    res.json(response.data);
  } catch (error) {
	const status = error?.response?.status || 500;
	const detail = error?.response?.data || error?.message || 'Internal Server Error';
    console.error('Error in /api/history:', detail);
    res.status(status).json({ error: 'Upstream history error',detail });
  }
});

// Fuzzy search
app.get('/api/search', async (req, res) => {
  try {
    const { q, limit } = req.query;
	if(!q) return res.status(400).json({ error: 'Missing query parameter q' });
    const response = await http.get('/search', { params: { q, limit } });
    res.json(response.data);
  } catch (error) {
	const status = error?.response?.status || 500;
	const detail = error?.response?.data || error?.message || 'Internal Server Error';
    console.error('Error in /api/search:', detail);
    res.status(status).json({ error: 'Upstream search error' ,detail});
  }
});


app.post('/api/suggestions', async (req, res) => {
  try {
    const response = await http.post('/suggestions', req.body);
    res.json(response.data);
  } catch (error) {
    const status = error?.response?.status || 500;
    const detail = error?.response?.data || error?.message || 'Internal Server Error';
    console.error('Error in /api/suggestions:', detail);
    res.status(status).json({ error: 'Upstream suggestions error', detail });
  }
});


app.get('/api/health', (_req, res) => {
	res.json({ status: 'ok', upstream: BASE_URL, time: new Date().toISOString() });
});

app.listen(PORT, () => {
	console.log(`Server is running on http://localhost:${PORT} (upstream: ${BASE_URL})`);
});