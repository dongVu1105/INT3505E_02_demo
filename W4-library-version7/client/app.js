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

// Debounce timer for search
let searchDebounceTimer = null;

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
// AUTHENTICATION - TOKEN MANAGEMENT IN LOCAL STORAGE
// ============================================================

/**
 * Get JWT token from localStorage
 * 
 * REST Principle: Stateless - Client stores and manages token
 * 
 * Token được lưu trữ tại: localStorage với key 'jwt_token'
 * - localStorage là bộ nhớ lưu trữ trên trình duyệt
 * - Token sẽ tồn tại ngay cả khi đóng trình duyệt
 * - Token chỉ bị xóa khi user logout hoặc hết hạn
 */
function getToken() {
    return localStorage.getItem('jwt_token');
}

/**
 * Set JWT token to localStorage
 * 
 * Lưu token vào localStorage của trình duyệt
 * @param {string} token - JWT token nhận được từ server
 */
function setToken(token) {
    localStorage.setItem('jwt_token', token);
    console.log('✅ Token đã được lưu vào localStorage');
    console.log('📍 Location: localStorage["jwt_token"]');
}

/**
 * Remove JWT token from localStorage
 * 
 * Xóa token khỏi localStorage khi logout hoặc token hết hạn
 */
function removeToken() {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('username');
    console.log('🗑️ Token đã được xóa khỏi localStorage');
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
            // Store token in localStorage (Lưu token vào localStorage)
            // Token sẽ được dùng cho các request tiếp theo
            setToken(result.data.token);
            localStorage.setItem('username', result.data.username);
            
            // Show token to user
            document.getElementById('tokenValue').textContent = result.data.token;
            document.getElementById('tokenDisplay').style.display = 'block';
            
            showAlert('✅ Login successful! Token has been saved to localStorage.', 'success');
            console.log('📦 Token info:', {
                token: result.data.token.substring(0, 20) + '...',
                username: result.data.username,
                storage: 'localStorage',
                key: 'jwt_token'
            });
            
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
    // Remove token from localStorage
    removeToken();
    
    // Clear all cached data
    clearCache();
    
    showAlert('✅ Logged out successfully! Token removed from localStorage.', 'success');
    console.log('🚪 User logged out - localStorage cleared');
    
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
            showAlert('⚠️ Session expired. Please login again.', 'error');
            console.log('🔒 Token expired or invalid - clearing localStorage');
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

/**
 * Build query string for books with all filters
 */
function getBooksQueryParams(page = 1) {
    const params = new URLSearchParams();
    params.append('page', page);
    params.append('per_page', 10);
    
    // Search filters
    const title = document.getElementById('searchTitle')?.value.trim();
    const author = document.getElementById('searchAuthor')?.value.trim();
    const isbn = document.getElementById('searchISBN')?.value.trim();
    
    if (title) params.append('title', title);
    if (author) params.append('author', author);
    if (isbn) params.append('isbn', isbn);
    
    // Available only filter
    const availableOnly = document.getElementById('availableOnlyFilter')?.checked;
    if (availableOnly) params.append('available_only', 'true');
    
    // Sorting
    const sortBy = document.getElementById('sortByBooks')?.value || 'created_at';
    const sortOrder = document.getElementById('sortOrderBooks')?.value || 'desc';
    params.append('sort_by', sortBy);
    params.append('sort_order', sortOrder);
    
    return params.toString();
}

/**
 * Clear all books filters
 */
function clearBooksFilters() {
    document.getElementById('searchTitle').value = '';
    document.getElementById('searchAuthor').value = '';
    document.getElementById('searchISBN').value = '';
    document.getElementById('availableOnlyFilter').checked = false;
    document.getElementById('sortByBooks').value = 'created_at';
    document.getElementById('sortOrderBooks').value = 'desc';
    loadBooks(1);
}

/**
 * Debounce search input
 */
function debounceSearch(type) {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        if (type === 'books') {
            loadBooks(1);
        } else if (type === 'borrowRecords') {
            loadBorrowRecords(1);
        }
    }, 500); // Wait 500ms after user stops typing
}

async function loadBooks(page = 1) {
    currentPage.books = page;
    
    const queryParams = getBooksQueryParams(page);
    const data = await apiRequest(`/books?${queryParams}`);
    
    if (data && data.result.success) {
        const books = data.result.data.books;
        const pagination = data.result.data.pagination;
        
        // Show result info
        showResultInfo('books', pagination);
        
        // Render books table
        const tbody = document.getElementById('booksTableBody');
        
        if (books.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px; color: #999;">
                        📚 No books found. ${pagination.total === 0 ? 'Try adjusting your filters.' : ''}
                    </td>
                </tr>
            `;
        } else {
            tbody.innerHTML = books.map(book => `
                <tr>
                    <td>${book.id}</td>
                    <td><strong>${book.title}</strong></td>
                    <td>${book.author}</td>
                    <td><code>${book.isbn}</code></td>
                    <td>${book.quantity}</td>
                    <td>
                        <span class="badge ${book.available > 0 ? 'badge-success' : 'badge-error'}">
                            ${book.available}
                        </span>
                    </td>
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
        }
        
        // Render pagination
        renderPagination('books', pagination);
    }
}

/**
 * Show result info (total count and current range)
 */
function showResultInfo(type, pagination) {
    const infoElement = document.getElementById(`${type}ResultInfo`);
    if (!infoElement) return;
    
    if (pagination.total === 0) {
        infoElement.innerHTML = '<p style="color: #999;">No results found</p>';
        return;
    }
    
    const start = (pagination.page - 1) * pagination.per_page + 1;
    const end = Math.min(pagination.page * pagination.per_page, pagination.total);
    
    infoElement.innerHTML = `
        <p>
            Showing <strong>${start}-${end}</strong> of <strong>${pagination.total}</strong> 
            ${type === 'books' ? 'books' : 'records'}
        </p>
    `;
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

/**
 * Build query string for borrow records with all filters
 */
function getBorrowRecordsQueryParams(page = 1) {
    const params = new URLSearchParams();
    params.append('page', page);
    params.append('per_page', 10);
    
    // Search filters
    const borrowerName = document.getElementById('searchBorrowerName')?.value.trim();
    const borrowerEmail = document.getElementById('searchBorrowerEmail')?.value.trim();
    
    if (borrowerName) params.append('borrower_name', borrowerName);
    if (borrowerEmail) params.append('borrower_email', borrowerEmail);
    
    // Status filter
    const status = document.getElementById('statusFilter')?.value;
    if (status) params.append('status', status);
    
    // Sorting
    const sortBy = document.getElementById('sortByBorrowRecords')?.value || 'borrow_date';
    const sortOrder = document.getElementById('sortOrderBorrowRecords')?.value || 'desc';
    params.append('sort_by', sortBy);
    params.append('sort_order', sortOrder);
    
    return params.toString();
}

/**
 * Clear all borrow records filters
 */
function clearBorrowRecordsFilters() {
    document.getElementById('searchBorrowerName').value = '';
    document.getElementById('searchBorrowerEmail').value = '';
    document.getElementById('statusFilter').value = '';
    document.getElementById('sortByBorrowRecords').value = 'borrow_date';
    document.getElementById('sortOrderBorrowRecords').value = 'desc';
    loadBorrowRecords(1);
}

async function loadBorrowRecords(page = 1) {
    currentPage.borrowRecords = page;
    
    const queryParams = getBorrowRecordsQueryParams(page);
    const data = await apiRequest(`/borrow-records?${queryParams}`);
    
    if (data && data.result.success) {
        const records = data.result.data.records;
        const pagination = data.result.data.pagination;
        
        // Show result info
        showResultInfo('borrowRecords', pagination);
        
        // Render records table
        const tbody = document.getElementById('borrowRecordsTableBody');
        
        if (records.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 40px; color: #999;">
                        📖 No borrow records found. ${pagination.total === 0 ? 'Try adjusting your filters.' : ''}
                    </td>
                </tr>
            `;
        } else {
            tbody.innerHTML = records.map(record => `
                <tr>
                    <td>${record.id}</td>
                    <td><strong>${record.book_title}</strong></td>
                    <td>${record.borrower_name}</td>
                    <td>${record.borrower_email}</td>
                    <td>${new Date(record.borrow_date).toLocaleDateString('vi-VN')}</td>
                    <td>${record.return_date ? new Date(record.return_date).toLocaleDateString('vi-VN') : '-'}</td>
                    <td>
                        <span class="badge badge-${record.status}">
                            ${record.status === 'borrowed' ? '📤 Borrowed' : '✅ Returned'}
                        </span>
                    </td>
                    <td>
                        ${record.status === 'borrowed' ? 
                            `<button class="btn-icon" onclick="returnBook(${record.id})" title="Return Book">
                                ↩️
                            </button>` : 
                            '<span style="color: #999;">-</span>'
                        }
                    </td>
                </tr>
            `).join('');
        }
        
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
    
    let html = '<div class="pagination-container">';
    
    // Page navigation buttons
    html += '<div class="pagination-buttons">';
    
    // First page button
    if (pagination.page > 1) {
        html += `<button class="btn-page" onclick="load${type === 'books' ? 'Books' : 'BorrowRecords'}(1)" title="First page">
            ⏮️
        </button>`;
    }
    
    // Previous button
    if (pagination.has_prev) {
        html += `<button class="btn-page" onclick="load${type === 'books' ? 'Books' : 'BorrowRecords'}(${pagination.prev_page})">
            ← Previous
        </button>`;
    } else {
        html += `<button class="btn-page" disabled>← Previous</button>`;
    }
    
    // Page numbers
    html += renderPageNumbers(type, pagination);
    
    // Next button
    if (pagination.has_next) {
        html += `<button class="btn-page" onclick="load${type === 'books' ? 'Books' : 'BorrowRecords'}(${pagination.next_page})">
            Next →
        </button>`;
    } else {
        html += `<button class="btn-page" disabled>Next →</button>`;
    }
    
    // Last page button
    if (pagination.page < pagination.pages) {
        html += `<button class="btn-page" onclick="load${type === 'books' ? 'Books' : 'BorrowRecords'}(${pagination.pages})" title="Last page">
            ⏭️
        </button>`;
    }
    
    html += '</div>'; // End pagination-buttons
    
    // Page info
    html += `<div class="page-info">
        Page <strong>${pagination.page}</strong> of <strong>${pagination.pages}</strong>
    </div>`;
    
    html += '</div>'; // End pagination-container
    
    container.innerHTML = html;
}

/**
 * Render page number buttons (with ellipsis for large page counts)
 */
function renderPageNumbers(type, pagination) {
    let html = '';
    const currentPage = pagination.page;
    const totalPages = pagination.pages;
    const maxButtons = 5; // Maximum page buttons to show
    
    if (totalPages <= maxButtons + 2) {
        // Show all pages
        for (let i = 1; i <= totalPages; i++) {
            html += renderPageButton(type, i, currentPage);
        }
    } else {
        // Show with ellipsis
        const leftEllipsis = currentPage > 3;
        const rightEllipsis = currentPage < totalPages - 2;
        
        // Always show first page
        html += renderPageButton(type, 1, currentPage);
        
        if (leftEllipsis) {
            html += '<span class="page-ellipsis">...</span>';
        }
        
        // Show pages around current page
        let startPage = Math.max(2, currentPage - 1);
        let endPage = Math.min(totalPages - 1, currentPage + 1);
        
        if (currentPage <= 3) {
            endPage = Math.min(totalPages - 1, 4);
        }
        if (currentPage >= totalPages - 2) {
            startPage = Math.max(2, totalPages - 3);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            html += renderPageButton(type, i, currentPage);
        }
        
        if (rightEllipsis) {
            html += '<span class="page-ellipsis">...</span>';
        }
        
        // Always show last page
        html += renderPageButton(type, totalPages, currentPage);
    }
    
    return html;
}

/**
 * Render a single page button
 */
function renderPageButton(type, pageNum, currentPage) {
    const isActive = pageNum === currentPage;
    const loadFunction = type === 'books' ? 'Books' : 'BorrowRecords';
    
    return `<button class="btn-page ${isActive ? 'active' : ''}" 
                    onclick="load${loadFunction}(${pageNum})"
                    ${isActive ? 'disabled' : ''}>
        ${pageNum}
    </button>`;
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
