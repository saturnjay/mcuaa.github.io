<!-- start Simple Custom CSS and JS -->
<script type="text/javascript">
/**
 * 使 WordPress Query Loop 卡片可点击
 */
document.addEventListener('DOMContentLoaded', function() {
    // 使用事件委托，将点击事件监听器绑定到 document 或一个静态的父容器上
    // 这样可以处理动态加载的内容，并避免事件绑定时机问题
    document.addEventListener('click', function(event) {
        // 检查被点击的元素是否具有 .wp-block-post 类，或者是其子元素
        const clickedCard = event.target.closest('.wp-block-query .wp-block-post');
        
        if (clickedCard) {
            // 阻止事件冒泡，避免与卡片内其他可能的链接点击事件冲突
            event.stopPropagation();
            
            // 在卡片内部查找文章标题的链接
            // 选择器可根据您的主题结构调整，例如可能是 h2 a 或 .wp-block-post-title a
            const postLink = clickedCard.querySelector('.wp-block-post-title a, h2 a, h3 a');
            
            if (postLink && postLink.href) {
                // 获取链接地址并跳转
                window.location.href = postLink.href;
            }
        }
    });
});</script>
<!-- end Simple Custom CSS and JS -->
