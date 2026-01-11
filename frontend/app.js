/**
 * Python Learning App - Frontend JavaScript
 */

// API Base URL
const API_BASE_URL = '/api';

// State management
const state = {
    username: null,  // Current logged in username
    isLoggedIn: false,  // Authentication status
    currentTerm: null,
    currentLevel: 1,
    maxLevel: 3,
    isLoading: false,
    currentPractice: null,  // Current practice problem data
    monacoEditor: null,  // Monaco Editor instance
    loadedRelatedKeywords: new Set(),  // Already loaded related keywords
    activityChartInstance: null,  // Chart.js instance for activity
    keywordsChartInstance: null,  // Chart.js instance for keywords
};

// DOM Elements
const elements = {
    searchInput: null,
    searchBtn: null,
    explanationCard: null,
    termTitle: null,
    explanationContent: null,
    levelIndicator: null,
    understandBtn: null,
    moreDetailBtn: null,
    welcomeMessage: null,
    successMessage: null,
    errorMessage: null,
    errorText: null,
    retryBtn: null,
    historyList: null,
    refreshHistoryBtn: null,
    profileSummary: null,
    statsBadge: null,
    profileModal: null,
    profileContent: null,
    modalClose: null,
    loadingOverlay: null,
    // History modal elements
    historyModal: null,
    historyModalTitle: null,
    historyModalMeta: null,
    historyModalContent: null,
    historyModalClose: null,
    // Practice mode elements
    practiceBtn: null,
    practiceCard: null,
    practiceTitle: null,
    practiceProblem: null,
    practiceCode: null,
    checkAnswerBtn: null,
    showHintBtn: null,
    showAnswerBtn: null,
    practiceHint: null,
    practiceAnswer: null,
    practiceResult: null,
    closePracticeBtn: null,
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeElements();
    initializeTheme();
    setupEventListeners();
    configureMarked();

    // Check if user is logged in
    if (checkAuth()) {
        // User is logged in, show main app
        hideLoginScreen();
        loadInitialData();
        initializeMonacoEditor();
    } else {
        // Show login screen
        showLoginScreen();
    }
});

// ========== Authentication Functions ==========

// Check if user is logged in (from localStorage)
function checkAuth() {
    const username = localStorage.getItem('username');
    if (username) {
        state.username = username;
        state.isLoggedIn = true;
        return true;
    }
    return false;
}

// Login function
async function login(username) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim() })
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'ログインに失敗しました' }));
        throw new Error(error.detail || 'ログインに失敗しました');
    }

    const data = await response.json();

    // Store in localStorage
    localStorage.setItem('username', data.username);
    state.username = data.username;
    state.isLoggedIn = true;

    return data;
}

// Logout function
function logout() {
    localStorage.removeItem('username');
    state.username = null;
    state.isLoggedIn = false;

    // Show login screen
    showLoginScreen();

    // Clear any loaded data
    state.currentTerm = null;
    state.currentLevel = 1;
    state.currentPractice = null;
    state.loadedRelatedKeywords.clear();
}

// Show login screen
function showLoginScreen() {
    document.getElementById('login-screen').hidden = false;
    document.getElementById('app-container').hidden = true;
}

// Hide login screen and show app
function hideLoginScreen() {
    document.getElementById('login-screen').hidden = true;
    document.getElementById('app-container').hidden = false;
    updateUsernameDisplay();
}

// Update username display in header
function updateUsernameDisplay() {
    const usernameDisplay = document.getElementById('username-display');
    if (usernameDisplay && state.username) {
        usernameDisplay.textContent = state.username;
    }
}

// Handle login form submission
async function handleLoginSubmit(e) {
    e.preventDefault();

    const usernameInput = document.getElementById('username-input');
    const loginBtn = document.getElementById('login-btn');
    const loginError = document.getElementById('login-error');
    const errorText = document.getElementById('login-error-text');

    const username = usernameInput.value.trim();

    if (!username) {
        usernameInput.focus();
        return;
    }

    // Show loading
    loginBtn.disabled = true;
    loginBtn.querySelector('.btn-text').hidden = true;
    loginBtn.querySelector('.btn-loading').hidden = false;
    loginError.hidden = true;

    try {
        const result = await login(username);

        // Hide login screen
        hideLoginScreen();

        // Show welcome notification
        if (result.is_new_user) {
            showNotification('アカウントを作成しました！学習を始めましょう！', 'success');
        } else {
            showNotification(`おかえりなさい、${result.username}さん！`, 'success');
        }

        // Load user data
        await loadInitialData();
        initializeMonacoEditor();

    } catch (error) {
        errorText.textContent = error.message;
        loginError.hidden = false;
    } finally {
        loginBtn.disabled = false;
        loginBtn.querySelector('.btn-text').hidden = false;
        loginBtn.querySelector('.btn-loading').hidden = true;
    }
}

// Handle logout
function handleLogout() {
    if (confirm('ログアウトしますか？')) {
        logout();
    }
}

// Show notification toast
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `toast-notification toast-${type}`;
    notification.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
            <span class="toast-message">${message}</span>
        </div>
    `;
    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Cache DOM elements
function initializeElements() {
    elements.searchInput = document.getElementById('search-input');
    elements.searchBtn = document.getElementById('search-btn');
    elements.explanationCard = document.getElementById('explanation-card');
    elements.termTitle = document.getElementById('term-title');
    elements.explanationContent = document.getElementById('explanation-content');
    elements.levelIndicator = document.getElementById('level-indicator');
    elements.understandBtn = document.getElementById('understand-btn');
    elements.moreDetailBtn = document.getElementById('more-detail-btn');
    elements.welcomeMessage = document.getElementById('welcome-message');
    elements.successMessage = document.getElementById('success-message');
    elements.errorMessage = document.getElementById('error-message');
    elements.errorText = document.getElementById('error-text');
    elements.retryBtn = document.getElementById('retry-btn');
    elements.historyList = document.getElementById('history-list');
    elements.refreshHistoryBtn = document.getElementById('refresh-history');
    elements.clearHistoryBtn = document.getElementById('clear-history');
    elements.profileSummary = document.getElementById('profile-summary');
    elements.statsBadge = document.getElementById('stats-badge');
    elements.profileModal = document.getElementById('profile-modal');
    elements.profileContent = document.getElementById('profile-content');
    elements.modalClose = document.getElementById('modal-close');
    elements.loadingOverlay = document.getElementById('loading-overlay');
    // History modal elements
    elements.historyModal = document.getElementById('history-modal');
    elements.historyModalTitle = document.getElementById('history-modal-title');
    elements.historyModalMeta = document.getElementById('history-modal-meta');
    elements.historyModalContent = document.getElementById('history-modal-content');
    elements.historyModalClose = document.getElementById('history-modal-close');
    // Practice mode elements
    elements.practiceBtn = document.getElementById('practice-btn');
    elements.practiceCard = document.getElementById('practice-card');
    elements.practiceTitle = document.getElementById('practice-title');
    elements.practiceProblem = document.getElementById('practice-problem');
    elements.practiceCodeEditor = document.getElementById('practice-code-editor');
    elements.checkAnswerBtn = document.getElementById('check-answer-btn');
    elements.showHintBtn = document.getElementById('show-hint-btn');
    elements.showAnswerBtn = document.getElementById('show-answer-btn');
    elements.practiceHint = document.getElementById('practice-hint');
    elements.practiceAnswer = document.getElementById('practice-answer');
    elements.practiceResult = document.getElementById('practice-result');
    elements.closePracticeBtn = document.getElementById('close-practice-btn');
    // Related keywords elements
    elements.relatedKeywords = document.getElementById('related-keywords');
    elements.relatedKeywordsList = document.getElementById('related-keywords-list');
    elements.additionalExplanations = document.getElementById('additional-explanations');
    // Dashboard elements
    elements.openDashboardBtn = document.getElementById('open-dashboard-btn');
    elements.closeDashboardBtn = document.getElementById('close-dashboard-btn');
    elements.dashboardSection = document.getElementById('dashboard-section');
    elements.activityChart = document.getElementById('activity-chart');
    elements.keywordsChart = document.getElementById('keywords-chart');
    elements.recommendationsList = document.getElementById('recommendations-list');
    elements.totalLearned = document.getElementById('total-learned');
    elements.totalSearches = document.getElementById('total-searches');
    elements.studyDays = document.getElementById('study-days');
    elements.avgSearches = document.getElementById('avg-searches');
    // Theme toggle elements
    elements.themeToggle = document.getElementById('theme-toggle');
    // Mobile menu elements
    elements.mobileMenuBtn = document.getElementById('mobile-menu-btn');
    elements.sidebarOverlay = document.getElementById('sidebar-overlay');
    elements.sidebarCloseBtn = document.getElementById('sidebar-close-btn');
    elements.sidebar = document.getElementById('sidebar');
    // Progress bar elements
    elements.progressContainer = document.getElementById('progress-container');
    elements.progressStats = document.getElementById('progress-stats');
    elements.progressBarFill = document.getElementById('progress-bar-fill');
    elements.milestone1 = document.getElementById('milestone-1');
    elements.milestone2 = document.getElementById('milestone-2');
    elements.milestone3 = document.getElementById('milestone-3');
    elements.milestone4 = document.getElementById('milestone-4');
    // Keyword index elements (now in glossary)
    elements.learnedCount = document.getElementById('learned-count');
    elements.totalKeywordCount = document.getElementById('total-keyword-count');
    elements.keywordIndexToc = document.getElementById('keyword-index-toc');
    // Logo home link
    elements.logoHome = document.getElementById('logo-home');
    // Glossary elements
    elements.openGlossaryBtn = document.getElementById('open-glossary-btn');
    elements.closeGlossaryBtn = document.getElementById('close-glossary-btn');
    elements.glossarySection = document.getElementById('glossary-section');
    // Learning Center elements
    elements.openLearningCenterBtn = document.getElementById('open-learning-center-btn');
    elements.closeLearningCenterBtn = document.getElementById('close-learning-center-btn');
    elements.learningCenterSection = document.getElementById('learning-center-section');
    elements.streakDays = document.getElementById('streak-days');
    elements.learningPathsGrid = document.getElementById('learning-paths-grid');
    elements.activePaths = document.getElementById('active-paths');
    elements.earnedBadgesCount = document.getElementById('earned-badges-count');
    elements.totalBadgesCount = document.getElementById('total-badges-count');
    elements.earnedBadgesGrid = document.getElementById('earned-badges-grid');
    elements.lockedBadgesGrid = document.getElementById('locked-badges-grid');
    elements.reviewDueList = document.getElementById('review-due-list');
    elements.reviewUpcomingList = document.getElementById('review-upcoming-list');
    elements.practiceTotal = document.getElementById('practice-total');
    elements.practiceCorrect = document.getElementById('practice-correct');
    elements.practiceAccuracy = document.getElementById('practice-accuracy');
    elements.practiceHistoryList = document.getElementById('practice-history-list');
    elements.codeHistoryList = document.getElementById('code-history-list');
}

// Configure marked.js for markdown rendering
function configureMarked() {
    marked.setOptions({
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return hljs.highlightAuto(code).value;
        },
        breaks: true,
        gfm: true,
    });
}

// Initialize Monaco Editor
function initializeMonacoEditor() {
    require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });
    require(['vs/editor/editor.main'], function () {
        // Define custom theme to match example code colors
        monaco.editor.defineTheme('python-learning', {
            base: 'vs-dark',
            inherit: true,
            rules: [
                { token: 'comment', foreground: '64748b', fontStyle: 'italic' },
                { token: 'keyword', foreground: 'c084fc' },
                { token: 'string', foreground: '34d399' },
                { token: 'number', foreground: 'fbbf24' },
                { token: 'identifier', foreground: 'e2e8f0' },
            ],
            colors: {
                'editor.background': '#1e293b',
                'editor.foreground': '#e2e8f0',
                'editor.lineHighlightBackground': '#334155',
                'editor.selectionBackground': '#475569',
                'editorCursor.foreground': '#e2e8f0',
                'editorWhitespace.foreground': '#475569',
                'editorIndentGuide.activeBackground': '#475569',
                'editorIndentGuide.background': '#334155',
            }
        });

        state.monacoEditor = monaco.editor.create(elements.practiceCodeEditor, {
            value: '',
            language: 'python',
            theme: 'python-learning',
            fontSize: 14,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            insertSpaces: true,
            wordWrap: 'on',
            lineNumbers: 'on',
            roundedSelection: false,
            readOnly: false,
            cursorStyle: 'line',
            fontFamily: "'SF Mono', 'Fira Code', 'Fira Mono', Menlo, Monaco, 'Courier New', monospace",
            suggestOnTriggerCharacters: true,
            quickSuggestions: true,
            formatOnPaste: true,
            formatOnType: true,
        });
    });
}

// Setup event listeners
function setupEventListeners() {
    // Login form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLoginSubmit);
    }

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }

    // Search functionality
    elements.searchBtn.addEventListener('click', handleSearch);
    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });

    // Understanding buttons
    elements.understandBtn.addEventListener('click', handleUnderstand);
    elements.moreDetailBtn.addEventListener('click', handleMoreDetail);

    // Retry button
    elements.retryBtn.addEventListener('click', handleSearch);

    // History refresh and clear
    elements.refreshHistoryBtn.addEventListener('click', loadHistory);
    elements.clearHistoryBtn.addEventListener('click', handleClearHistory);

    // Profile modal
    elements.profileSummary.addEventListener('click', showProfileModal);
    elements.modalClose.addEventListener('click', hideProfileModal);
    elements.profileModal.addEventListener('click', (e) => {
        if (e.target === elements.profileModal) {
            hideProfileModal();
        }
    });

    // History modal
    elements.historyModalClose.addEventListener('click', hideHistoryModal);
    elements.historyModal.addEventListener('click', (e) => {
        if (e.target === elements.historyModal) {
            hideHistoryModal();
        }
    });

    // Practice mode
    elements.practiceBtn.addEventListener('click', handlePractice);
    elements.closePracticeBtn.addEventListener('click', hidePracticeCard);
    elements.checkAnswerBtn.addEventListener('click', checkPracticeAnswer);
    elements.showHintBtn.addEventListener('click', showPracticeHint);
    elements.showAnswerBtn.addEventListener('click', showPracticeAnswer);

    // Dashboard
    elements.openDashboardBtn.addEventListener('click', openDashboard);
    elements.closeDashboardBtn.addEventListener('click', closeDashboard);

    // Glossary
    elements.openGlossaryBtn.addEventListener('click', openGlossary);
    elements.closeGlossaryBtn.addEventListener('click', closeGlossary);

    // Learning Center
    elements.openLearningCenterBtn.addEventListener('click', openLearningCenter);
    elements.closeLearningCenterBtn.addEventListener('click', closeLearningCenter);

    // Learning Center tabs
    document.querySelectorAll('.lc-tab').forEach(tab => {
        tab.addEventListener('click', () => switchLearningCenterTab(tab.dataset.tab));
    });

    // Theme toggle
    elements.themeToggle.addEventListener('click', toggleTheme);

    // Mobile menu
    elements.mobileMenuBtn.addEventListener('click', openMobileSidebar);
    elements.sidebarOverlay.addEventListener('click', closeMobileSidebar);
    elements.sidebarCloseBtn.addEventListener('click', closeMobileSidebar);

    // Logo home link
    elements.logoHome.addEventListener('click', goHome);

    // Example term buttons
    document.querySelectorAll('.example-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            elements.searchInput.value = btn.dataset.term;
            handleSearch();
        });
    });

    // Keyboard shortcut: Escape to close modal/sidebar/sections
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!elements.profileModal.hidden) {
                hideProfileModal();
            }
            if (!elements.historyModal.hidden) {
                hideHistoryModal();
            }
            if (elements.sidebar.classList.contains('open')) {
                closeMobileSidebar();
            }
            if (!elements.dashboardSection.hidden) {
                closeDashboard();
            }
            if (!elements.glossarySection.hidden) {
                closeGlossary();
            }
            if (!elements.learningCenterSection.hidden) {
                closeLearningCenter();
            }
        }
    });
}

// Load initial data
async function loadInitialData() {
    await Promise.all([
        loadProfile(),
        loadHistory(),
    ]);
}

// API call helper
async function apiCall(endpoint, options = {}) {
    // Check authentication (except for login endpoint)
    if (!endpoint.startsWith('/auth/') && !state.isLoggedIn) {
        throw new Error('ログインが必要です');
    }

    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
    };

    // Add username header if logged in
    if (state.username) {
        headers['X-Username'] = state.username;
    }

    const defaultOptions = { headers };

    const response = await fetch(url, {
        ...defaultOptions,
        ...options,
        headers: { ...headers, ...(options.headers || {}) }
    });

    // Handle 401 Unauthorized - redirect to login
    if (response.status === 401) {
        logout();
        throw new Error('セッションが切れました。再度ログインしてください。');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// Show loading state
function setLoading(isLoading) {
    state.isLoading = isLoading;
    const btnText = elements.searchBtn.querySelector('.btn-text');
    const btnLoading = elements.searchBtn.querySelector('.btn-loading');

    if (isLoading) {
        btnText.hidden = true;
        btnLoading.hidden = false;
        elements.searchBtn.disabled = true;
        elements.searchInput.disabled = true;
    } else {
        btnText.hidden = false;
        btnLoading.hidden = true;
        elements.searchBtn.disabled = false;
        elements.searchInput.disabled = false;
    }
}

// Show global loading overlay
function showLoadingOverlay() {
    elements.loadingOverlay.hidden = false;
}

// Hide global loading overlay
function hideLoadingOverlay() {
    elements.loadingOverlay.hidden = true;
}

// Handle search
async function handleSearch() {
    const term = elements.searchInput.value.trim();

    if (!term) {
        elements.searchInput.focus();
        return;
    }

    if (state.isLoading) return;

    // Close dashboard if open
    if (elements.dashboardSection && !elements.dashboardSection.hidden) {
        elements.dashboardSection.hidden = true;
    }

    setLoading(true);
    hideAllMessages();
    hidePracticeCard();  // 新規検索時は実践画面をリセット

    try {
        const data = await apiCall('/search', {
            method: 'POST',
            body: JSON.stringify({
                term: term,
                level: 1,
            }),
        });

        state.currentTerm = term;
        state.currentLevel = data.level;

        displayExplanation(data);

        // Refresh history after search
        loadHistory();

        // Check for new badges (async, don't wait)
        checkForNewBadges();
    } catch (error) {
        console.error('Search error:', error);
        showError(error.message || '検索中にエラーが発生しました');
    } finally {
        setLoading(false);
    }
}

// Display explanation
function displayExplanation(data) {
    hideAllMessages();

    // Update term title
    elements.termTitle.textContent = data.term;

    // Render markdown content
    elements.explanationContent.innerHTML = marked.parse(data.explanation);

    // Apply syntax highlighting to code blocks
    elements.explanationContent.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });

    // Update level indicator
    updateLevelIndicator(data.level);

    // Update button states
    elements.moreDetailBtn.disabled = data.level >= state.maxLevel;
    if (data.level >= state.maxLevel) {
        elements.moreDetailBtn.textContent = '最高レベルです';
    } else {
        elements.moreDetailBtn.textContent = '🔍 もっと詳しく';
    }

    // Display related keywords
    displayRelatedKeywords(data.related_keywords || []);

    // Clear additional explanations when main search changes
    elements.additionalExplanations.innerHTML = '';
    state.loadedRelatedKeywords.clear();

    // Show card
    elements.explanationCard.hidden = false;
}

// Display related keywords buttons
function displayRelatedKeywords(keywords) {
    if (!keywords || keywords.length === 0) {
        elements.relatedKeywords.hidden = true;
        return;
    }

    elements.relatedKeywordsList.innerHTML = keywords.map(keyword => `
        <button class="related-keyword-btn" data-keyword="${escapeHtml(keyword)}">
            📖 「${escapeHtml(keyword)}」についても学ぶ
        </button>
    `).join('');

    // Add click handlers
    elements.relatedKeywordsList.querySelectorAll('.related-keyword-btn').forEach(btn => {
        btn.addEventListener('click', () => handleRelatedKeywordClick(btn));
    });

    elements.relatedKeywords.hidden = false;
}

// Handle related keyword button click
async function handleRelatedKeywordClick(btn) {
    const keyword = btn.dataset.keyword;

    // Skip if already loaded
    if (state.loadedRelatedKeywords.has(keyword)) {
        // Scroll to the explanation
        const existingCard = document.querySelector(`[data-related-term="${keyword}"]`);
        if (existingCard) {
            existingCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        return;
    }

    // Disable button and show loading state
    btn.disabled = true;
    btn.textContent = '⏳ 読み込み中...';

    try {
        const data = await apiCall('/search', {
            method: 'POST',
            body: JSON.stringify({
                term: keyword,
                level: 1,
            }),
        });

        // Mark as loaded
        state.loadedRelatedKeywords.add(keyword);
        btn.classList.add('loaded');
        btn.textContent = `✓「${keyword}」を追加しました`;

        // Create additional explanation card
        const card = document.createElement('div');
        card.className = 'additional-explanation-card';
        card.dataset.relatedTerm = keyword;
        card.innerHTML = `
            <div class="card-header">
                <h2 class="term-title">${escapeHtml(keyword)}</h2>
                <div class="level-indicator">
                    <span class="level-badge level-1 active">Lv.1</span>
                </div>
            </div>
            <div class="card-body">
                <div class="explanation-content markdown-body">
                    ${marked.parse(data.explanation)}
                </div>
            </div>
        `;

        // Apply syntax highlighting
        card.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });

        // Append to additional explanations container
        elements.additionalExplanations.appendChild(card);

        // Scroll to the new card
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Refresh history
        loadHistory();
    } catch (error) {
        console.error('Related keyword load error:', error);
        btn.disabled = false;
        btn.textContent = `📖 「${keyword}」についても学ぶ`;
        alert('読み込みに失敗しました: ' + error.message);
    }
}

// Update level indicator
function updateLevelIndicator(activeLevel) {
    const badges = elements.levelIndicator.querySelectorAll('.level-badge');
    badges.forEach(badge => {
        const level = parseInt(badge.dataset.level);
        badge.classList.toggle('active', level <= activeLevel);
    });
}

// Handle "わかった" button
async function handleUnderstand() {
    if (!state.currentTerm || state.isLoading) return;

    elements.understandBtn.disabled = true;

    try {
        await apiCall('/feedback', {
            method: 'POST',
            body: JSON.stringify({
                term: state.currentTerm,
                understood: true,
                current_level: state.currentLevel,
            }),
        });

        showSuccess();

        // Refresh profile and history
        await Promise.all([
            loadProfile(),
            loadHistory(),
        ]);

        // Check for new badges
        checkForNewBadges();

        // Schedule review for this term (spaced repetition)
        try {
            await apiCall('/review/schedule', {
                method: 'POST',
                body: JSON.stringify({ term: state.currentTerm })
            });
        } catch (e) {
            console.log('Review scheduling skipped:', e);
        }

        // Update learning path progress and suggest next term
        await updateLearningPathAndSuggestNext(state.currentTerm);
    } catch (error) {
        console.error('Understand error:', error);
        showError(error.message || '記録中にエラーが発生しました');
    } finally {
        elements.understandBtn.disabled = false;
    }
}

// 練習問題正解時に自動的に「わかった！」を適用
async function applyUnderstandAutomatically() {
    if (!state.currentTerm) return;

    try {
        // Record understanding
        await apiCall('/feedback', {
            method: 'POST',
            body: JSON.stringify({
                term: state.currentTerm,
                understood: true,
                current_level: state.currentLevel,
            }),
        });

        // Refresh profile and history in background
        Promise.all([
            loadProfile(),
            loadHistory(),
        ]).catch(e => console.log('Background refresh failed:', e));

        // Check for new badges
        checkForNewBadges();

        // Schedule review for this term (spaced repetition)
        try {
            await apiCall('/review/schedule', {
                method: 'POST',
                body: JSON.stringify({ term: state.currentTerm })
            });
        } catch (e) {
            console.log('Review scheduling skipped:', e);
        }

        // Update learning path progress and suggest next term
        await updateLearningPathAndSuggestNext(state.currentTerm);

        // Update the "わかった！" button state if visible
        if (elements.understandBtn) {
            elements.understandBtn.disabled = true;
            elements.understandBtn.textContent = '✓ 理解済み';
        }

    } catch (error) {
        console.error('Auto-understand error:', error);
    }
}

// Update learning path progress and suggest next term
async function updateLearningPathAndSuggestNext(term) {
    try {
        // Get user's active learning paths
        const progressData = await apiCall('/learning-paths/progress');

        if (!progressData.progress || progressData.progress.length === 0) {
            return; // No active paths
        }

        // Check each active path
        for (const path of progressData.progress) {
            if (path.completed) continue;

            // Try to update progress for this path
            try {
                const updateResult = await apiCall('/learning-paths/update', {
                    method: 'POST',
                    body: JSON.stringify({
                        path_id: path.path_id,
                        term: term
                    })
                });

                // If progress was made (step increased or completed)
                if (updateResult.current_step > path.current_step || updateResult.completed) {
                    if (updateResult.completed) {
                        // Path completed!
                        showLearningPathNotification({
                            type: 'completed',
                            pathName: path.name,
                            pathIcon: path.icon
                        });
                    } else if (updateResult.next_term) {
                        // Suggest next term
                        showLearningPathNotification({
                            type: 'next',
                            pathName: path.name,
                            pathIcon: path.icon,
                            nextTerm: updateResult.next_term,
                            currentStep: updateResult.current_step,
                            totalSteps: path.total_steps
                        });
                    }
                    break; // Only update one path at a time
                }
            } catch (e) {
                // This path didn't match, continue to next
            }
        }
    } catch (error) {
        console.log('Learning path update skipped:', error);
    }
}

// Show learning path notification
function showLearningPathNotification(data) {
    const notification = document.createElement('div');
    notification.className = 'learning-path-notification';

    if (data.type === 'completed') {
        notification.classList.add('completed');
        notification.innerHTML = `
            <div class="lp-notification-content">
                <div class="lp-notification-header">
                    <div class="lp-notification-icon">🎉</div>
                    <div class="lp-notification-text">
                        <strong>${data.pathIcon} ${data.pathName} 完了！</strong>
                        <span>おめでとうございます！</span>
                    </div>
                    <button class="lp-notification-close" onclick="this.closest('.learning-path-notification').remove()">✕</button>
                </div>
                <div class="lp-notification-progress">全ステップを完了しました</div>
            </div>
        `;
    } else {
        notification.innerHTML = `
            <div class="lp-notification-content">
                <div class="lp-notification-header">
                    <div class="lp-notification-icon">✅</div>
                    <div class="lp-notification-text">
                        <strong>${data.pathIcon} ${data.pathName}</strong>
                        <span>ステップ完了！</span>
                    </div>
                    <button class="lp-notification-close" onclick="this.closest('.learning-path-notification').remove()">✕</button>
                </div>
                <div class="lp-notification-progress">進捗: ${data.currentStep} / ${data.totalSteps} ステップ</div>
                <div class="lp-notification-action">
                    <button class="lp-next-term-btn" onclick="searchNextTerm('${escapeHtml(data.nextTerm)}'); this.closest('.learning-path-notification').remove();">
                        次へ: 「${escapeHtml(data.nextTerm)}」を学ぶ →
                    </button>
                </div>
            </div>
        `;
    }

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Auto-remove after 15 seconds if not interacted
    setTimeout(() => {
        if (notification.parentElement) {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }
    }, 15000);
}

// Search next term from notification
function searchNextTerm(term) {
    elements.searchInput.value = term;
    handleSearch();
}

// Handle "もっと詳しく" button
async function handleMoreDetail() {
    if (!state.currentTerm || state.isLoading) return;
    if (state.currentLevel >= state.maxLevel) return;

    setLoading(true);

    try {
        const nextLevel = state.currentLevel + 1;
        const data = await apiCall('/search', {
            method: 'POST',
            body: JSON.stringify({
                term: state.currentTerm,
                level: nextLevel,
            }),
        });

        state.currentLevel = data.level;
        displayExplanation(data);
    } catch (error) {
        console.error('More detail error:', error);
        showError(error.message || '詳細の取得中にエラーが発生しました');
    } finally {
        setLoading(false);
    }
}

// Load user profile
async function loadProfile() {
    try {
        const profile = await apiCall('/profile');
        updateProfileSummary(profile);
    } catch (error) {
        console.error('Profile load error:', error);
        elements.statsBadge.textContent = '読み込みエラー';
    }
}

// Update profile summary in header
function updateProfileSummary(profile) {
    // understood_terms配列またはunderstood_countプロパティに対応
    const understoodCount = profile.understood_count
        ?? profile.understood_terms?.length
        ?? 0;
    elements.statsBadge.textContent = `✨ 理解済み: ${understoodCount}個`;
}

// Show profile modal
async function showProfileModal() {
    showLoadingOverlay();

    try {
        const profile = await apiCall('/profile');
        renderProfileModal(profile);
        elements.profileModal.hidden = false;
    } catch (error) {
        console.error('Profile modal error:', error);
        showError('プロファイルの取得に失敗しました');
    } finally {
        hideLoadingOverlay();
    }
}

// Render profile modal content
function renderProfileModal(profile) {
    const understoodTerms = profile.understood_terms || [];
    const understoodCount = profile.understood_count ?? understoodTerms.length;
    const searchCount = profile.search_count ?? profile.total_searches ?? 0;

    elements.profileContent.innerHTML = `
        <div class="profile-stat">
            <span class="profile-stat-label">理解した用語</span>
            <span class="profile-stat-value">${understoodCount}</span>
        </div>
        <div class="profile-stat">
            <span class="profile-stat-label">検索回数</span>
            <span class="profile-stat-value">${searchCount}</span>
        </div>
        ${understoodTerms.length > 0 ? `
            <h3 class="profile-section-title">理解済みの用語</h3>
            <div class="understood-terms">
                ${understoodTerms.map(term => `
                    <span class="understood-term-badge">${escapeHtml(term)}</span>
                `).join('')}
            </div>
        ` : ''}
    `;
}

// Hide profile modal
function hideProfileModal() {
    elements.profileModal.hidden = true;
}

// Show history detail modal
async function showHistoryModal(term, level, understood, timestamp) {
    showLoadingOverlay();

    try {
        // Fetch the explanation for this term/level from cache
        const data = await apiCall('/search', {
            method: 'POST',
            body: JSON.stringify({
                term: term,
                level: level,
            }),
        });

        // Update modal title
        elements.historyModalTitle.textContent = `📖 ${term}`;

        // Update meta info
        elements.historyModalMeta.innerHTML = `
            <span class="meta-item">🕐 ${formatDate(timestamp)}</span>
            <span class="meta-badge ${understood ? 'understood' : ''}">
                ${understood ? '✓ 理解済み' : `Lv.${level}`}
            </span>
        `;

        // Render markdown content
        elements.historyModalContent.innerHTML = marked.parse(data.explanation);

        // Apply syntax highlighting to code blocks
        elements.historyModalContent.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });

        elements.historyModal.hidden = false;
    } catch (error) {
        console.error('History modal error:', error);
        // Show simple error in modal
        elements.historyModalTitle.textContent = `📖 ${term}`;
        elements.historyModalMeta.innerHTML = `
            <span class="meta-item">🕐 ${formatDate(timestamp)}</span>
        `;
        elements.historyModalContent.innerHTML = '<p>解説の取得に失敗しました。</p>';
        elements.historyModal.hidden = false;
    } finally {
        hideLoadingOverlay();
    }
}

// Hide history modal
function hideHistoryModal() {
    elements.historyModal.hidden = true;
}

// ========== Practice Mode Functions ==========

// Handle practice button click
async function handlePractice() {
    if (!state.currentTerm) return;

    showLoadingOverlay();

    try {
        const data = await apiCall('/practice', {
            method: 'POST',
            body: JSON.stringify({
                term: state.currentTerm,
                level: state.currentLevel,
            }),
        });

        state.currentPractice = data;
        displayPractice(data);
    } catch (error) {
        console.error('Practice error:', error);
        showError('練習問題の取得に失敗しました');
    } finally {
        hideLoadingOverlay();
    }
}

// Display practice problem
function displayPractice(data) {
    elements.practiceTitle.textContent = `💻 実践: ${data.term}`;

    elements.practiceProblem.innerHTML = `
        <h3>${escapeHtml(data.problem_title)}</h3>
        <p>${escapeHtml(data.problem_description)}</p>
    `;

    // Reset state
    if (state.monacoEditor) {
        state.monacoEditor.setValue('');
        // Clear any error decorations
        state.monacoEditor.deltaDecorations([], []);
    }
    elements.practiceHint.hidden = true;
    elements.practiceAnswer.hidden = true;
    elements.practiceResult.hidden = true;

    elements.practiceCard.hidden = false;

    // Scroll to practice card
    elements.practiceCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Hide practice card
function hidePracticeCard() {
    elements.practiceCard.hidden = true;
    state.currentPractice = null;
    if (state.monacoEditor) {
        state.monacoEditor.setValue('');
    }
}

// Show practice hint
function showPracticeHint() {
    if (!state.currentPractice) return;

    elements.practiceHint.innerHTML = `
        <h4>💡 ヒント</h4>
        <p>${escapeHtml(state.currentPractice.hint)}</p>
    `;
    elements.practiceHint.hidden = false;
}

// Show practice answer
function showPracticeAnswer() {
    if (!state.currentPractice) return;

    elements.practiceAnswer.innerHTML = `
        <h4>📖 解答例</h4>
        <pre><code>${escapeHtml(state.currentPractice.answer)}</code></pre>
    `;
    elements.practiceAnswer.hidden = false;

    // Apply syntax highlighting
    elements.practiceAnswer.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
}

// Check practice answer
async function checkPracticeAnswer() {
    if (!state.currentPractice) return;
    if (!state.monacoEditor) {
        showError('エディタの初期化を待っています。しばらくお待ちください。');
        return;
    }

    const userCode = state.monacoEditor.getValue().trim();

    if (!userCode) {
        elements.practiceResult.className = 'practice-result error';
        elements.practiceResult.innerHTML = `
            <h4>⚠️ コードが入力されていません</h4>
            <p>コードを入力してから確認してください。</p>
        `;
        elements.practiceResult.hidden = false;
        return;
    }

    // Clear previous error markers
    if (state.monacoEditor) {
        state.monacoEditor.deltaDecorations([], []);
    }

    // Disable button during execution
    elements.checkAnswerBtn.disabled = true;
    elements.checkAnswerBtn.textContent = '⏳ 実行中...';

    try {
        // Execute code
        const result = await apiCall('/execute', {
            method: 'POST',
            body: JSON.stringify({
                code: userCode,
                expected_output: state.currentPractice.expected_output,
                output_pattern: state.currentPractice.output_pattern
            }),
        });

        if (result.success) {
            // Code executed successfully
            const output = result.output || '';
            const expectedOutput = state.currentPractice.expected_output;
            const outputPattern = state.currentPractice.output_pattern;
            const patternMatched = result.pattern_matched;

            // 正解判定ロジック:
            // 1. output_pattern がある場合: パターンマッチで判定
            // 2. output_pattern がない場合: コードが正常実行され出力があれば正解
            //    (expected_outputは解答例として表示するが、厳密一致は求めない)
            const isCorrect = patternMatched === true ||
                              (patternMatched !== false && output.trim().length > 0) ||
                              (!expectedOutput && !outputPattern && output.trim().length >= 0);

            elements.practiceResult.className = 'practice-result success';

            let resultHTML = `
                <h4>🎉 素晴らしい！</h4>
                <div class="execution-output">
                    <p><strong>実行結果:</strong></p>
                    <div class="output-box">${escapeHtml(output)}</div>
            `;

            // Show expected output as reference (not strict match)
            if (expectedOutput && output.trim() !== expectedOutput.trim()) {
                resultHTML += `
                    <p class="reference-answer"><strong>解答例:</strong> ${escapeHtml(expectedOutput)}</p>
                `;
            }

            if (isCorrect) {
                resultHTML += `
                    <p>コードが正常に実行されました！</p>
                    <p class="auto-understand-notice">✅ 「わかった！」が自動的に記録されました</p>
                `;
                // 自動的に「わかった！」を適用
                await applyUnderstandAutomatically();
            } else if (patternMatched === false) {
                // Pattern didn't match - suggest checking the output format
                resultHTML += `
                    <p class="warning-text">⚠️ 出力形式が期待と異なります。問題文の形式を確認してみましょう。</p>
                `;
            }

            resultHTML += `</div>`;
            elements.practiceResult.innerHTML = resultHTML;
        } else {
            // Code execution failed
            const errorLine = result.error_line;
            const errorMessage = result.error || 'エラーが発生しました';
            const suggestion = result.suggestion || 'コードを見直してください。';

            // Highlight error line in Monaco Editor
            if (errorLine && state.monacoEditor && typeof monaco !== 'undefined') {
                try {
                    const decorations = [{
                        range: new monaco.Range(errorLine, 1, errorLine, 1),
                        options: {
                            isWholeLine: true,
                            className: 'error-line-highlight',
                            glyphMarginClassName: 'error-glyph',
                            minimap: {
                                color: '#ef4444',
                                position: monaco.editor.MinimapPosition.Inline
                            },
                            overviewRuler: {
                                color: '#ef4444',
                                position: monaco.editor.OverviewRulerLane.Right
                            }
                        }
                    }];
                    state.monacoEditor.deltaDecorations([], decorations);
                } catch (e) {
                    console.warn('Failed to highlight error line:', e);
                }
            }

            elements.practiceResult.className = 'practice-result error';
            elements.practiceResult.innerHTML = `
                <h4>❌ エラーが発生しました</h4>
                <div class="error-details">
                    ${errorLine ? `<p><strong>エラー箇所:</strong> ${errorLine}行目</p>` : ''}
                    <p><strong>エラーメッセージ:</strong></p>
                    <div class="error-box">${escapeHtml(errorMessage)}</div>
                    <p><strong>修正方法:</strong></p>
                    <div class="suggestion-box">${escapeHtml(suggestion)}</div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Code execution error:', error);
        elements.practiceResult.className = 'practice-result error';
        elements.practiceResult.innerHTML = `
            <h4>❌ 実行エラー</h4>
            <p>コードの実行中にエラーが発生しました: ${escapeHtml(error.message)}</p>
        `;
    } finally {
        elements.checkAnswerBtn.disabled = false;
        elements.checkAnswerBtn.textContent = '✓ 回答を確認';
        elements.practiceResult.hidden = false;
    }
}

// Load search history
async function loadHistory() {
    try {
        const response = await apiCall('/history');
        // レスポンスが { history: [...] } の形式の場合に対応
        const history = response.history || response;
        renderHistory(history);
    } catch (error) {
        console.error('History load error:', error);
        elements.historyList.innerHTML = '<p class="empty-message">履歴の読み込みに失敗しました</p>';
    }
}

// Handle clear history button
async function handleClearHistory() {
    if (!confirm('学習履歴を全てクリアしますか？\n（検索履歴と理解度記録が削除されます）')) {
        return;
    }

    showLoadingOverlay();

    try {
        await apiCall('/history', {
            method: 'DELETE',
        });

        // Reload history and profile
        await Promise.all([
            loadHistory(),
            loadProfile(),
        ]);

        // Show success notification
        alert('学習履歴をクリアしました');
    } catch (error) {
        console.error('Clear history error:', error);
        alert('履歴のクリアに失敗しました: ' + error.message);
    } finally {
        hideLoadingOverlay();
    }
}

// Render history list
function renderHistory(history) {
    if (!history || history.length === 0) {
        elements.historyList.innerHTML = '<p class="empty-message">まだ履歴がありません</p>';
        return;
    }

    // Sort by timestamp descending (most recent first)
    const sortedHistory = [...history].sort((a, b) => {
        return new Date(b.timestamp) - new Date(a.timestamp);
    });

    // Take only the last 20 items
    const recentHistory = sortedHistory.slice(0, 20);

    elements.historyList.innerHTML = recentHistory.map(item => `
        <div class="history-item"
             data-term="${escapeHtml(item.term)}"
             data-level="${item.level}"
             data-understood="${item.understood}"
             data-timestamp="${item.timestamp}">
            <div class="history-term">${escapeHtml(item.term)}</div>
            <div class="history-meta">
                <span class="history-time">${formatDate(item.timestamp)}</span>
                <span class="history-level ${item.understood ? 'understood' : ''}">
                    ${item.understood ? '✓ 理解済み' : `Lv.${item.level}`}
                </span>
            </div>
        </div>
    `).join('');

    // Add click handlers to history items - show in modal instead of new search
    elements.historyList.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => {
            const term = item.dataset.term;
            const level = parseInt(item.dataset.level) || 1;
            const understood = item.dataset.understood === 'true';
            const timestamp = item.dataset.timestamp;
            showHistoryModal(term, level, understood, timestamp);
        });
    });
}

// Show error message
function showError(message) {
    hideAllMessages();
    elements.errorText.textContent = message;
    elements.errorMessage.hidden = false;
}

// Show success message
function showSuccess() {
    hideAllMessages();
    elements.successMessage.hidden = false;

    // Auto-hide after 3 seconds
    setTimeout(() => {
        if (!elements.successMessage.hidden) {
            elements.successMessage.hidden = true;
            elements.welcomeMessage.hidden = false;
        }
    }, 3000);
}

// Hide all message elements
function hideAllMessages() {
    elements.welcomeMessage.hidden = true;
    elements.successMessage.hidden = true;
    elements.errorMessage.hidden = true;
    elements.explanationCard.hidden = true;
}

// ========== Page Mode Functions ==========

// Enter page mode (hide main search content, show section as full page)
function enterPageMode(sectionName) {
    document.body.classList.add('page-mode');
    document.body.setAttribute('data-active-section', sectionName);

    // Hide other sections
    elements.dashboardSection.hidden = true;
    elements.glossarySection.hidden = true;
    elements.learningCenterSection.hidden = true;
}

// Exit page mode (show main search content)
function exitPageMode() {
    document.body.classList.remove('page-mode');
    document.body.removeAttribute('data-active-section');

    // Hide all sections
    elements.dashboardSection.hidden = true;
    elements.glossarySection.hidden = true;
    elements.learningCenterSection.hidden = true;

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ========== Dashboard Functions ==========

// Open dashboard
async function openDashboard() {
    enterPageMode('dashboard');
    showLoadingOverlay();

    try {
        // Fetch all analytics data in parallel
        const [progress, daily, keywords, recommendations] = await Promise.all([
            apiCall('/analytics/progress'),
            apiCall('/analytics/daily'),
            apiCall('/analytics/keywords'),
            apiCall('/analytics/recommendations')
        ]);

        // Update stats cards
        elements.totalLearned.textContent = progress.total_terms_learned;
        elements.totalSearches.textContent = progress.total_searches;
        elements.studyDays.textContent = progress.study_days;
        elements.avgSearches.textContent = progress.avg_searches_per_day.toFixed(1);

        // Render recommendations first (doesn't need visible container)
        renderRecommendations(recommendations);

        // Show dashboard BEFORE rendering charts (Chart.js needs visible container)
        elements.dashboardSection.hidden = false;

        // Update progress bar and keyword index
        await updateProgressBar();

        // Use setTimeout to ensure DOM is fully rendered before Chart.js calculates dimensions
        setTimeout(() => {
            try {
                renderActivityChart(daily);
                renderKeywordsChart(keywords);
            } catch (chartError) {
                console.error('Chart rendering error:', chartError);
            }
        }, 100);

        window.scrollTo({ top: 0, behavior: 'smooth' });

    } catch (error) {
        console.error('Dashboard load error:', error);
        console.error('Error details:', error.message, error.stack);
        showError('ダッシュボードの読み込みに失敗しました: ' + error.message);
    } finally {
        hideLoadingOverlay();
    }
}

// Close dashboard
function closeDashboard() {
    exitPageMode();
}

// ========== Glossary Functions ==========

// Open glossary
async function openGlossary() {
    enterPageMode('glossary');
    showLoadingOverlay();

    try {
        // Fetch profile to get learned terms
        const profile = await apiCall('/profile');
        const learnedTerms = profile.understood_terms || [];

        // Show glossary section
        elements.glossarySection.hidden = false;

        // Render keyword index with learned terms
        renderKeywordIndex(learnedTerms);

        window.scrollTo({ top: 0, behavior: 'smooth' });

    } catch (error) {
        console.error('Glossary load error:', error);
        showError('用語集の読み込みに失敗しました: ' + error.message);
    } finally {
        hideLoadingOverlay();
    }
}

// Close glossary
function closeGlossary() {
    exitPageMode();
}

// ========== Learning Center Functions ==========

// Open Learning Center
async function openLearningCenter() {
    enterPageMode('learning-center');
    showLoadingOverlay();

    try {
        // Show Learning Center
        elements.learningCenterSection.hidden = false;

        // Load all data in parallel
        await Promise.all([
            loadStreak(),
            loadLearningPaths(),
            loadBadges(),
            loadReviews(),
            loadPracticeHistory(),
            loadCodeHistory()
        ]);

        window.scrollTo({ top: 0, behavior: 'smooth' });

    } catch (error) {
        console.error('Learning Center load error:', error);
        showError('学習センターの読み込みに失敗しました: ' + error.message);
    } finally {
        hideLoadingOverlay();
    }
}

// Close Learning Center
function closeLearningCenter() {
    exitPageMode();
}

// Switch Learning Center tab
function switchLearningCenterTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.lc-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.lc-tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

// Load streak
async function loadStreak() {
    try {
        const data = await apiCall('/streak');
        elements.streakDays.textContent = data.streak_days;
    } catch (error) {
        console.error('Failed to load streak:', error);
    }
}

// Load learning paths
async function loadLearningPaths() {
    try {
        const [allPaths, progress] = await Promise.all([
            apiCall('/learning-paths'),
            apiCall('/learning-paths/progress')
        ]);

        // Create a map of active paths
        const activePathMap = {};
        progress.progress.forEach(p => {
            activePathMap[p.path_id] = p;
        });

        // Render all paths
        elements.learningPathsGrid.innerHTML = allPaths.paths.map(path => {
            const isActive = activePathMap[path.id];
            return `
                <div class="learning-path-card ${isActive ? 'active' : ''}" onclick="startLearningPath('${path.id}')">
                    <div class="path-header">
                        <span class="path-icon">${path.icon}</span>
                        <span class="path-name">${path.name}</span>
                    </div>
                    <div class="path-description">${path.description}</div>
                    <div class="path-steps">${path.total_steps}ステップ</div>
                    ${isActive ? `
                        <div class="path-progress">
                            <div class="path-progress-bar">
                                <div class="path-progress-fill" style="width: ${activePathMap[path.id].progress_percent}%"></div>
                            </div>
                            <div class="path-progress-text">${activePathMap[path.id].current_step} / ${path.total_steps} 完了</div>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

        // Render active paths with step-by-step list
        if (progress.progress.length > 0) {
            elements.activePaths.innerHTML = progress.progress.map(p => {
                // Generate step list HTML
                const stepsHtml = p.steps.map((step, index) => {
                    let statusClass = 'pending';
                    let indicator = index + 1;
                    let actionHint = '';

                    if (index < p.current_step) {
                        statusClass = 'completed';
                        indicator = '✓';
                    } else if (index === p.current_step && !p.completed) {
                        statusClass = 'current';
                        actionHint = '← 「わかった！」で完了';
                    }

                    return `
                        <div class="path-step-item ${statusClass}">
                            <span class="step-indicator">${indicator}</span>
                            <span class="step-name" onclick="searchFromLearningCenter('${escapeHtml(step)}')" style="cursor:pointer">${escapeHtml(step)}</span>
                            ${actionHint ? `<span class="step-action-hint">${actionHint}</span>` : ''}
                        </div>
                    `;
                }).join('');

                return `
                    <div class="active-path-item">
                        <div class="active-path-header">
                            <span class="active-path-name">${p.icon} ${p.name}</span>
                            <span class="active-path-status ${p.completed ? 'completed' : ''}">${p.completed ? '完了！' : `${p.current_step} / ${p.total_steps}`}</span>
                        </div>
                        <div class="path-progress">
                            <div class="path-progress-bar">
                                <div class="path-progress-fill" style="width: ${p.progress_percent}%"></div>
                            </div>
                        </div>
                        <div class="path-steps-list">
                            ${stepsHtml}
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            elements.activePaths.innerHTML = '<p class="empty-message">まだ学習パスを開始していません。上のパスをクリックして開始しましょう！</p>';
        }

    } catch (error) {
        console.error('Failed to load learning paths:', error);
    }
}

// Start a learning path
async function startLearningPath(pathId) {
    try {
        const result = await apiCall('/learning-paths/start', {
            method: 'POST',
            body: JSON.stringify({ path_id: pathId })
        });

        // Reload learning paths
        await loadLearningPaths();

        // Check for new badges
        await checkForNewBadges();

        // Offer to start learning the first term
        if (result.first_term) {
            if (confirm(`「${result.name}」を開始しました！\n\n最初の用語「${result.first_term}」を学習しますか？`)) {
                searchFromLearningCenter(result.first_term);
            }
        }
    } catch (error) {
        console.error('Failed to start learning path:', error);
    }
}

// Search from Learning Center
function searchFromLearningCenter(term) {
    closeLearningCenter();
    elements.searchInput.value = term;
    handleSearch();
}

// Load badges
async function loadBadges() {
    try {
        const [allBadges, earnedBadges] = await Promise.all([
            apiCall('/badges'),
            apiCall('/badges/earned')
        ]);

        const earnedIds = new Set(earnedBadges.earned_badges.map(b => b.badge_id));

        elements.earnedBadgesCount.textContent = earnedBadges.total_earned;
        elements.totalBadgesCount.textContent = earnedBadges.total_available;

        // Render earned badges
        if (earnedBadges.earned_badges.length > 0) {
            elements.earnedBadgesGrid.innerHTML = earnedBadges.earned_badges.map(badge => `
                <div class="badge-card earned">
                    <div class="badge-icon">${badge.icon}</div>
                    <div class="badge-name">${badge.name}</div>
                    <div class="badge-description">${badge.description}</div>
                    <div class="badge-earned-date">${formatDate(badge.earned_at)}</div>
                </div>
            `).join('');
        } else {
            elements.earnedBadgesGrid.innerHTML = '<p class="empty-message">まだバッジを獲得していません</p>';
        }

        // Render locked badges
        const lockedBadges = allBadges.badges.filter(b => !earnedIds.has(b.id));
        if (lockedBadges.length > 0) {
            elements.lockedBadgesGrid.innerHTML = lockedBadges.map(badge => `
                <div class="badge-card locked">
                    <div class="badge-icon">🔒</div>
                    <div class="badge-name">${badge.name}</div>
                    <div class="badge-description">${badge.description}</div>
                </div>
            `).join('');
        } else {
            elements.lockedBadgesGrid.innerHTML = '<p class="empty-message">全てのバッジを獲得しました！</p>';
        }

    } catch (error) {
        console.error('Failed to load badges:', error);
    }
}

// Check for new badges
async function checkForNewBadges() {
    try {
        const result = await apiCall('/badges/check', { method: 'POST' });

        if (result.newly_awarded && result.newly_awarded.length > 0) {
            // Show notification for each new badge
            result.newly_awarded.forEach(badge => {
                showBadgeNotification(badge);
            });
        }
    } catch (error) {
        console.error('Failed to check badges:', error);
    }
}

// Show badge notification
function showBadgeNotification(badge) {
    const notification = document.createElement('div');
    notification.className = 'badge-notification';
    notification.innerHTML = `
        <div class="badge-notification-content">
            <div class="badge-notification-icon">${badge.icon}</div>
            <div class="badge-notification-text">
                <strong>バッジ獲得！</strong>
                <span>${badge.name}</span>
            </div>
        </div>
    `;
    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Load reviews
async function loadReviews() {
    try {
        const [due, upcoming] = await Promise.all([
            apiCall('/review/due'),
            apiCall('/review/upcoming')
        ]);

        // Render due reviews
        if (due.due_reviews.length > 0) {
            elements.reviewDueList.innerHTML = due.due_reviews.map(review => `
                <div class="review-item due">
                    <span class="review-term" onclick="searchFromLearningCenter('${review.term}')">${review.term}</span>
                    <span class="review-info">復習${review.review_count + 1}回目</span>
                    <button class="review-btn" onclick="completeReview('${review.term}')">復習完了</button>
                </div>
            `).join('');
        } else {
            elements.reviewDueList.innerHTML = '<p class="empty-message">復習が必要な用語はありません</p>';
        }

        // Render upcoming reviews
        if (upcoming.upcoming_reviews.length > 0) {
            elements.reviewUpcomingList.innerHTML = upcoming.upcoming_reviews.map(review => `
                <div class="review-item">
                    <span class="review-term" onclick="searchFromLearningCenter('${review.term}')">${review.term}</span>
                    <span class="review-info">${formatDate(review.scheduled_for)} (${review.interval_days}日後)</span>
                </div>
            `).join('');
        } else {
            elements.reviewUpcomingList.innerHTML = '<p class="empty-message">復習予定はありません</p>';
        }

    } catch (error) {
        console.error('Failed to load reviews:', error);
    }
}

// Complete a review
async function completeReview(term) {
    try {
        await apiCall('/review/schedule', {
            method: 'POST',
            body: JSON.stringify({ term: term })
        });

        // Reload reviews
        await loadReviews();

        // Check for badges
        await checkForNewBadges();
    } catch (error) {
        console.error('Failed to complete review:', error);
    }
}

// Load practice history
async function loadPracticeHistory() {
    try {
        const data = await apiCall('/practice/history');

        // Update statistics
        elements.practiceTotal.textContent = data.statistics.total_attempts;
        elements.practiceCorrect.textContent = data.statistics.correct_count;
        elements.practiceAccuracy.textContent = data.statistics.accuracy + '%';

        // Render history
        if (data.history.length > 0) {
            elements.practiceHistoryList.innerHTML = data.history.slice(0, 20).map(item => `
                <div class="history-item ${item.is_correct ? 'correct' : 'incorrect'}">
                    <span class="history-term">${item.term}</span>
                    <span class="history-result">${item.is_correct ? '✓ 正解' : '✗ 不正解'}</span>
                    <span class="history-date">${formatDate(item.attempted_at)}</span>
                </div>
            `).join('');
        } else {
            elements.practiceHistoryList.innerHTML = '<p class="empty-message">まだ練習問題に挑戦していません</p>';
        }

    } catch (error) {
        console.error('Failed to load practice history:', error);
    }
}

// Load code history
async function loadCodeHistory() {
    try {
        const data = await apiCall('/code-history');

        if (data.history.length > 0) {
            elements.codeHistoryList.innerHTML = data.history.slice(0, 10).map(item => `
                <div class="code-history-item">
                    <div class="code-history-header">
                        <span class="history-term">${item.term}</span>
                        <span class="history-date">${formatDate(item.executed_at)}</span>
                    </div>
                    <pre class="code-history-code">${escapeHtml(item.code)}</pre>
                    ${item.output ? `<div class="code-output">出力: ${escapeHtml(item.output)}</div>` : ''}
                    ${item.error ? `<div class="code-error">エラー: ${escapeHtml(item.error)}</div>` : ''}
                </div>
            `).join('');
        } else {
            elements.codeHistoryList.innerHTML = '<p class="empty-message">コード実行履歴はありません</p>';
        }

    } catch (error) {
        console.error('Failed to load code history:', error);
    }
}

// Format date helper
function formatDate(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'たった今';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}時間前`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}日前`;

    return date.toLocaleDateString('ja-JP');
}

// Escape HTML helper
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Render activity chart (line chart)
function renderActivityChart(data) {
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded');
        return;
    }

    if (!elements.activityChart) {
        console.error('Activity chart canvas not found');
        return;
    }

    const canvas = elements.activityChart;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('Failed to get canvas context');
        return;
    }

    // Destroy existing chart
    if (state.activityChartInstance) {
        state.activityChartInstance.destroy();
        state.activityChartInstance = null;
    }

    // Format dates for display (show only day)
    const labels = data.dates.map(date => {
        const d = new Date(date);
        return `${d.getMonth() + 1}/${d.getDate()}`;
    });

    state.activityChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '検索数',
                    data: data.search_counts,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: '理解済み',
                    data: data.understood_counts,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    }
                }
            }
        }
    });
}

// Render keywords chart (bar chart)
function renderKeywordsChart(data) {
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded');
        return;
    }

    const ctx = elements.keywordsChart.getContext('2d');

    // Destroy existing chart
    if (state.keywordsChartInstance) {
        state.keywordsChartInstance.destroy();
    }

    // Get top 10 keywords
    const top10 = (data.keywords || []).slice(0, 10);

    if (top10.length === 0) {
        // Show empty message
        ctx.clearRect(0, 0, elements.keywordsChart.width, elements.keywordsChart.height);
        ctx.font = '14px sans-serif';
        ctx.fillStyle = '#64748b';
        ctx.textAlign = 'center';
        ctx.fillText('まだデータがありません', elements.keywordsChart.width / 2, 100);
        return;
    }

    state.keywordsChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top10.map(k => k.term),
            datasets: [{
                label: '検索回数',
                data: top10.map(k => k.count),
                backgroundColor: top10.map(k =>
                    k.understood ? '#10b981' : '#3b82f6'
                ),
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const keyword = top10[context.dataIndex];
                            return keyword.understood ? '✓ 理解済み' : '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// Render recommendations
function renderRecommendations(data) {
    const recommendations = data.recommendations || [];

    if (recommendations.length === 0) {
        elements.recommendationsList.innerHTML = `
            <div class="empty-recommendations">
                <p>推奨トピックはありません。</p>
                <p>学習を進めると、次に学ぶべきトピックが提案されます。</p>
            </div>
        `;
        return;
    }

    elements.recommendationsList.innerHTML = recommendations.map(rec => `
        <div class="recommendation-item" data-term="${escapeHtml(rec.term)}">
            <div class="recommendation-icon">📚</div>
            <div class="recommendation-content">
                <div class="recommendation-term">${escapeHtml(rec.term)}</div>
                <div class="recommendation-reason">${escapeHtml(rec.reason)}</div>
            </div>
        </div>
    `).join('');

    // Add click handlers to search for the term
    elements.recommendationsList.querySelectorAll('.recommendation-item').forEach(item => {
        item.addEventListener('click', () => {
            const term = item.dataset.term;
            elements.searchInput.value = term;
            elements.dashboardSection.hidden = true;
            handleSearch();
        });
    });
}

// Utility: Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    // Less than 1 minute
    if (diff < 60000) {
        return 'たった今';
    }

    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}分前`;
    }

    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}時間前`;
    }

    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}日前`;
    }

    // Otherwise show date
    return date.toLocaleDateString('ja-JP', {
        month: 'short',
        day: 'numeric',
    });
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Utility: Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ========== Theme Management ==========

// Initialize theme from localStorage or system preference
function initializeTheme() {
    // テーマは既にindex.htmlのインラインスクリプトで適用済み
    // ここでは念のため再確認
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
        // Check system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) {
            document.documentElement.setAttribute('data-theme', 'dark');
        }
    }

    // ページ読み込み完了後にトランジションを有効化（ちらつき防止）
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            document.body.classList.add('theme-ready');
        });
    });
}

// Toggle between light and dark theme
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // Add animation class
    document.body.classList.add('theme-transitioning');
    setTimeout(() => {
        document.body.classList.remove('theme-transitioning');
    }, 300);
}

// ========== Mobile Sidebar ==========

// Open mobile sidebar
function openMobileSidebar() {
    elements.sidebar.classList.add('open');
    elements.sidebarOverlay.classList.add('visible');
    document.body.style.overflow = 'hidden';
}

// Close mobile sidebar
function closeMobileSidebar() {
    elements.sidebar.classList.remove('open');
    elements.sidebarOverlay.classList.remove('visible');
    document.body.style.overflow = '';
}

// Go to home screen
function goHome() {
    // Exit page mode if active
    document.body.classList.remove('page-mode');
    document.body.removeAttribute('data-active-section');

    // Reset state
    state.currentTerm = null;
    state.currentLevel = 1;
    state.currentPractice = null;
    state.loadedRelatedKeywords.clear();

    // Clear search input
    elements.searchInput.value = '';

    // Hide all content sections
    elements.explanationCard.hidden = true;
    elements.practiceCard.hidden = true;
    elements.successMessage.hidden = true;
    elements.errorMessage.hidden = true;
    elements.dashboardSection.hidden = true;
    elements.glossarySection.hidden = true;
    elements.learningCenterSection.hidden = true;

    // Clear additional explanations
    elements.additionalExplanations.innerHTML = '';

    // Show welcome message
    elements.welcomeMessage.hidden = false;

    // Close mobile sidebar if open
    closeMobileSidebar();

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ========== Progress Bar ==========

// Progress milestones will be configured dynamically after PYTHON_KEYWORD_INDEX is defined
let PROGRESS_MILESTONES = {
    beginner: 0,     // 初心者
    learning: 20,    // 学習中
    intermediate: 50, // 中級者
    advanced: 100    // 上級者 - will be updated to ALL_PYTHON_KEYWORDS.length
};

// Python keywords index organized by category (based on official Python documentation)
const PYTHON_KEYWORD_INDEX = {
    '1. 基本構文': {
        icon: '📝',
        keywords: [
            'コメント', 'インデント', '変数', '代入', '式', '文',
            'print関数', 'input関数', '型変換', 'f文字列'
        ]
    },
    '2. データ型': {
        icon: '📦',
        keywords: [
            '整数 (int)', '浮動小数点 (float)', '文字列 (str)', 'ブール値 (bool)',
            'None', 'bytes', '複素数 (complex)'
        ]
    },
    '3. データ構造': {
        icon: '🗂️',
        keywords: [
            'リスト (list)', 'タプル (tuple)', '辞書 (dict)', 'セット (set)',
            'frozenset', 'リスト内包表記', '辞書内包表記', 'セット内包表記',
            'スライス', 'アンパック'
        ]
    },
    '4. 制御フロー': {
        icon: '🔀',
        keywords: [
            'if文', 'elif', 'else', 'for文', 'while文', 'break', 'continue',
            'pass', 'match文', 'range関数', 'enumerate', 'zip'
        ]
    },
    '5. 関数': {
        icon: '⚙️',
        keywords: [
            '関数定義 (def)', '引数', 'デフォルト引数', 'キーワード引数',
            '*args', '**kwargs', 'return', 'ラムダ式 (lambda)', 'スコープ',
            'global', 'nonlocal', 'クロージャ', 'デコレータ', 'ドキュメント文字列'
        ]
    },
    '6. クラスとオブジェクト': {
        icon: '🏛️',
        keywords: [
            'クラス定義 (class)', 'インスタンス', 'self', '__init__', '属性',
            'メソッド', 'クラス変数', 'インスタンス変数', '継承', '多重継承',
            'super()', 'オーバーライド', 'プロパティ (@property)', 'クラスメソッド',
            'スタティックメソッド', '抽象クラス', 'ダンダーメソッド'
        ]
    },
    '7. モジュールとパッケージ': {
        icon: '📚',
        keywords: [
            'import', 'from import', 'as', 'モジュール', 'パッケージ',
            '__name__', '__main__', '__init__.py', 'pip', '仮想環境 (venv)',
            'requirements.txt', 'サードパーティライブラリ'
        ]
    },
    '8. 例外処理': {
        icon: '⚠️',
        keywords: [
            'try', 'except', 'finally', 'raise', 'assert', 'Exception',
            'カスタム例外', '例外チェーン', 'with文', 'コンテキストマネージャ'
        ]
    },
    '9. ファイル操作': {
        icon: '📁',
        keywords: [
            'open()', 'read()', 'write()', 'close()', 'withによるファイル操作',
            'ファイルモード', 'テキストファイル', 'バイナリファイル',
            'pathlib', 'os.path'
        ]
    },
    '10. イテレータとジェネレータ': {
        icon: '🔄',
        keywords: [
            'イテレータ', 'イテラブル', '__iter__', '__next__', 'iter()',
            'next()', 'ジェネレータ', 'yield', 'ジェネレータ式', 'itertools'
        ]
    },
    '11. 組み込み関数': {
        icon: '🔧',
        keywords: [
            'len()', 'type()', 'isinstance()', 'id()', 'dir()', 'help()',
            'sorted()', 'reversed()', 'map()', 'filter()', 'reduce()',
            'any()', 'all()', 'sum()', 'min()', 'max()', 'abs()',
            'round()', 'pow()', 'divmod()', 'hash()', 'callable()'
        ]
    },
    '12. 文字列操作': {
        icon: '📜',
        keywords: [
            'split()', 'join()', 'strip()', 'replace()', 'find()', 'format()',
            'upper()', 'lower()', 'startswith()', 'endswith()', 'encode()',
            'decode()', '正規表現 (re)', 'エスケープシーケンス'
        ]
    },
    '13. 数値と演算': {
        icon: '🔢',
        keywords: [
            '算術演算子', '比較演算子', '論理演算子', 'ビット演算子',
            '代入演算子', '演算子の優先順位', 'mathモジュール', 'randomモジュール',
            'decimalモジュール', 'fractionsモジュール'
        ]
    },
    '14. 日付と時刻': {
        icon: '📅',
        keywords: [
            'datetime', 'date', 'time', 'timedelta', 'strftime()',
            'strptime()', 'timezone', 'calendarモジュール'
        ]
    },
    '15. データシリアライズ': {
        icon: '💾',
        keywords: [
            'JSON', 'json.dumps()', 'json.loads()', 'pickle', 'csv',
            'YAML', 'XML', 'configparser'
        ]
    },
    '16. ネットワークとWeb': {
        icon: '🌐',
        keywords: [
            'urllib', 'requests', 'HTTP', 'REST API', 'ソケット',
            'asyncio', 'aiohttp', 'websocket'
        ]
    },
    '17. 並行処理': {
        icon: '⚡',
        keywords: [
            'threading', 'Thread', 'Lock', 'multiprocessing', 'Process',
            'Queue', 'Pool', 'concurrent.futures', 'async/await', 'コルーチン'
        ]
    },
    '18. テストとデバッグ': {
        icon: '🧪',
        keywords: [
            'unittest', 'pytest', 'assert', 'mock', 'doctest',
            'pdb', 'breakpoint()', 'logging', 'traceback'
        ]
    },
    '19. 型ヒント': {
        icon: '🏷️',
        keywords: [
            '型アノテーション', 'typing', 'Optional', 'Union', 'List', 'Dict',
            'Tuple', 'Set', 'Callable', 'Any', 'TypeVar', 'Generic', 'Protocol'
        ]
    },
    '20. 高度なトピック': {
        icon: '🎓',
        keywords: [
            'メタクラス', 'デスクリプタ', '__slots__', 'weakref',
            'functools', 'operator', 'dataclasses', 'namedtuple',
            'enum', 'ABC', 'contextlib', 'collections'
        ]
    }
};

// Flatten all keywords for counting
const ALL_PYTHON_KEYWORDS = Object.values(PYTHON_KEYWORD_INDEX)
    .flatMap(category => category.keywords);

// Update progress milestones to match total keyword count
PROGRESS_MILESTONES.advanced = ALL_PYTHON_KEYWORDS.length;
// Adjust intermediate and learning milestones proportionally
PROGRESS_MILESTONES.intermediate = Math.round(ALL_PYTHON_KEYWORDS.length * 0.4);  // ~40%
PROGRESS_MILESTONES.learning = Math.round(ALL_PYTHON_KEYWORDS.length * 0.15);     // ~15%

// Update progress bar based on learned terms
async function updateProgressBar() {
    try {
        const profile = await apiCall('/profile');
        const learnedTerms = profile.understood_terms || [];
        const learnedCount = profile.understood_count ?? learnedTerms.length ?? 0;

        // Calculate progress percentage (max at 30 terms = 100%)
        const maxTerms = PROGRESS_MILESTONES.advanced;
        const percentage = Math.min((learnedCount / maxTerms) * 100, 100);

        // Update progress bar with animation
        elements.progressBarFill.style.width = `${percentage}%`;
        elements.progressStats.textContent = `${learnedCount} / ${maxTerms} 用語`;

        // Add pulsing animation if progress is ongoing
        if (percentage > 0 && percentage < 100) {
            elements.progressBarFill.classList.add('animating');
        } else {
            elements.progressBarFill.classList.remove('animating');
        }

        // Update milestones
        updateMilestones(learnedCount);

        // Note: Keyword index is now rendered in the glossary section, not here

    } catch (error) {
        console.error('Progress bar update error:', error);
    }
}

// Update milestone achievements
function updateMilestones(learnedCount) {
    const milestones = [
        { element: elements.milestone1, threshold: 0 },       // Beginner
        { element: elements.milestone2, threshold: PROGRESS_MILESTONES.learning },      // Learning
        { element: elements.milestone3, threshold: PROGRESS_MILESTONES.intermediate },  // Intermediate
        { element: elements.milestone4, threshold: PROGRESS_MILESTONES.advanced }       // Advanced
    ];

    // Clear all classes first
    milestones.forEach(m => {
        m.element.classList.remove('achieved', 'current');
    });

    // Find current level
    let currentIndex = 0;
    for (let i = milestones.length - 1; i >= 0; i--) {
        if (learnedCount >= milestones[i].threshold) {
            currentIndex = i;
            break;
        }
    }

    // Mark achieved milestones
    for (let i = 0; i <= currentIndex; i++) {
        if (learnedCount >= milestones[i].threshold) {
            milestones[i].element.classList.add('achieved');
        }
    }

    // Mark current milestone (the next goal if not at max)
    if (currentIndex < milestones.length - 1) {
        milestones[currentIndex + 1].element.classList.add('current');
    } else if (learnedCount >= PROGRESS_MILESTONES.advanced) {
        // At max level, mark as achieved
        milestones[currentIndex].element.classList.add('achieved');
    }
}

// Check if a keyword is learned (with flexible matching)
function isKeywordLearned(keyword, normalizedLearnedTerms) {
    const normalizedKeyword = keyword.toLowerCase().trim();
    // Check exact match
    if (normalizedLearnedTerms.includes(normalizedKeyword)) return true;
    // Check if keyword contains the learned term or vice versa
    for (const term of normalizedLearnedTerms) {
        if (normalizedKeyword.includes(term) || term.includes(normalizedKeyword)) {
            return true;
        }
    }
    return false;
}

// Render the keyword index with categories
function renderKeywordIndex(learnedTerms) {
    console.log('renderKeywordIndex called with:', learnedTerms);

    // Ensure learnedTerms is an array
    if (!Array.isArray(learnedTerms)) {
        console.warn('learnedTerms is not an array, defaulting to empty array');
        learnedTerms = [];
    }

    // Normalize learned terms for comparison
    const normalizedLearnedTerms = learnedTerms.map(term => term.toLowerCase().trim());
    console.log('Normalized terms:', normalizedLearnedTerms);

    // Count total and learned keywords
    const totalKeywords = ALL_PYTHON_KEYWORDS.length;
    let learnedCount = 0;

    // Update total count display
    elements.totalKeywordCount.textContent = totalKeywords;

    // Clear current TOC
    elements.keywordIndexToc.innerHTML = '';

    console.log('PYTHON_KEYWORD_INDEX:', PYTHON_KEYWORD_INDEX);
    console.log('Number of categories:', Object.keys(PYTHON_KEYWORD_INDEX).length);

    // Render each category
    Object.entries(PYTHON_KEYWORD_INDEX).forEach(([categoryName, categoryData]) => {
        console.log('Rendering category:', categoryName, categoryData);
        const { icon, keywords } = categoryData;

        // Count learned keywords in this category
        let categoryLearnedCount = 0;
        keywords.forEach(keyword => {
            if (isKeywordLearned(keyword, normalizedLearnedTerms)) {
                categoryLearnedCount++;
                learnedCount++;
            }
        });

        // Create category item (collapsed by default)
        const categoryItem = document.createElement('div');
        categoryItem.className = 'category-item';

        // Category header - build using createElement for better compatibility
        const categoryHeader = document.createElement('div');
        categoryHeader.className = 'category-header';

        // Title section
        const titleDiv = document.createElement('div');
        titleDiv.className = 'category-title';

        const iconSpan = document.createElement('span');
        iconSpan.className = 'category-icon';
        iconSpan.textContent = icon;

        const nameSpan = document.createElement('span');
        nameSpan.className = 'category-name';
        nameSpan.textContent = categoryName;

        titleDiv.appendChild(iconSpan);
        titleDiv.appendChild(nameSpan);

        // Meta section
        const metaDiv = document.createElement('div');
        metaDiv.className = 'category-meta';

        const progressSpan = document.createElement('span');
        progressSpan.className = 'category-progress' + (categoryLearnedCount === keywords.length ? ' complete' : '');
        progressSpan.textContent = `${categoryLearnedCount}/${keywords.length}`;

        const toggleSpan = document.createElement('span');
        toggleSpan.className = 'category-toggle';
        toggleSpan.textContent = '▼';

        metaDiv.appendChild(progressSpan);
        metaDiv.appendChild(toggleSpan);

        categoryHeader.appendChild(titleDiv);
        categoryHeader.appendChild(metaDiv);

        // Toggle expansion on click
        categoryHeader.addEventListener('click', () => {
            categoryItem.classList.toggle('expanded');
        });

        // Category keywords container
        const categoryKeywords = document.createElement('div');
        categoryKeywords.className = 'category-keywords';

        const keywordList = document.createElement('div');
        keywordList.className = 'keyword-list';

        // Add keyword buttons
        keywords.forEach(keyword => {
            const btn = document.createElement('button');
            const isLearned = isKeywordLearned(keyword, normalizedLearnedTerms);
            btn.className = `keyword-btn ${isLearned ? 'learned' : ''}`;
            btn.textContent = keyword;
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                // Close glossary and search for this keyword
                closeGlossary();
                elements.searchInput.value = keyword;
                handleSearch();
            });
            keywordList.appendChild(btn);
        });

        categoryKeywords.appendChild(keywordList);
        categoryItem.appendChild(categoryHeader);
        categoryItem.appendChild(categoryKeywords);
        elements.keywordIndexToc.appendChild(categoryItem);
    });

    // Update learned count display
    elements.learnedCount.textContent = learnedCount;
}
