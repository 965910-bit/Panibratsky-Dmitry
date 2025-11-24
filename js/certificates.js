// Certificates page functionality

class CertificatesManager {
    constructor() {
        this.certificates = [];
        this.categories = [];
        this.filteredCertificates = [];
        this.currentFilter = 'all';
        this.searchTerm = '';
        
        this.initialize();
    }

    async initialize() {
        await this.loadData();
        this.renderFilters();
        this.renderCertificates();
        this.setupEventListeners();
    }

    async loadData() {
        try {
            const data = await fetch('/data/certificates.json');
            if (!data.ok) throw new Error('Failed to load certificates data');
            
            const jsonData = await data.json();
            this.certificates = jsonData.certificates || [];
            this.categories = jsonData.categories || [];
            
        } catch (error) {
            console.error('Error loading certificates:', error);
            this.showError('Ошибка загрузки данных сертификатов');
        }
    }

    renderFilters() {
        const filtersContainer = document.getElementById('certificate-filters');
        if (!filtersContainer) return;

        filtersContainer.innerHTML = `
            <button class="filter-btn active" data-filter="all">Все</button>
            ${this.categories.map(category => `
                <button class="filter-btn" data-filter="${category.id}">${category.name}</button>
            `).join('')}
        `;
    }

    renderCertificates() {
        const container = document.getElementById('certificates-container');
        if (!container) return;

        this.filterCertificates();

        if (this.filteredCertificates.length === 0) {
            container.innerHTML = `
                <div class="error">
                    <i class="fas fa-search"></i>
                    <p>Сертификаты не найдены</p>
                    <p>Попробуйте изменить параметры поиска или фильтрации</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.filteredCertificates.map(certificate => `
            <div class="certificate-card ${certificate.importance === 'high' ? 'diploma-card' : ''}">
                <div class="certificate-icon">
                    ${this.getCertificateIcon(certificate.category)}
                </div>
                <h3>${certificate.title}</h3>
                <div class="certificate-date">
                    <i class="far fa-calendar"></i>
                    ${this.formatDate(certificate.date)}
                </div>
                <div class="certificate-institution">
                    ${certificate.institution}
                </div>
                ${certificate.description ? `
                    <p class="certificate-description">${certificate.description}</p>
                ` : ''}
                ${certificate.skills && certificate.skills.length > 0 ? `
                    <div class="certificate-skills">
                        ${certificate.skills.map(skill => `
                            <span class="skill-tag">${skill}</span>
                        `).join('')}
                    </div>
                ` : ''}
                <a href="${certificate.file}" target="_blank" class="certificate-btn ${certificate.importance === 'high' ? 'diploma-btn' : ''}">
                    <i class="far fa-file-pdf"></i>
                    PDF сертификат
                </a>
            </div>
        `).join('');
    }

    filterCertificates() {
        this.filteredCertificates = this.certificates.filter(certificate => {
            // Apply category filter
            const categoryMatch = this.currentFilter === 'all' || certificate.category === this.currentFilter;
            
            // Apply search filter
            const searchMatch = !this.searchTerm || 
                certificate.title.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
                certificate.skills.some(skill => skill.toLowerCase().includes(this.searchTerm.toLowerCase())) ||
                certificate.institution.toLowerCase().includes(this.searchTerm.toLowerCase());
            
            return categoryMatch && searchMatch;
        });

        // Sort by importance and date
        this.filteredCertificates.sort((a, b) => {
            if (a.importance === 'high' && b.importance !== 'high') return -1;
            if (a.importance !== 'high' && b.importance === 'high') return 1;
            return new Date(b.date) - new Date(a.date);
        });
    }

    getCertificateIcon(categoryId) {
        const icons = {
            'main': '🏆',
            'time-management': '⏱️',
            'management': '💼'
        };
        return icons[categoryId] || '📄';
    }

    formatDate(dateString) {
        const options = { day: 'numeric', month: 'long', year: 'numeric' };
        return new Date(dateString).toLocaleDateString('ru-RU', options);
    }

    setupEventListeners() {
        // Filter buttons
        document.getElementById('certificate-filters')?.addEventListener('click', (e) => {
            if (e.target.classList.contains('filter-btn')) {
                const filter = e.target.dataset.filter;
                this.setFilter(filter);
            }
        });

        // Search input
        document.getElementById('certificate-search')?.addEventListener('input', (e) => {
            this.searchTerm = e.target.value;
            this.renderCertificates();
        });
    }

    setFilter(filter) {
        this.currentFilter = filter;
        
        // Update active button
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });
        
        this.renderCertificates();
    }

    showError(message) {
        const container = document.getElementById('certificates-container');
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
    new CertificatesManager();
});
