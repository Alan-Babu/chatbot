const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());

const base_url = 'http://localhost:8000';

app.post('/api/chat', async (req, res) => {
    try{
        console.log('Received request on /api/chat:', req.body);
        console.log('####################');
        if (!req.body.query || !req.body.k) {
            return res.status(400).json({ error: 'Missing query or k parameter' });
        }
        const {query,k} = req.body;
        const response = await axios.post(`${base_url}/chat`, {
            query,
            k
        });
        res.json(response.data);
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

app.listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});