import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import axios from "axios";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const PY_SERVICE = process.env.PYTHON_BASE_URL || "http://localhost:8000";

app.get("/api/health", async (req, res) => {
  try {
    const { data } = await axios.get(`${PY_SERVICE}/health`);
    res.json({ node: "ok", python: data });
  } catch (err) {
    res.status(500).json({ error: "Python service not reachable", details: err.message });
  }
});

app.post("/api/ingest", async (req, res) => {
  try {
    const { data } = await axios.post(`${PY_SERVICE}/ingest`);
    res.json(data);
  } catch (err) {
    const status = err.response?.status || 500;
    res.status(status).json({ error: err.response?.data || err.message });
  }
});

app.post("/api/chat", async (req, res) => {
  try {
    const payload = { query: req.body.query || "", k: req.body.k || 3, return_snippets: true };
    const { data } = await axios.post(`${PY_SERVICE}/chat`, payload);
    res.json(data);
  } catch (err) {
    const status = err.response?.status || 500;
    res.status(status).json({ error: err.response?.data || err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Node API running on http://localhost:${PORT}`));
