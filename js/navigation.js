// Основной скрипт для навигации между разделами
class TrendsNavigation {
    constructor() {
        this.currentContentSection = 'logistics';
        this.currentYear = '2024';
        this.initialized = false;
        
        // Элементы DOM
        this.elements = {
            megaMenu: null,
            trendsLink: null,
            contentSections: [],
            yearNavigations: [],
            subNavLinks: [],
            sidebarNavs: []
        };
    }
    
    // Инициализация
    init() {
        if (this.initialized) return;
        
        this.cacheElements();
        this.setupEventListeners();
        this.handleInitialHash();
        this.initialized = true;
        
        console.log('TrendsNavigation initialized successfully');
    }
    
    // Кэширование элементов DOM
    cacheElements() {
        this.elements.megaMenu = document.getElementById('trends-mega-menu');
        this.elements.trendsLink = document.getElementById('nav-logistics');
        
        // Собираем все секции контента
        this.elements.contentSections = {
            logistics: document.getElementById('logistics-content'),
            personnel: document.getElementById('personnel-content'),
            academy: document.getElementById('academy-content'),
            strategy: document.getElementById('strategy-content')
        };
        
        // Собираем навигации по годам
        this.elements.yearNavigations = {
            logistics: document.getElementById('logistics-years'),
            personnel: document.getElementById('personnel-years'),
            academy: document.getElementById('academy-years'),
            strategy: document.getElementById('strategy-years')
        };
        
        // Собираем ссылки поднавигации
        this.elements.subNavLinks = {
            logistics: document.getElementById('sub-nav-logistics'),
            personnel: document.getElementById('sub-nav-personnel'),
            academy: document.getElementById('sub-nav-academy'),
            strategy: document.getElementById('sub-nav-strategy')
        };
        
        // Собираем навигации в сайдбаре
        this.elements.sidebarNavs = {
            logistics: document.getElementById('logistics-nav-year'),
            personnel: document.getElementById('personnel-nav-year'),
            academy: document.getElementById('academy-nav-year'),
            strategy: document.getElementById('strategy-nav-year')
        };
    }
    
    // Настройка обработчиков событий
    setupEventListeners() {
        // Мега-меню
        if (this.elements.trendsLink && this.elements.megaMenu) {
            this.setupMegaMenu();
        }
        
        // Ссылки в мега-меню
        document.querySelectorAll('.mega-links a').forEach(link => {
            link.addEventListener('click', (e) => this.handleMegaLinkClick(e));
        });
        
        // Вкладки лет для каждого раздела
        this.setupYearTabs();
        
        // Поднавигация
        this.setupSubNavigation();
        
        // Навигация в сайдбаре
        this.setupSidebarNavigation();
        
        // Обработка изменения hash в URL
        window.addEventListener('hashchange', () => this.handleHashChange());
    }
    
    // Настройка мега-меню
    setupMegaMenu() {
        this.elements.trendsLink.addEventListener('mouseenter', () => {
            this.elements.megaMenu.classList.add('active');
        });
        
        this.elements.trendsLink.addEventListener('mouseleave', () => {
            setTimeout(() => {
                if (!this.elements.megaMenu.matches(':hover')) {
                    this.elements.megaMenu.classList.remove('active');
                }
            }, 100);
        });
        
        this.elements.megaMenu.addEventListener('mouseleave', () => {
            this.elements.megaMenu.classList.remove('active');
        });
    }
    
    // Настройка вкладок лет
    setupYearTabs() {
        const sections = ['logistics', 'personnel', 'academy', 'strategy'];
        
        sections.forEach(section => {
            const yearTabs = document.querySelectorAll(`#${section}-years .year-tab`);
            yearTabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    e.preventDefault();
                    const year = tab.dataset.year;
                    this.switchYear(year, section);
                });
            });
        });
    }
    
    // Настройка поднавигации
    setupSubNavigation() {
        const sections = ['logistics', 'personnel', 'academy', 'strategy'];
        
        sections.forEach(section => {
            const link = this.elements.subNavLinks[section];
            if (link) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.switchContentSection(section);
                });
            }
        });
    }
    
    // Настройка навигации в сайдбаре
    setupSidebarNavigation() {
        const sections = ['logistics', 'personnel', 'academy', 'strategy'];
        
        sections.forEach(section => {
            const nav = this.elements.sidebarNavs[section];
            if (nav) {
                nav.querySelectorAll('a').forEach(link => {
                    link.addEventListener('click', (e) => {
                        e.preventDefault();
                        const year = link.dataset.year;
                        
                        if (section !== this.currentContentSection) {
                            this.switchContentSection(section);
                        }
                        
                        this.switchYear(year, section);
                        
                        // Плавная прокрутка
                        const targetSection = document.getElementById(`${section}-${year}`);
                        if (targetSection) {
                            window.scrollTo({
                                top: targetSection.offsetTop - 140,
                                behavior: 'smooth'
                            });
                        }
                    });
                });
            }
        });
    }
    
    // Обработка кликов по ссылкам в мега-меню
    handleMegaLinkClick(e) {
        e.preventDefault();
        const link = e.currentTarget;
        const section = link.dataset.section;
        const year = link.dataset.year || '2024';
        
        if (section) {
            this.switchContentSection(section);
            this.switchYear(year, section);
            
            // Плавная прокрутка
            const targetId = link.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 140,
                    behavior: 'smooth'
                });
            }
        }
    }
    
    // Переключение раздела контента
    switchContentSection(section) {
        // Сохраняем текущую секцию
        this.currentContentSection = section;
        
        // Скрываем все секции
        Object.values(this.elements.contentSections).forEach(sec => {
            if (sec) sec.classList.remove('active');
        });
        
        // Показываем выбранную секцию
        if (this.elements.contentSections[section]) {
            this.elements.contentSections[section].classList.add('active');
        }
        
        // Обновляем навигацию по годам
        this.updateYearNavigation(section);
        
        // Обновляем поднавигацию
        this.updateSubNavigation(section);
        
        // Обновляем навигацию в сайдбаре
        this.updateSidebarNavigation(section);
        
        // Закрываем мега-меню
        if (this.elements.megaMenu) {
            this.elements.megaMenu.classList.remove('active');
        }
        
        // Обновляем URL
        window.history.pushState(null, null, `#${section}`);
        
        // Анимация прогресс-баров
        setTimeout(() => this.animateProgressBars(), 300);
    }
    
    // Переключение года в разделе
    switchYear(year, section = this.currentContentSection) {
        this.currentYear = year;
        
        // Скрываем все годовые секции в текущем разделе
        const yearSections = document.querySelectorAll(`#${section}-content .year-section`);
        yearSections.forEach(sec => {
            sec.classList.remove('active');
        });
        
        // Показываем выбранную годовую секцию
        const targetSection = document.getElementById(`${section}-${year}`);
        if (targetSection) {
            targetSection.classList.add('active');
            
            // Обновляем URL
            window.history.pushState(null, null, `#${section}-${year}`);
        }
        
        // Обновляем активные вкладки лет
        this.updateYearTabs(section, year);
        
        // Обновляем активные ссылки в сайдбаре
        this.updateSidebarYearLinks(section, year);
    }
    
    // Обновление навигации по годам
    updateYearNavigation(section) {
        // Скрываем все навигации
        Object.values(this.elements.yearNavigations).forEach(nav => {
            if (nav) nav.style.display = 'none';
        });
        
        // Показываем нужную навигацию
        if (this.elements.yearNavigations[section]) {
            this.elements.yearNavigations[section].style.display = 'flex';
        }
    }
    
    // Обновление активных вкладок лет
    updateYearTabs(section, year) {
        const yearTabs = document.querySelectorAll(`#${section}-years .year-tab`);
        yearTabs.forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.year === year) {
                tab.classList.add('active');
            }
        });
    }
    
    // Обновление поднавигации
    updateSubNavigation(section) {
        // Удаляем активный класс у всех ссылок
        Object.values(this.elements.subNavLinks).forEach(link => {
            if (link) link.classList.remove('active');
        });
        
        // Добавляем активный класс к выбранной ссылке
        if (this.elements.subNavLinks[section]) {
            this.elements.subNavLinks[section].classList.add('active');
        }
    }
    
    // Обновление навигации в сайдбаре
    updateSidebarNavigation(section) {
        // Скрываем все навигации
        Object.values(this.elements.sidebarNavs).forEach(nav => {
            if (nav) nav.style.display = 'none';
        });
        
        // Показываем нужную навигацию
        if (this.elements.sidebarNavs[section]) {
            this.elements.sidebarNavs[section].style.display = 'block';
        }
    }
    
    // Обновление активных ссылок лет в сайдбаре
    updateSidebarYearLinks(section, year) {
        const sidebarLinks = document.querySelectorAll(`#${section}-nav-year a`);
        sidebarLinks.forEach(link => {
            link.classList.remove('active');
            if (link.dataset.year === year) {
                link.classList.add('active');
            }
        });
    }
    
    // Анимация прогресс-баров
    animateProgressBars() {
        const progressFills = document.querySelectorAll('.progress-fill');
        progressFills.forEach(fill => {
            const width = fill.style.width;
            fill.style.width = '0';
            setTimeout(() => {
                fill.style.width = width;
            }, 100);
        });
    }
    
    // Обработка начального hash
    handleInitialHash() {
        const hash = window.location.hash.substring(1);
        
        if (hash) {
            let section = 'logistics';
            let year = '2024';
            
            // Проверяем, является ли hash годом в конкретном разделе
            const sectionMatch = hash.match(/^(logistics|personnel|academy|strategy)-(\d{4})$/);
            if (sectionMatch) {
                section = sectionMatch[1];
                year = sectionMatch[2];
                this.switchContentSection(section);
                this.switchYear(year, section);
                
                // Прокручиваем к секции
                setTimeout(() => {
                    const targetElement = document.getElementById(hash);
                    if (targetElement) {
                        window.scrollTo({
                            top: targetElement.offsetTop - 140,
                            behavior: 'smooth'
                        });
                    }
                }, 300);
            }
            
            // Проверяем, является ли hash просто разделом
            else if (['logistics', 'personnel', 'academy', 'strategy'].includes(hash)) {
                this.switchContentSection(hash);
            }
        }
    }
    
    // Обработка изменения hash
    handleHashChange() {
        this.handleInitialHash();
    }
    
    // Обновление текущей даты
    updateCurrentDate() {
        const currentDateElement = document.querySelector('.current-date');
        if (currentDateElement) {
            const now = new Date();
            const options = { day: '2-digit', month: '2-digit', year: 'numeric' };
            const formattedDate = now.toLocaleDateString('ru-RU', options);
            currentDateElement.innerHTML = `<i class="far fa-calendar"></i> Актуально на ${formattedDate}`;
        }
    }
}

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    const trendsNav = new TrendsNavigation();
    trendsNav.init();
    trendsNav.updateCurrentDate();
});

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TrendsNavigation;
}
