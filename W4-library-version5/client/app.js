/**
 * Library Management System - REST API Client
 * 
 * Client-Server Architecture:
 * - Client: Single Page Application (SPA) with vanilla JavaScript
 * - Server: REST API (running on separate port)
 * - Communication: HTTP requests with JSON payload
 * - Authentication: JWT Token (stored in localStorage)
 * 
 * REST Principles Applied:
 * - Stateless: Token sent with every request
 * - Uniform Interface: HTTP methods (GET, POST, PUT, DELETE)
 * - Resource-based: Clear URL structure
 * - Cacheable: Client respects cache headers and uses conditional requests
 */

// Configuration
const API_BASE_URL = 'http://localhost:5000/api';
let currentPage = {
    books: 1,
    borrowRecords: 1
};

// ============================================================
// CACHE MANAGEMENT
// ============================================================

/**
 * In-memory cache store for API responses
 * Cache structure: { url: { data: {...}, etag: "...", timestamp: ... } }
 * 
 * REST Principle - Cacheable:
 * Client caches responses để giảm số lượng request và tăng hiệu năng
 */
const apiCache = new Map();

/**
 * Get cached response nếu còn valid
 */
function getCachedResponse(url, maxAge = 60) {
    const cached = apiCache.get(url);
    if (!cached) return null;
    
    const age = (Date.now() - cached.timestamp) / 1000; // seconds
    if (age > maxAge) {
        // Cache expired
        apiCache.delete(url);
        return null;
    }
    
    return cached;
}

/**
 * Save response to cache
 */
function setCachedResponse(url, data, etag) {
    apiCache.set(url, {
        data: data,
        etag: etag,
        timestamp: Date.now()
    });
}

/**
 * Clear cache (call after mutations)
 */
function clearCache(pattern = null) {
    if (!pattern) {
        apiCache.clear();
        console.log('🗑️ Cache cleared');
        updateCacheCount();
        return;
    }
    
    // Clear specific pattern
    for (const [key] of apiCache) {
        if (key.includes(pattern)) {
            apiCache.delete(key);
        }
    }
    console.log(`🗑️ Cache cleared for pattern: ${pattern}`);
    updateCacheCount();
}

/**
 * Update cache count display
 */
function updateCacheCount() {
    const countElement = document.getElementById('cacheCount');
    if (countElement) {
        countElement.textContent = apiCache.size;
    }
}

/**
 * Show cache status modal
 */
document.addEventListener('DOMContentLoaded', () => {
    const cacheBtn = document.getElementById('cacheInfoBtn');
    if (cacheBtn) {
        cacheBtn.addEventListener('click', () => {
            let cacheInfo = '<h3>📊 Cache Status</h3>';
            cacheInfo += `<p><strong>Total cached items:</strong> ${apiCache.size}</p>`;
            
            if (apiCache.size > 0) {
                cacheInfo += '<table style="width: 100%; margin-top: 10px; border-collapse: collapse;">';
                cacheInfo += '<thead><tr><th style="border: 1px solid #ddd; padding: 8px;">URL</th><th style="border: 1px solid #ddd; padding: 8px;">ETag</th><th style="border: 1px solid #ddd; padding: 8px;">Age (s)</th></tr></thead><tbody>';
                
                for (const [url, cache] of apiCache) {
                    const age = Math.floor((Date.now() - cache.timestamp) / 1000);
                    const shortUrl = url.replace(API_BASE_URL, '');
                    cacheInfo += `<tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">${shortUrl}</td>
                        <td style="border: 1px solid #ddd; padding: 8px; font-size: 11px; font-family: monospace;">${cache.etag ? cache.etag.substring(0, 12) + '...' : 'N/A'}</td>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${age}s</td>
                    </tr>`;
                }
                
                cacheInfo += '</tbody></table>';
            } else {
                cacheInfo += '<p style="color: #666;">No cached items</p>';
            }
            
            showAlert(cacheInfo, 'info', 10000);
        });
    }
});

// ============================================================
// AUTHENTICATION
// ============================================================

/**
 * Get JWT token from localStorage
 * REST Principle: Stateless - Client stores and manages token
 */
function getToken() {
    return localStorage.getItem('jwt_token');
}

/**
 * Set JWT token to localStorage
 */
function setToken(token) {
    localStorage.setItem('jwt_token', token);
}

/**
 * Remove JWT token from localStorage
 */
function removeToken() {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('username');
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return !!getToken();
}

/**
 * Login handler
 */
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Store token (Client-side state)
            setToken(result.data.token);
            localStorage.setItem('username', result.data.username);
            
            // Show token
            document.getElementById('tokenValue').textContent = result.data.token;
            document.getElementById('tokenDisplay').style.display = 'block';
            
            showAlert('Login successful! Token saved in localStorage.', 'success');
            
            // Switch to dashboard after 1.5 seconds
            setTimeout(() => {
                switchView('dashboard');
                loadDashboard();
            }, 1500);
        } else {
            showAlert(result.message || 'Login failed', 'error');
        }
    } catch (error) {
        showAlert('Connection error: ' + error.message, 'error');
    }
});

/**
 * Logout handler
 */
document.getElementById('logoutBtn').addEventListener('click', () => {
    // Remove token from client
    removeToken();
    
    // Clear all cached data
    clearCache();
    
    showAlert('Logged out successfully!', 'success');
    
    // Hide main nav and show login view
    document.getElementById('mainNav').style.display = 'none';
    switchView('login');
});

// ============================================================
// HTTP REQUEST HELPER
// ============================================================

/**
 * Make authenticated API request with cache support
 * 
 * REST Principle - Cacheable:
 * - Sử dụng cached data nếu available
 * - Gửi conditional request (If-None-Match) với ETag
 * - Xử lý 304 Not Modified response
 * - Cache fresh responses
 */
async function apiRequest(endpoint, options = {}) {
    const token = getToken();
    const fullUrl = `${API_BASE_URL}${endpoint}`;
    
    const config = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    };
    
    // Add Bearer token if authenticated
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // For GET requests, check cache and add conditional headers
    if (!options.method || options.method === 'GET') {
        const cached = getCachedResponse(fullUrl);
        
        if (cached) {
            // Add If-None-Match header for conditional request
            if (cached.etag) {
                config.headers['If-None-Match'] = cached.etag;
                console.log(`📤 Conditional GET: ${endpoint} (ETag: ${cached.etag})`);
            }
        }
    }
    
    try {
        const response = await fetch(fullUrl, config);
        
        // Handle 304 Not Modified - use cached data
        if (response.status === 304) {
            const cached = getCachedResponse(fullUrl);
            if (cached) {
                console.log(`✅ 304 Not Modified: Using cached data for ${endpoint}`);
                return { response: { status: 200, ok: true }, result: cached.data };
            }
        }
        
        const result = await response.json();
        
        // Handle authentication errors
        if (response.status === 401) {
            showAlert('Session expired. Please login again.', 'error');
            removeToken();
            clearCache(); // Clear cache on logout
            switchView('login');
            return null;
        }
        
        // Cache successful GET responses
        if (response.ok && (!options.method || options.method === 'GET')) {
            const etag = response.headers.get('ETag');
            const cacheControl = response.headers.get('Cache-Control');
            
            if (etag) {
                // Extract max-age from Cache-Control header
                let maxAge = 60; // default
                if (cacheControl) {
                    const match = cacheControl.match(/max-age=(\d+)/);
                    if (match) {
                        maxAge = parseInt(match[1]);
                    }
                }
                
                setCachedResponse(fullUrl, result, etag);
                console.log(`💾 Cached: ${endpoint} (max-age: ${maxAge}s, ETag: ${etag})`);
                updateCacheCount(); // Update UI
            }
        }
        
        // Clear relevant cache after mutations (POST, PUT, DELETE)
        if (options.method && ['POST', 'PUT', 'DELETE'].includes(options.method)) {
            if (endpoint.includes('/books')) {
                clearCache('/books');
                clearCache('/statistics');
            } else if (endpoint.includes('/borrow-records')) {
                clearCache('/borrow-records');
                clearCache('/books');
                clearCache('/statistics');
            }
        }
        
        return { response, result };
    } catch (error) {
        showAlert('Connection error: ' + error.message, 'error');
        return null;
    }
}

// ============================================================
// VIEW MANAGEMENT
// ============================================================

/**
 * Switch between views
 */
function switchView(viewName) {
    // Hide all views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    
    // Show selected view
    const selectedView = document.getElementById(viewName + 'View');
    if (selectedView) {
        selectedView.classList.add('active');
    }
    
    // Update navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = document.querySelector(`[data-view="${viewName}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // Show/hide main navigation
    if (viewName === 'login') {
        document.getElementById('mainNav').style.display = 'none';
    } else {
        document.getElementById('mainNav').style.display = 'flex';
    }
    
    // Load data for specific views
    if (viewName === 'books') {
        loadBooks();
    } else if (viewName === 'borrow-records') {
        loadBorrowRecords();
    }
}

// Navigation buttons
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const view = e.target.dataset.view;
        switchView(view);
    });
});

// ============================================================
// DASHBOARD
// ============================================================

async function loadDashboard() {
    const data = await apiRequest('/statistics');
    
    if (data && data.result.success) {
        const stats = data.result.data;
        
        document.getElementById('statsGrid').innerHTML = `
            <div class="stat-card">
                <div class="stat-icon">📚</div>
                <div class="stat-value">${stats.books.total_titles}</div>
                <div class="stat-label">Total Book Titles</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📖</div>
                <div class="stat-value">${stats.books.total_copies}</div>
                <div class="stat-label">Total Copies</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">✅</div>
                <div class="stat-value">${stats.books.available_copies}</div>
                <div class="stat-label">Available Copies</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📤</div>
                <div class="stat-value">${stats.books.borrowed_copies}</div>
                <div class="stat-label">Borrowed Copies</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📝</div>
                <div class="stat-value">${stats.borrow_records.total}</div>
                <div class="stat-label">Total Records</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🔄</div>
                <div class="stat-value">${stats.borrow_records.returned}</div>
                <div class="stat-label">Returned Books</div>
            </div>
        `;
    }
}

// ============================================================
// BOOKS MANAGEMENT
// ============================================================

async function loadBooks(page = 1) {
    currentPage.books = page;
    
    const data = await apiRequest(`/books?page=${page}&per_page=10`);
    
    if (data && data.result.success) {
        const books = data.result.data.books;
        const pagination = data.result.data.pagination;
        
        // Render books table
        const tbody = document.getElementById('booksTableBody');
        tbody.innerHTML = books.map(book => `
            <tr>
                <td>${book.id}</td>
                <td>${book.title}</td>
                <td>${book.author}</td>
                <td>${book.isbn}</td>
                <td>${book.quantity}</td>
                <td>${book.available}</td>
                <td>
                    <button class="btn-icon" onclick="editBook(${book.id})" title="Edit">
                        ✏️
                    </button>
                    <button class="btn-icon" onclick="deleteBook(${book.id})" title="Delete">
                        🗑️
                    </button>
                </td>
            </tr>
        `).join('');
        
        // Render pagination
        renderPagination('books', pagination);
    }
}

function showAddBookForm() {
    document.getElementById('bookFormTitle').textContent = 'Add New Book';
    document.getElementById('bookForm').reset();
    document.getElementById('bookId').value = '';
    document.getElementById('bookFormContainer').style.display = 'block';
}

function hideBookForm() {
    document.getElementById('bookFormContainer').style.display = 'none';
}

async function editBook(bookId) {
    const data = await apiRequest(`/books/${bookId}`);
    
    if (data && data.result.success) {
        const book = data.result.data;
        
        document.getElementById('bookFormTitle').textContent = 'Edit Book';
        document.getElementById('bookId').value = book.id;
        document.getElementById('bookTitle').value = book.title;
        document.getElementById('bookAuthor').value = book.author;
        document.getElementById('bookIsbn').value = book.isbn;
        document.getElementById('bookQuantity').value = book.quantity;
        document.getElementById('bookFormContainer').style.display = 'block';
    }
}

document.getElementById('bookForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const bookId = document.getElementById('bookId').value;
    const bookData = {
        title: document.getElementById('bookTitle').value,
        author: document.getElementById('bookAuthor').value,
        isbn: document.getElementById('bookIsbn').value,
        quantity: parseInt(document.getElementById('bookQuantity').value)
    };
    
    let data;
    if (bookId) {
        // Update existing book (PUT)
        data = await apiRequest(`/books/${bookId}`, {
            method: 'PUT',
            body: JSON.stringify(bookData)
        });
    } else {
        // Create new book (POST)
        data = await apiRequest('/books', {
            method: 'POST',
            body: JSON.stringify(bookData)
        });
    }
    
    if (data && data.result.success) {
        showAlert(data.result.message, 'success');
        hideBookForm();
        loadBooks(currentPage.books);
    } else if (data) {
        showAlert(data.result.message || 'Operation failed', 'error');
    }
});

async function deleteBook(bookId) {
    if (!confirm('Are you sure you want to delete this book?')) {
        return;
    }
    
    const data = await apiRequest(`/books/${bookId}`, {
        method: 'DELETE'
    });
    
    if (data && data.result.success) {
        showAlert(data.result.message, 'success');
        loadBooks(currentPage.books);
    } else if (data) {
        showAlert(data.result.message || 'Delete failed', 'error');
    }
}

// ============================================================
// BORROW RECORDS MANAGEMENT
// ============================================================

async function loadBorrowRecords(page = 1) {
    currentPage.borrowRecords = page;
    
    const status = document.getElementById('statusFilter').value;
    let url = `/borrow-records?page=${page}&per_page=10`;
    if (status) {
        url += `&status=${status}`;
    }
    
    const data = await apiRequest(url);
    
    if (data && data.result.success) {
        const records = data.result.data.records;
        const pagination = data.result.data.pagination;
        
        // Render records table
        const tbody = document.getElementById('borrowRecordsTableBody');
        tbody.innerHTML = records.map(record => `
            <tr>
                <td>${record.id}</td>
                <td>${record.book_title}</td>
                <td>${record.borrower_name}</td>
                <td>${record.borrower_email}</td>
                <td>${new Date(record.borrow_date).toLocaleDateString()}</td>
                <td>${record.return_date ? new Date(record.return_date).toLocaleDateString() : '-'}</td>
                <td>
                    <span class="badge badge-${record.status}">
                        ${record.status}
                    </span>
                </td>
                <td>
                    ${record.status === 'borrowed' ? 
                        `<button class="btn-icon" onclick="returnBook(${record.id})" title="Return">
                            ↩️
                        </button>` : 
                        '-'
                    }
                </td>
            </tr>
        `).join('');
        
        // Render pagination
        renderPagination('borrowRecords', pagination);
    }
}

async function showBorrowBookForm() {
    // Load available books
    const data = await apiRequest('/books?available_only=true&per_page=100');
    
    if (data && data.result.success) {
        const books = data.result.data.books;
        
        const select = document.getElementById('borrowBookId');
        select.innerHTML = '<option value="">-- Select a book --</option>' +
            books.map(book => `
                <option value="${book.id}">
                    ${book.title} - ${book.author} (Available: ${book.available})
                </option>
            `).join('');
        
        document.getElementById('borrowFormContainer').style.display = 'block';
    }
}

function hideBorrowForm() {
    document.getElementById('borrowFormContainer').style.display = 'none';
}

document.getElementById('borrowForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const borrowData = {
        book_id: parseInt(document.getElementById('borrowBookId').value),
        borrower_name: document.getElementById('borrowerName').value,
        borrower_email: document.getElementById('borrowerEmail').value
    };
    
    const data = await apiRequest('/borrow-records', {
        method: 'POST',
        body: JSON.stringify(borrowData)
    });
    
    if (data && data.result.success) {
        showAlert(data.result.message, 'success');
        hideBorrowForm();
        loadBorrowRecords(currentPage.borrowRecords);
        // Also refresh dashboard if visible
        if (document.getElementById('dashboardView').classList.contains('active')) {
            loadDashboard();
        }
    } else if (data) {
        showAlert(data.result.message || 'Borrow failed', 'error');
    }
});

async function returnBook(recordId) {
    if (!confirm('Confirm book return?')) {
        return;
    }
    
    const data = await apiRequest(`/borrow-records/${recordId}/return`, {
        method: 'PUT'
    });
    
    if (data && data.result.success) {
        showAlert(data.result.message, 'success');
        loadBorrowRecords(currentPage.borrowRecords);
    } else if (data) {
        showAlert(data.result.message || 'Return failed', 'error');
    }
}

// ============================================================
// PAGINATION
// ============================================================

function renderPagination(type, pagination) {
    const container = document.getElementById(`${type}Pagination`);
    
    if (pagination.pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '<div class="pagination-buttons">';
    
    // Previous button
    if (pagination.has_prev) {
        html += `<button class="btn-page" onclick="load${type === 'books' ? 'Books' : 'BorrowRecords'}(${pagination.page - 1})">
            ← Previous
        </button>`;
    }
    
    // Page info
    html += `<span class="page-info">Page ${pagination.page} of ${pagination.pages}</span>`;
    
    // Next button
    if (pagination.has_next) {
        html += `<button class="btn-page" onclick="load${type === 'books' ? 'Books' : 'BorrowRecords'}(${pagination.page + 1})">
            Next →
        </button>`;
    }
    
    html += '</div>';
    container.innerHTML = html;
}

// ============================================================
// ALERT SYSTEM
// ============================================================

function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.getElementById('alertContainer');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    
    // Allow HTML for cache info display
    if (type === 'info' && message.includes('<')) {
        alertDiv.innerHTML = message;
    } else {
        alertDiv.textContent = message;
    }
    
    alertContainer.appendChild(alertDiv);
    
    // Auto remove after duration
    setTimeout(() => {
        alertDiv.remove();
    }, duration);
}

// ============================================================
// INITIALIZATION
// ============================================================

// Check authentication on page load
window.addEventListener('DOMContentLoaded', () => {
    if (isAuthenticated()) {
        switchView('dashboard');
        loadDashboard();
    } else {
        switchView('login');
    }
});
