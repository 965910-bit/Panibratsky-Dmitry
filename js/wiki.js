// Wiki page functionality

class WikiManager {
    constructor() {
        this.articles = [];
        this.categories = [];
        this.currentArticle = null;
        
        this.initialize();
    }

    async initialize() {
        await this.loadData();
        this.renderNavigation();
        this.renderArticle('introduction'); // Show first article by default
    }

    async loadData() {
        try {
            const data = await fetch('/data/wiki.json');
            if (!data.ok) throw new Error('Failed to load wiki data');
            
            const jsonData = await data.json();
            this.articles = jsonData.articles || [];
            this.categories = jsonData.categories || [];
            
        } catch (error) {
            console.error('Error loading wiki:', error);
            this.showError('Ошибка загрузки данных Wiki');
        }
    }

    renderNavigation() {
        const navContainer = document.getElementById('wiki-nav');
        const contentContainer = document.getElementById('wiki-content');

        if (!navContainer || !contentContainer) return;

        // Render navigation buttons
        navContainer.innerHTML = this.categories.map(category => `
            <button class="wiki-nav-btn" data-category="${category.id}">
                ${category.name}
            </button>
        `).join('');

        // Render articles container
        contentContainer.innerHTML = this.articles.map(article => `
            <div class="wiki-article" id="article-${article.id}">
                <h2>${article.title}</h2>
                <div class="article-meta">
                    <i class="far fa-calendar"></i> Обновлено: ${article.updated} | 
                    <i class="far fa-clock"></i> Время чтения: ${article.readingTime}
                </div>
                <div class="article-content">
                    ${article.content}
                </div>
            </div>
        `).join('');

        // Set first button as active
        if (this.categories.length > 0) {
            const firstButton = navContainer.querySelector('.wiki-nav-btn');
            firstButton.classList.add('active');
        }

        // Add event listeners
        navContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('wiki-nav-btn')) {
                const category = e.target.dataset.category;
                this.setActiveCategory(category);
            }
        });
    }

    setActiveCategory(categoryId) {
        // Update active button
        document.querySelectorAll('.wiki-nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.category === categoryId);
        });

        // Show articles for this category
        this.showCategoryArticles(categoryId);
    }

    showCategoryArticles(categoryId) {
        // Hide all articles
        document.querySelectorAll('.wiki-article').forEach(article => {
            article.classList.remove('active');
        });

        // Show articles for the selected category
        const categoryArticles = this.articles.filter(article => 
            article.category === categoryId
        );

        if (categoryArticles.length > 0) {
            // Show the first article in the category
            this.renderArticle(categoryArticles[0].id);
        }
    }

    renderArticle(articleId) {
        // Hide all articles
        document.querySelectorAll('.wiki-article').forEach(article => {
            article.classList.remove('active');
        });

        // Show selected article
        const articleElement = document.getElementById(`article-${articleId}`);
        if (articleElement) {
            articleElement.classList.add('active');
            this.currentArticle = articleId;
        }
    }

    showError(message) {
        const container = document.getElementById('wiki-content');
        if (container) {
            container.innerHTML = `
                <div class="error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${message}</p>
                </div>
            `;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new WikiManager();
});
