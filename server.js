const express = require('express');
const cors = require('cors');
const morgan = require('morgan');

// Import routes
const searchRoutes = require('./routes/search');
const episodesRoutes = require('./routes/episodes');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(morgan('combined')); // Logging for all requests
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.use('/search', searchRoutes);
app.use('/episodes', episodesRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Server is running' });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Search endpoint: http://localhost:${PORT}/search?term=your_search_term`);
  console.log(`Episodes endpoint: http://localhost:${PORT}/episodes?feedUrl=your_feed_url`);
}); 