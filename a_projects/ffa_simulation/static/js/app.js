/**
 * FFA模拟交易系统 - 主应用JavaScript
 * 模仿OpenVlab风格的交互功能
 */

// 全局应用对象
const FFAApp = {
    // 配置
    config: {
        apiBaseUrl: '/api',
        refreshInterval: 5000,
        animationDuration: 300,
        maxRetries: 3
    },
    
    // 状态管理
    state: {
        isAuthenticated: false,
        currentUser: null,
        authToken: null,
        currentAccount: null,
        marketData: {},
        positions: [],
        trades: [],
        isConnected: true
    },
    
    // 初始化应用
    init() {
        console.log('🚀 FFA模拟交易系统启动中...');
        this.loadAuthState();
        this.setupEventListeners();
        this.initializeComponents();
        this.startDataRefresh();
        console.log('✅ FFA模拟交易系统启动完成');
    },
    
    // 加载认证状态
    loadAuthState() {
        const token = localStorage.getItem('authToken');
        if (token) {
            this.state.authToken = token;
            this.validateToken();
        }
    },
    
    // 验证token
    async validateToken() {
        try {
            const response = await this.apiCall('/me', 'GET');
            if (response.ok) {
                this.state.currentUser = await response.json();
                this.state.isAuthenticated = true;
                this.updateUIForAuthenticatedUser();
            } else {
                this.logout();
            }
        } catch (error) {
            console.error('Token验证失败:', error);
            this.logout();
        }
    },
    
    // 设置事件监听器
    setupEventListeners() {
        // 导航栏滚动效果
        window.addEventListener('scroll', this.handleScroll.bind(this));
        
        // 窗口大小变化
        window.addEventListener('resize', this.handleResize.bind(this));
        
        // 网络状态监听
        window.addEventListener('online', this.handleOnline.bind(this));
        window.addEventListener('offline', this.handleOffline.bind(this));
        
        // 页面可见性变化
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    },
    
    // 初始化组件
    initializeComponents() {
        this.initTooltips();
        this.initModals();
        this.initCharts();
        this.initDataTables();
    },
    
    // 处理滚动事件
    handleScroll() {
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }
    },
    
    // 处理窗口大小变化
    handleResize() {
        // 重新计算图表大小等
        this.resizeCharts();
    },
    
    // 处理网络连接
    handleOnline() {
        this.state.isConnected = true;
        this.showNotification('网络连接已恢复', 'success');
        this.startDataRefresh();
    },
    
    handleOffline() {
        this.state.isConnected = false;
        this.showNotification('网络连接已断开', 'warning');
        this.stopDataRefresh();
    },
    
    // 处理页面可见性变化
    handleVisibilityChange() {
        if (document.hidden) {
            this.stopDataRefresh();
        } else {
            this.startDataRefresh();
        }
    },
    
    // API调用封装
    async apiCall(endpoint, method = 'GET', data = null, retries = 0) {
        const url = `${this.config.apiBaseUrl}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (this.state.authToken) {
            options.headers['Authorization'] = `Bearer ${this.state.authToken}`;
        }
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            if (!response.ok && response.status === 401 && retries < this.config.maxRetries) {
                // Token过期，尝试刷新
                await this.refreshToken();
                return this.apiCall(endpoint, method, data, retries + 1);
            }
            
            return response;
        } catch (error) {
            console.error(`API调用失败 (${method} ${endpoint}):`, error);
            throw error;
        }
    },
    
    // 刷新token
    async refreshToken() {
        // 这里应该实现token刷新逻辑
        console.log('刷新token...');
    },
    
    // 登录
    async login(credentials) {
        try {
            const response = await this.apiCall('/login', 'POST', credentials);
            const result = await response.json();
            
            if (response.ok) {
                this.state.authToken = result.access_token;
                localStorage.setItem('authToken', this.state.authToken);
                this.state.isAuthenticated = true;
                
                // 获取用户信息
                const userResponse = await this.apiCall('/me', 'GET');
                this.state.currentUser = await userResponse.json();
                
                this.updateUIForAuthenticatedUser();
                this.showNotification('登录成功！', 'success');
                
                return { success: true };
            } else {
                throw new Error(result.detail || '登录失败');
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
            return { success: false, error: error.message };
        }
    },
    
    // 注册
    async register(userData) {
        try {
            const response = await this.apiCall('/register', 'POST', userData);
            const result = await response.json();
            
            if (response.ok) {
                this.showNotification('注册成功！请登录', 'success');
                return { success: true };
            } else {
                throw new Error(result.detail || '注册失败');
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
            return { success: false, error: error.message };
        }
    },
    
    // 登出
    logout() {
        this.state.authToken = null;
        this.state.currentUser = null;
        this.state.isAuthenticated = false;
        localStorage.removeItem('authToken');
        this.updateUIForUnauthenticatedUser();
        this.showNotification('已登出', 'info');
    },
    
    // 更新已认证用户的UI
    updateUIForAuthenticatedUser() {
        const loginBtn = document.querySelector('.btn-login');
        if (loginBtn && this.state.currentUser) {
            loginBtn.innerHTML = `<i class="fas fa-user me-1"></i>${this.state.currentUser.username}`;
            loginBtn.onclick = () => this.showUserMenu();
        }
        
        // 显示需要认证的功能
        document.querySelectorAll('.auth-required').forEach(el => {
            el.style.display = 'block';
        });
    },
    
    // 更新未认证用户的UI
    updateUIForUnauthenticatedUser() {
        const loginBtn = document.querySelector('.btn-login');
        if (loginBtn) {
            loginBtn.innerHTML = '<i class="fas fa-sign-in-alt me-1"></i>登录';
            loginBtn.onclick = () => this.showLoginModal();
        }
        
        // 隐藏需要认证的功能
        document.querySelectorAll('.auth-required').forEach(el => {
            el.style.display = 'none';
        });
    },
    
    // 显示登录模态框
    showLoginModal() {
        const modal = new bootstrap.Modal(document.getElementById('loginModal'));
        modal.show();
    },
    
    // 显示用户菜单
    showUserMenu() {
        // 实现用户菜单逻辑
        console.log('显示用户菜单');
    },
    
    // 执行交易
    async executeTrade(tradeData) {
        if (!this.state.isAuthenticated) {
            this.showNotification('请先登录', 'warning');
            this.showLoginModal();
            return { success: false, error: '未登录' };
        }
        
        try {
            // 获取账户ID
            const accountsResponse = await this.apiCall('/accounts', 'GET');
            const accounts = await accountsResponse.json();
            
            if (accounts.length === 0) {
                throw new Error('没有可用的交易账户');
            }
            
            const accountId = accounts[0].id;
            const response = await this.apiCall(`/trades?account_id=${accountId}`, 'POST', tradeData);
            const result = await response.json();
            
            if (response.ok) {
                this.showNotification('交易执行成功！', 'success');
                this.loadAccountData();
                return { success: true, data: result };
            } else {
                throw new Error(result.detail || '交易执行失败');
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
            return { success: false, error: error.message };
        }
    },
    
    // 加载账户数据
    async loadAccountData() {
        if (!this.state.isAuthenticated) return;
        
        try {
            const accountsResponse = await this.apiCall('/accounts', 'GET');
            const accounts = await accountsResponse.json();
            
            if (accounts.length > 0) {
                this.state.currentAccount = accounts[0];
                await this.loadAccountSummary(accounts[0].id);
                await this.loadRecentTrades(accounts[0].id);
                await this.loadPositions(accounts[0].id);
            }
        } catch (error) {
            console.error('加载账户数据失败:', error);
        }
    },
    
    // 加载账户汇总
    async loadAccountSummary(accountId) {
        try {
            const response = await this.apiCall(`/accounts/${accountId}/summary`, 'GET');
            const summary = await response.json();
            this.displayAccountSummary(summary);
        } catch (error) {
            console.error('加载账户汇总失败:', error);
        }
    },
    
    // 显示账户汇总
    displayAccountSummary(summary) {
        const container = document.getElementById('accountSummary');
        if (!container) return;
        
        container.innerHTML = `
            <div class="row text-center">
                <div class="col-6 mb-3">
                    <div class="text-muted">总资产</div>
                    <div class="h5 text-primary">$${this.formatNumber(summary.total_equity || 0)}</div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-muted">可用资金</div>
                    <div class="h5 text-success">$${this.formatNumber(summary.available_cash || 0)}</div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-muted">浮动盈亏</div>
                    <div class="h5 ${summary.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}">
                        $${this.formatNumber(summary.unrealized_pnl || 0)}
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="text-muted">已实现盈亏</div>
                    <div class="h5 ${summary.realized_pnl >= 0 ? 'text-success' : 'text-danger'}">
                        $${this.formatNumber(summary.realized_pnl || 0)}
                    </div>
                </div>
            </div>
        `;
    },
    
    // 加载最近交易
    async loadRecentTrades(accountId) {
        try {
            const response = await this.apiCall(`/trades?account_id=${accountId}&limit=5`, 'GET');
            const trades = await response.json();
            this.displayRecentTrades(trades);
        } catch (error) {
            console.error('加载最近交易失败:', error);
        }
    },
    
    // 显示最近交易
    displayRecentTrades(trades) {
        const container = document.getElementById('recentTrades');
        if (!container) return;
        
        if (trades.length === 0) {
            container.innerHTML = '<p class="text-muted">暂无交易记录</p>';
            return;
        }
        
        const tradesHtml = trades.map(trade => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <div class="small">${trade.contract} ${trade.month}</div>
                    <div class="text-muted small">${trade.action} ${trade.buy_sell}</div>
                </div>
                <div class="text-end">
                    <div class="small">$${this.formatNumber(trade.future_price)}</div>
                    <div class="text-muted small">${trade.volume}</div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = tradesHtml;
    },
    
    // 加载持仓信息
    async loadPositions(accountId) {
        try {
            const response = await this.apiCall(`/positions?account_id=${accountId}`, 'GET');
            const positions = await response.json();
            this.displayPositions(positions);
        } catch (error) {
            console.error('加载持仓信息失败:', error);
        }
    },
    
    // 显示持仓信息
    displayPositions(positions) {
        const tbody = document.getElementById('positionsTable');
        if (!tbody) return;
        
        if (positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">暂无持仓数据</td></tr>';
            return;
        }
        
        const positionsHtml = positions.map(position => `
            <tr>
                <td>${position.contract} ${position.month}</td>
                <td>
                    <span class="badge ${position.position_volume > 0 ? 'bg-success' : 'bg-danger'}">
                        ${position.position_volume > 0 ? '多头' : '空头'}
                    </span>
                </td>
                <td>${Math.abs(position.position_volume)}</td>
                <td>$${this.formatNumber(position.average_price || 0, 2)}</td>
                <td>$${this.formatNumber(position.daily_settlement_price || 0, 2)}</td>
                <td class="${position.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}">
                    $${this.formatNumber(position.unrealized_pnl || 0, 2)}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="FFAApp.closePosition(${position.id})">
                        平仓
                    </button>
                </td>
            </tr>
        `).join('');
        
        tbody.innerHTML = positionsHtml;
    },
    
    // 平仓操作
    async closePosition(positionId) {
        if (!this.state.isAuthenticated) {
            this.showNotification('请先登录', 'warning');
            return;
        }
        
        if (confirm('确定要平仓这个持仓吗？')) {
            try {
                // 这里应该实现平仓逻辑
                this.showNotification('平仓功能开发中...', 'info');
            } catch (error) {
                this.showNotification('平仓失败: ' + error.message, 'error');
            }
        }
    },
    
    // 开始数据刷新
    startDataRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        this.refreshTimer = setInterval(() => {
            if (this.state.isAuthenticated && !document.hidden) {
                this.loadAccountData();
            }
        }, this.config.refreshInterval);
    },
    
    // 停止数据刷新
    stopDataRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    },
    
    // 初始化工具提示
    initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },
    
    // 初始化模态框
    initModals() {
        // 模态框相关初始化
    },
    
    // 初始化图表
    initCharts() {
        // 图表相关初始化
    },
    
    // 重新调整图表大小
    resizeCharts() {
        // 重新调整图表大小
    },
    
    // 初始化数据表格
    initDataTables() {
        // 数据表格相关初始化
    },
    
    // 显示通知
    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `alert-custom alert-${type} alert-dismissible fade show`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            animation: slideInDown 0.3s ease-out;
        `;
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close float-end" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.animation = 'slideOutUp 0.3s ease-in';
                setTimeout(() => notification.remove(), 300);
            }
        }, duration);
    },
    
    // 格式化数字
    formatNumber(num, decimals = 0) {
        return Number(num).toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    },
    
    // 格式化货币
    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    },
    
    // 格式化日期
    formatDate(date, format = 'YYYY-MM-DD') {
        const d = new Date(date);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        
        switch (format) {
            case 'YYYY-MM-DD':
                return `${year}-${month}-${day}`;
            case 'MM/DD/YYYY':
                return `${month}/${day}/${year}`;
            case 'DD/MM/YYYY':
                return `${day}/${month}/${year}`;
            default:
                return d.toLocaleDateString();
        }
    },
    
    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // 节流函数
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideOutUp {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-30px);
        }
    }
`;
document.head.appendChild(style);

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    FFAApp.init();
});

// 导出到全局
window.FFAApp = FFAApp;
