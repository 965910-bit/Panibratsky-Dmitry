// Tools page functionality

class ToolsManager {
    constructor() {
        this.tools = [];
        this.categories = [];
        this.filteredTools = [];
        this.currentCategory = 'all';
        
        this.initialize();
    }

    async initialize() {
        await this.loadData();
        this.renderCategories();
        this.renderTools();
        this.setupEventListeners();
    }

    async loadData() {
        try {
            const data = await fetch('/data/tools.json');
            if (!data.ok) throw new Error('Failed to load tools data');
            
            const jsonData = await data.json();
            this.tools = jsonData.tools || [];
            this.categories = jsonData.categories || [];
            
        } catch (error) {
            console.error('Error loading tools:', error);
            this.showError('Ошибка загрузки данных инструментов');
        }
    }

    renderCategories() {
        const categoriesContainer = document.getElementById('tools-categories');
        if (!categoriesContainer) return;

        categoriesContainer.innerHTML = `
            <button class="category-btn active" data-category="all">Все инструменты</button>
            ${this.categories.map(category => `
                <button class="category-btn" data-category="${category.id}">${category.name}</button>
            `).join('')}
        `;
    }

    renderTools() {
        const container = document.getElementById('tools-container');
        if (!container) return;

        this.filterTools();

        if (this.filteredTools.length === 0) {
            container.innerHTML = `
                <div class="error">
                    <i class="fas fa-search"></i>
                    <p>Инструменты не найдены</p>
                    <p>Попробуйте выбрать другую категорию</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.filteredTools.map(tool => `
            <div class="tool-card">
                <div class="tool-icon">
                    ${tool.icon}
                </div>
                <h3>${tool.title}</h3>
                <p class="tool-description">${tool.description}</p>
                
                ${tool.features && tool.features.length > 0 ? `
                    <div class="tool-features">
                        <h4>Возможности:</h4>
                        <ul>
                            ${tool.features.map(feature => `
                                <li>${feature}</li>
                            `).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                <a href="${tool.link}" class="tool-link">
                    <i class="fas fa-external-link-alt"></i>
                    Открыть инструмент
                </a>
            </div>
        `).join('');
    }

    filterTools() {
        this.filteredTools = this.tools.filter(tool => {
            return this.currentCategory === 'all' || tool.category === this.currentCategory;
        });

        // Sort by category and title
        this.filteredTools.sort((a, b) => {
            if (a.category !== b.category) {
                return a.category.localeCompare(b.category);
            }
            return a.title.localeCompare(b.title);
        });
    }

    setupEventListeners() {
        // Category buttons
        document.getElementById('tools-categories')?.addEventListener('click', (e) => {
            if (e.target.classList.contains('category-btn')) {
                const category = e.target.dataset.category;
                this.setCategory(category);
            }
        });
    }

    setCategory(category) {
        this.currentCategory = category;
        
        // Update active button
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.category === category);
        });
        
        this.renderTools();
    }

    showError(message) {
        const container = document.getElementById('tools-container');
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
    new ToolsManager();
});
