// Certificates data and functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeCertificates();
    initializeFilters();
    initializeSearch();
    updateStatistics();
});

// Автоматическое создание карточек для всех PDF файлов
const certificatesData = [
    // Основные сертификаты - добавьте сюда ВСЕ ваши PDF файлы
    {
        id: 1,
        title: "MBA в логистике и управлении цепями поставок",
        file: "images/mba-logistics.pdf",
        type: "pdf",
        category: "scm",
        organization: "Российская академия народного хозяйства",
        date: "2023",
        description: "Магистр делового администрирования со специализацией в логистике и SCM",
        skills: ["Стратегическое управление", "Цепочка поставок", "Логистика"]
    },
    {
        id: 2,
        title: "Сертифицированный специалист по цифровой трансформации",
        file: "images/digital-transformation.pdf",
        type: "pdf",
        category: "digital",
        organization: "Digital Transformation Institute",
        date: "2024",
        description: "Сертификация в области цифровой трансформации бизнес-процессов",
        skills: ["Цифровизация", "Бизнес-процессы", "Инновации"]
    },
    {
        id: 3,
        title: "AI и машинное обучение в бизнесе",
        file: "images/ai-business.pdf",
        type: "pdf",
        category: "analytics",
        organization: "Data Science Academy",
        date: "2023",
        description: "Применение искусственного интеллекта и ML для оптимизации бизнес-процессов",
        skills: ["Машинное обучение", "AI", "Аналитика данных"]
    },
    {
        id: 4,
        title: "Диплом о высшем образовании",
        file: "images/diploma.pdf",
        type: "pdf",
        category: "management",
        organization: "Университет",
        date: "2010",
        description: "Диплом специалиста по управлению цепями поставок",
        skills: ["Высшее образование", "Фундаментальные знания", "Специализация"]
    },
    {
        id: 5,
        title: "Управление проектами по методологии PMI",
        file: "images/pmi-certification.pdf",
        type: "pdf",
        category: "management",
        organization: "Project Management Institute",
        date: "2022",
        description: "Сертификация по управлению проектами согласно стандартам PMI",
        skills: ["Управление проектами", "PMBOK", "Agile"]
    },
    {
        id: 6,
        title: "Сертификат по бережливому производству",
        file: "images/lean-manufacturing.pdf",
        type: "pdf",
        category: "scm",
        organization: "Lean Six Sigma Institute",
        date: "2023",
        description: "Сертификация в области бережливого производства и оптимизации процессов",
        skills: ["Бережливое производство", "Kaizen", "Оптимизация"]
    },
    {
        id: 7,
        title: "Корпоративные финансы и управление затратами",
        file: "images/corporate-finance.pdf",
        type: "pdf",
        category: "management",
        organization: "Financial Management Association",
        date: "2022",
        description: "Сертификация в области корпоративных финансов и управления затратами",
        skills: ["Финансы", "Управление затратами", "Бюджетирование"]
    },
    {
        id: 8,
        title: "Большие данные в цепях поставок",
        file: "images/big-data-sc.pdf",
        type: "pdf",
        category: "analytics",
        organization: "Big Data Analytics Council",
        date: "2024",
        description: "Сертификация по применению больших данных в управлении цепями поставок",
        skills: ["Big Data", "Аналитика", "SCM аналитика"]
    },
    {
        id: 9,
        title: "Цифровые двойники в логистике",
        file: "images/digital-twins.pdf",
        type: "pdf",
        category: "digital",
        organization: "Digital Innovation Lab",
        date: "2024",
        description: "Сертификация по созданию и использованию цифровых двойников в логистике",
        skills: ["Цифровые двойники", "Моделирование", "Логистика"]
    },
    {
        id: 10,
        title: "Сертификат по управлению запасами",
        file: "images/inventory-management.pdf",
        type: "pdf",
        category: "scm",
        organization: "Supply Chain Council",
        date: "2023",
        description: "Сертификация в области управления запасами и оптимизации складских операций",
        skills: ["Управление запасами", "Складские операции", "Оптимизация"]
    },
    {
        id: 11,
        title: "Сертификат по транспортной логистике",
        file: "images/transport-logistics.pdf",
        type: "pdf",
        category: "scm",
        organization: "Logistics Association",
        date: "2022",
        description: "Сертификация в области транспортной логистики и управления перевозками",
        skills: ["Транспортная логистика", "Управление перевозками", "Маршрутизация"]
    },
    {
        id: 12,
        title: "Сертификат по управлению рисками в SCM",
        file: "images/risk-management.pdf",
        type: "pdf",
        category: "management",
        organization: "Risk Management Institute",
        date: "2023",
        description: "Сертификация в области управления рисками в цепях поставок",
        skills: ["Управление рисками", "SCM", "Анализ рисков"]
    }
    // ДОБАВЬТЕ ЗДЕСЬ ВСЕ ОСТАЛЬНЫЕ ВАШИ СЕРТИФИКАТЫ И ДИПЛОМЫ
    // Просто скопируйте структуру выше и замените названия файлов и информацию
];

function initializeCertificates() {
    const container = document.getElementById('certificatesContainer');
    container.innerHTML = '';
    
    certificatesData.forEach(certificate => {
        const certificateCard = createCertificateCard(certificate);
        container.appendChild(certificateCard);
    });
}

function createCertificateCard(certificate) {
    const card = document.createElement('div');
    card.className = 'certificate-card';
    card.setAttribute('data-category', certificate.category);
    card.setAttribute('data-type', certificate.type);
    card.setAttribute('data-title', certificate.title.toLowerCase());
    
    // Preview section
    const preview = document.createElement('div');
    preview.className = 'certificate-preview';
    
    if (certificate.type === 'pdf') {
        preview.innerHTML = `
            <i class="fas fa-file-pdf pdf-icon"></i>
            <div class="pdf-badge">PDF</div>
        `;
    } else {
        preview.innerHTML = `<img src="${certificate.file}" alt="${certificate.title}" loading="lazy">`;
    }
    
    // Info section
    const info = document.createElement('div');
    info.className = 'certificate-info';
    
    const title = document.createElement('h3');
    title.textContent = certificate.title;
    
    const meta = document.createElement('div');
    meta.className = 'certificate-meta';
    meta.innerHTML = `
        <div><strong>Организация:</strong> ${certificate.organization}</div>
        <div><strong>Дата получения:</strong> ${certificate.date}</div>
    `;
    
    const description = document.createElement('div');
    description.className = 'certificate-description';
    description.textContent = certificate.description;
    
    // Skills section
    const skills = document.createElement('div');
    skills.className = 'certificate-skills';
    certificate.skills.forEach(skill => {
        const skillTag = document.createElement('span');
        skillTag.className = 'skill-tag';
        skillTag.textContent = skill;
        skills.appendChild(skillTag);
    });
    
    // Actions section
    const actions = document.createElement('div');
    actions.className = 'certificate-actions';
    
    if (certificate.type === 'pdf') {
        actions.innerHTML = `
            <button class="certificate-btn danger" onclick="openPdf('${certificate.file}')">
                <i class="fas fa-file-pdf"></i>
                Открыть PDF
            </button>
            <button class="certificate-btn secondary" onclick="downloadPdf('${certificate.file}', '${certificate.title}')">
                <i class="fas fa-download"></i>
                Скачать
            </button>
        `;
    } else {
        actions.innerHTML = `
            <button class="certificate-btn primary" onclick="viewCertificate('${certificate.file}', '${certificate.title}')">
                <i class="fas fa-expand"></i>
                Просмотр
            </button>
        `;
    }
    
    // Assemble card
    info.appendChild(title);
    info.appendChild(meta);
    info.appendChild(description);
    info.appendChild(skills);
    info.appendChild(actions);
    
    card.appendChild(preview);
    card.appendChild(info);
    
    return card;
}

function initializeFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            filterButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            
            const filter = this.getAttribute('data-filter');
            filterCertificates(filter);
        });
    });
}

function filterCertificates(filter) {
    const certificates = document.querySelectorAll('.certificate-card');
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    certificates.forEach(card => {
        const category = card.getAttribute('data-category');
        const type = card.getAttribute('data-type');
        const title = card.getAttribute('data-title');
        
        let shouldShow = true;
        
        // Apply category filter
        if (filter !== 'all' && filter !== 'pdf') {
            shouldShow = category === filter;
        } else if (filter === 'pdf') {
            shouldShow = type === 'pdf';
        }
        
        // Apply search filter
        if (shouldShow && searchTerm) {
            shouldShow = title.includes(searchTerm);
        }
        
        card.style.display = shouldShow ? 'block' : 'none';
    });
    
    updateStatistics();
}

function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    
    searchInput.addEventListener('input', function() {
        const activeFilter = document.querySelector('.filter-btn.active');
        const filter = activeFilter ? activeFilter.getAttribute('data-filter') : 'all';
        filterCertificates(filter);
    });
}

function updateStatistics() {
    const visibleCertificates = document.querySelectorAll('.certificate-card[style="display: block"]');
    const totalCertificates = document.querySelectorAll('.certificate-card');
    const pdfCertificates = certificatesData.filter(cert => cert.type === 'pdf');
    const currentYearCertificates = certificatesData.filter(cert => cert.date === '2024');
    
    document.getElementById('total-certificates').textContent = totalCertificates.length;
    document.getElementById('current-year').textContent = currentYearCertificates.length;
    document.getElementById('pdf-count').textContent = pdfCertificates.length;
}

// PDF functions - ИСПРАВЛЕННЫЕ ФУНКЦИИ
function openPdf(pdfPath) {
    console.log('Opening PDF:', pdfPath);
    // Проверяем, существует ли файл
    fetch(pdfPath)
        .then(response => {
            if (response.ok) {
                window.open(pdfPath, '_blank');
            } else {
                alert('Файл не найден: ' + pdfPath + '\nПроверьте путь к файлу.');
            }
        })
        .catch(error => {
            console.error('Error opening PDF:', error);
            alert('Ошибка при открытии файла: ' + pdfPath + '\n' + error.message);
        });
}

function downloadPdf(pdfPath, fileName) {
    console.log('Downloading PDF:', pdfPath);
    fetch(pdfPath)
        .then(response => {
            if (response.ok) {
                const link = document.createElement('a');
                link.href = pdfPath;
                link.download = fileName + '.pdf';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                alert('Файл не найден: ' + pdfPath + '\nПроверьте путь к файлу.');
            }
        })
        .catch(error => {
            console.error('Error downloading PDF:', error);
            alert('Ошибка при скачивании файла: ' + pdfPath + '\n' + error.message);
        });
}

function viewCertificate(imagePath, title) {
    console.log('Viewing certificate:', imagePath);
    fetch(imagePath)
        .then(response => {
            if (response.ok) {
                window.open(imagePath, '_blank');
            } else {
                alert('Файл не найден: ' + imagePath + '\nПроверьте путь к файлу.');
            }
        })
        .catch(error => {
            console.error('Error viewing certificate:', error);
            alert('Ошибка при открытии файла: ' + imagePath + '\n' + error.message);
        });
}

// Initialize certificates
initializeCertificates();
