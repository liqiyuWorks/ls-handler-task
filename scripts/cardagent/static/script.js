// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('名片智能体页面已加载');
    
    // 监听 iframe 加载
    const agentFrame = document.getElementById('agentFrame');
    
    agentFrame.addEventListener('load', function() {
        console.log('智能体聊天窗口已加载');
    });
    
    agentFrame.addEventListener('error', function() {
        console.error('智能体聊天窗口加载失败');
        // 可以在这里添加错误提示
    });
    
    // 添加平滑滚动效果
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // 添加卡片交互效果
    const card = document.querySelector('.card');
    if (card) {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.3s ease';
        });
    }
});

// 处理窗口大小变化
window.addEventListener('resize', function() {
    const chatSection = document.querySelector('.chat-section');
    if (window.innerWidth <= 1024) {
        chatSection.style.height = '600px';
    } else {
        chatSection.style.height = 'calc(100vh - 40px)';
    }
});

