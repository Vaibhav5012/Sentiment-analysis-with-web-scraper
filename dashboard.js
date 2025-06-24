// Sample data - this would normally come from your Python application
const sampleData = {
    reviews: [
        {
            text: "This product exceeded my expectations! The quality is outstanding and delivery was super fast. Highly recommend to anyone looking for reliability.",
            sentiment: "POSITIVE",
            confidence: 0.95,
            date: "2024-01-15T10:30:00Z",
            source: "Amazon Product Reviews"
        },
        {
            text: "Terrible experience. The item arrived damaged and customer service was unhelpful. Would not buy again.",
            sentiment: "NEGATIVE", 
            confidence: 0.92,
            date: "2024-01-14T15:45:00Z",
            source: "Amazon Product Reviews"
        },
        {
            text: "It's okay, nothing special. Does what it's supposed to do but doesn't stand out from competitors.",
            sentiment: "NEUTRAL",
            confidence: 0.78,
            date: "2024-01-13T09:15:00Z",
            source: "Amazon Product Reviews"
        },
        {
            text: "Amazing customer service! They went above and beyond to resolve my issue. The product quality is also top-notch.",
            sentiment: "POSITIVE",
            confidence: 0.98,
            date: "2024-01-12T14:20:00Z",
            source: "Amazon Product Reviews"
        },
        {
            text: "Waste of money. Poor build quality and doesn't work as advertised. Very disappointed with this purchase.",
            sentiment: "NEGATIVE",
            confidence: 0.89,
            date: "2024-01-11T11:30:00Z",
            source: "Amazon Product Reviews"
        }
    ]
};

// Global variables
let currentData = sampleData.reviews;
let currentPage = 0;
let reviewsPerPage = 10;
let sentimentChart = null;
let timelineChart = null;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
});

function initializeDashboard() {
    updateLastUpdated();
    updateStatistics();
    initializeCharts();
    renderReviews();
}

function setupEventListeners() {
    // Chart type toggle
    document.querySelectorAll('.chart-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            updateSentimentChart(this.dataset.chart);
        });
    });

    // Filter controls
    document.getElementById('sentimentFilter').addEventListener('change', filterReviews);
    document.getElementById('sortOrder').addEventListener('change', sortReviews);
    
    // Load more button
    document.getElementById('loadMoreBtn').addEventListener('click', loadMoreReviews);
}

function updateLastUpdated() {
    const now = new Date();
    const timeString = now.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    document.getElementById('lastUpdated').textContent = timeString;
}

function updateStatistics() {
    const stats = calculateStatistics(currentData);
    
    document.getElementById('totalCount').textContent = stats.total;
    document.getElementById('positiveCount').textContent = stats.positive;
    document.getElementById('negativeCount').textContent = stats.negative;
    document.getElementById('neutralCount').textContent = stats.neutral;
    
    document.getElementById('positivePercentage').textContent = `${stats.positivePercent}%`;
    document.getElementById('negativePercentage').textContent = `${stats.negativePercent}%`;
    document.getElementById('neutralPercentage').textContent = `${stats.neutralPercent}%`;
    document.getElementById('avgConfidence').textContent = `${stats.avgConfidence}% avg confidence`;
}

function calculateStatistics(data) {
    const total = data.length;
    const positive = data.filter(r => r.sentiment === 'POSITIVE').length;
    const negative = data.filter(r => r.sentiment === 'NEGATIVE').length;
    const neutral = data.filter(r => r.sentiment === 'NEUTRAL').length;
    
    const avgConfidence = total > 0 ? 
        Math.round(data.reduce((sum, r) => sum + (r.confidence * 100), 0) / total) : 0;
    
    return {
        total,
        positive,
        negative,
        neutral,
        positivePercent: total > 0 ? Math.round((positive / total) * 100) : 0,
        negativePercent: total > 0 ? Math.round((negative / total) * 100) : 0,
        neutralPercent: total > 0 ? Math.round((neutral / total) * 100) : 0,
        avgConfidence
    };
}

function initializeCharts() {
    initializeSentimentChart();
    initializeTimelineChart();
}

function initializeSentimentChart() {
    const ctx = document.getElementById('sentimentChart').getContext('2d');
    const stats = calculateStatistics(currentData);
    
    sentimentChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Positive', 'Negative', 'Neutral'],
            datasets: [{
                data: [stats.positive, stats.negative, stats.neutral],
                backgroundColor: [
                    '#48bb78',
                    '#f56565', 
                    '#ed8936'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function initializeTimelineChart() {
    const ctx = document.getElementById('timelineChart').getContext('2d');
    const timelineData = prepareTimelineData(currentData);
    
    timelineChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Positive',
                    data: timelineData.positive,
                    borderColor: '#48bb78',
                    backgroundColor: 'rgba(72, 187, 120, 0.1)',
                    tension: 0.4,
                    fill: false
                },
                {
                    label: 'Negative', 
                    data: timelineData.negative,
                    borderColor: '#f56565',
                    backgroundColor: 'rgba(245, 101, 101, 0.1)',
                    tension: 0.4,
                    fill: false
                },
                {
                    label: 'Neutral',
                    data: timelineData.neutral,
                    borderColor: '#ed8936',
                    backgroundColor: 'rgba(237, 137, 54, 0.1)',
                    tension: 0.4,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM dd'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Reviews'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                }
            }
        }
    });
}

function prepareTimelineData(data) {
    const groupedData = {};
    
    data.forEach(review => {
        const date = new Date(review.date).toDateString();
        if (!groupedData[date]) {
            groupedData[date] = { positive: 0, negative: 0, neutral: 0 };
        }
        groupedData[date][review.sentiment.toLowerCase()]++;
    });
    
    const sortedDates = Object.keys(groupedData).sort((a, b) => new Date(a) - new Date(b));
    
    return {
        positive: sortedDates.map(date => ({
            x: new Date(date),
            y: groupedData[date].positive
        })),
        negative: sortedDates.map(date => ({
            x: new Date(date),
            y: groupedData[date].negative
        })),
        neutral: sortedDates.map(date => ({
            x: new Date(date),
            y: groupedData[date].neutral
        }))
    };
}

function updateSentimentChart(type) {
    if (!sentimentChart) return;
    
    sentimentChart.destroy();
    
    const ctx = document.getElementById('sentimentChart').getContext('2d');
    const stats = calculateStatistics(currentData);
    
    const chartConfig = {
        data: {
            labels: ['Positive', 'Negative', 'Neutral'],
            datasets: [{
                data: [stats.positive, stats.negative, stats.neutral],
                backgroundColor: [
                    '#48bb78',
                    '#f56565',
                    '#ed8936'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: type === 'pie' ? 'bottom' : 'top',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    }
                }
            }
        }
    };
    
    if (type === 'bar') {
        chartConfig.type = 'bar';
        chartConfig.options.scales = {
            y: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: 'Number of Reviews'
                }
            },
            x: {
                title: {
                    display: true,
                    text: 'Sentiment'
                }
            }
        };
    } else {
        chartConfig.type = 'pie';
    }
    
    sentimentChart = new Chart(ctx, chartConfig);
}

function renderReviews() {
    const container = document.getElementById('reviewsContainer');
    const startIndex = currentPage * reviewsPerPage;
    const endIndex = startIndex + reviewsPerPage;
    const reviewsToShow = currentData.slice(startIndex, endIndex);
    
    if (currentPage === 0) {
        container.innerHTML = '';
    }
    
    if (reviewsToShow.length === 0) {
        if (currentPage === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>No reviews found</h3>
                    <p>Try adjusting your filters to see more results.</p>
                </div>
            `;
        }
        document.getElementById('loadMoreBtn').style.display = 'none';
        return;
    }
    
    reviewsToShow.forEach(review => {
        const reviewCard = createReviewCard(review);
        container.appendChild(reviewCard);
    });
    
    // Update load more button
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (endIndex >= currentData.length) {
        loadMoreBtn.style.display = 'none';
    } else {
        loadMoreBtn.style.display = 'block';
        loadMoreBtn.textContent = `Load More Reviews (${currentData.length - endIndex} remaining)`;
    }
}

function createReviewCard(review) {
    const card = document.createElement('div');
    card.className = 'review-card';
    
    const sentimentClass = review.sentiment.toLowerCase();
    const confidencePercent = Math.round(review.confidence * 100);
    const reviewDate = new Date(review.date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
    
    card.innerHTML = `
        <div class="review-header">
            <span class="sentiment-badge ${sentimentClass}">${review.sentiment}</span>
            <span class="review-meta">${reviewDate}</span>
        </div>
        <div class="review-text">${review.text}</div>
        <div class="review-footer">
            <span>Source: ${review.source}</span>
            <span class="confidence-score">Confidence: ${confidencePercent}%</span>
        </div>
    `;
    
    return card;
}

function filterReviews() {
    const filter = document.getElementById('sentimentFilter').value;
    
    if (filter === 'all') {
        currentData = sampleData.reviews;
    } else {
        currentData = sampleData.reviews.filter(review => review.sentiment === filter);
    }
    
    currentPage = 0;
    updateStatistics();
    updateCharts();
    renderReviews();
}

function sortReviews() {
    const sortOrder = document.getElementById('sortOrder').value;
    
    currentData.sort((a, b) => {
        switch (sortOrder) {
            case 'newest':
                return new Date(b.date) - new Date(a.date);
            case 'oldest':
                return new Date(a.date) - new Date(b.date);
            case 'confidence':
                return b.confidence - a.confidence;
            default:
                return 0;
        }
    });
    
    currentPage = 0;
    renderReviews();
}

function loadMoreReviews() {
    currentPage++;
    renderReviews();
}

function updateCharts() {
    if (sentimentChart) {
        const stats = calculateStatistics(currentData);
        sentimentChart.data.datasets[0].data = [stats.positive, stats.negative, stats.neutral];
        sentimentChart.update();
    }
    
    if (timelineChart) {
        const timelineData = prepareTimelineData(currentData);
        timelineChart.data.datasets[0].data = timelineData.positive;
        timelineChart.data.datasets[1].data = timelineData.negative;
        timelineChart.data.datasets[2].data = timelineData.neutral;
        timelineChart.update();
    }
}

// Function to load real data (would be called from your Python app)
function loadRealData(reviewsData) {
    sampleData.reviews = reviewsData;
    currentData = reviewsData;
    currentPage = 0;
    
    updateLastUpdated();
    updateStatistics();
    updateCharts();
    renderReviews();
}

// Export function for use in Python integration
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { loadRealData };
}