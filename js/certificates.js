// Certificates data and functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Certificates page loaded');
    initializeCertificates();
    initializeFilters();
    initializeSearch();
    updateStatistics();
});

// SVG иконки
const pdfIconSVG = `
    <svg class="pdf-icon" viewBox="0 0 384 512" fill="#e74c3c">
        <path d="M369.9 97.9L286 14C277 5 264.8-.1 252.1-.1H48C21.5 0 0 21.5 0 48v416c0 26.5 21.5 48 48 48h288c26.5 0 48-21.5 48-48V131.9c0-12.7-5.1-25-14.1-34zM332.1 128H256V51.9l76.1 76.1zM48 464V48h160v104c0 13.3 10.7 24 24 24h104v288H48zm250.2-143.7c-12.2-12-47-8.7-64.4-6.5-17.2-10.5-28.7-25-36.8-46.3 3.9-16.1 10.1-40.6 5.4-56-4.2-26.2-37.8-23.6-42.6-5.9-4.4 16.1-.4 38.5 7 67.1-10 23.9-24.9 56-35.4 74.4-20 10.3-47 26.2-51 46.2-3.3 15.8 26 55.2 76.1-31.2 22.4-7.4 46.8-16.5 68.4-20.1 18.9 10.2 41 17 55.8 17 25.5 0 28-28.2 17.5-38.7zm-198.1 77.8c5.1-13.7 24.5-29.5 30.4-35-19 30.3-30.4 35.7-30.4 35zm81.6-190.6c7.4 0 6.7 32.1 1.8 40.8-4.4-13.9-4.3-40.8-1.8-40.8zm-24.4 136.6c9.7-16.9 18-37 24.7-54.7 8.3-15.1 20.8-28.9 30.9-30.9 7.1 15.8 2 73.3 12.1 73.3 5.4 0 9.5-17.8 12.2-42.3 13.4-4.2 26-7.4 38.3-9.9-5.5 15.8-19.4 47.2-35.7 69-23 10.7-42.2 5.5-61.6-4.5z"/>
    </svg>
`;

const downloadIconSVG = `
    <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
        <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
    </svg>
`;

const expandIconSVG = `
    <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
        <path d="M16 6l-1.41 1.41L17.17 11H8v2h9.17l-2.58 2.59L16 18l5-5z"/>
    </svg>
`;

// Real certificates data with your actual PDF files
const certificatesData = [
    {
        id: 1,
        title: "7 навыков высокоэффективных людей",
        file: "images/7-habits-effective-people.pdf",
        type: "pdf",
        category: "management",
        organization: "FranklinCovey",
        date: "2023",
        description: "Классика управления временем и личной эффективности",
        skills: ["Тайм-менеджмент", "Личная эффективность", "Привычки"]
    },
    {
        id: 2,
        title: "7 законов развития",
        file: "images/7-laws-development.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-школа",
        date: "2023",
        description: "Фундаментальные законы личностного и профессионального роста",
        skills: ["Развитие", "Личностный рост", "Профессионализм"]
    },
    {
        id: 3,
        title: "13 столпов Adizes",
        file: "images/adizes-13-pillars.pdf",
        type: "pdf",
        category: "management",
        organization: "Adizes Institute",
        date: "2023",
        description: "Методология управления организационными изменениями",
        skills: ["Управление изменениями", "Организационное развитие", "Менеджмент"]
    },
    {
        id: 4,
        title: "45 татуировок менеджера",
        file: "images/batyrev-45-tattoos.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-практика",
        date: "2023",
        description: "Практические принципы эффективного управления",
        skills: ["Управление командой", "Лидерство", "Практический менеджмент"]
    },
    {
        id: 5,
        title: "Корпоративный жизненный цикл",
        file: "images/corporate-lifecycle.pdf",
        type: "pdf",
        category: "management",
        organization: "Adizes Institute",
        date: "2023",
        description: "Теория жизненных циклов организаций",
        skills: ["Организационное развитие", "Стратегия", "Управление"]
    },
    {
        id: 6,
        title: "Принцип кураторства",
        file: "images/curatorship-principle.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-школа",
        date: "2023",
        description: "Методология наставничества и развития персонала",
        skills: ["Наставничество", "Развитие персонала", "HR"]
    },
    {
        id: 7,
        title: "Диплом коммерческого директора",
        file: "images/diplom-commercial-director.pdf",
        type: "pdf",
        category: "management",
        organization: "Профессиональная переподготовка",
        date: "2023",
        description: "Диплом о профессиональной переподготовке по специальности Коммерческий директор",
        skills: ["Коммерция", "Управление", "Стратегия"]
    },
    {
        id: 8,
        title: "Гарвардские переговоры",
        file: "images/harvard-negotiations.pdf",
        type: "pdf",
        category: "management",
        organization: "Harvard Business School",
        date: "2023",
        description: "Методология Гарвардской школы переговоров",
        skills: ["Переговоры", "Коммуникации", "Психология"]
    },
    {
        id: 9,
        title: "Менеджмент 21 века",
        file: "images/management-21-century.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-школа",
        date: "2024",
        description: "Современные подходы к управлению в цифровую эпоху",
        skills: ["Современный менеджмент", "Инновации", "Цифровая трансформация"]
    },
    {
        id: 10,
        title: "Менеджмент спецназа",
        file: "images/management-special-forces.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-практика",
        date: "2023",
        description: "Принципы управления из практики специальных подразделений",
        skills: ["Лидерство", "Оперативное управление", "Командообразование"]
    },
    {
        id: 11,
        title: "Инструменты McKinsey",
        file: "images/mckinsey-tools.pdf",
        type: "pdf",
        category: "analytics",
        organization: "McKinsey & Company",
        date: "2023",
        description: "Аналитические инструменты и фреймворки консалтинговой компании",
        skills: ["Аналитика", "Фреймворки", "Бизнес-анализ"]
    },
    {
        id: 12,
        title: "Практика продаж",
        file: "images/sales-practice.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-школа",
        date: "2023",
        description: "Практические методики и техники продаж",
        skills: ["Продажи", "Коммерция", "Переговоры"]
    },
    {
        id: 13,
        title: "Аудит тайм-менеджмента",
        file: "images/time-management%20audit.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-практика",
        date: "2023",
        description: "Методика аудита и анализа системы управления временем",
        skills: ["Тайм-менеджмент", "Аудит", "Эффективность"]
    },
    {
        id: 14,
        title: "Делегирование в тайм-менеджменте",
        file: "images/time-management-delegation.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-практика",
        date: "2023",
        description: "Эффективные методики делегирования задач",
        skills: ["Делегирование", "Тайм-менеджмент", "Управление командой"]
    },
    {
        id: 15,
        title: "Исполнение в тайм-менеджменте",
        file: "images/time-management-execution.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-практика",
        date: "2023",
        description: "Методики эффективного исполнения задач и проектов",
        skills: ["Исполнение", "Проекты", "Тайм-менеджмент"]
    },
    {
        id: 16,
        title: "Приоритизация в тайм-менеджменте",
        file: "images/time-management-prioritization.pdf",
        type: "pdf",
        category: "management",
        organization: "Бизнес-практика",
        date: "2023",
        description: "Системы расстановки приоритетов и фокусировки",
        skills: ["Приоритизация", "Фокусировка", "Тайм-менеджмент"]
    },
    {
        id: 17,
        title: "Поиск призвания",
        file: "images/vocation-finding.pdf",
        type: "pdf",
        category: "management",
        organization: "Карьерный консалтинг",
        date: "2023",
        description: "Методики поиска профессионального призвания и самореализации",
        skills: ["Карьера", "Самореализация", "Личностный рост"]
    }
];

function initializeCertificates() {
    const container = document.getElementById('certificatesContainer');
    if (!container) {
        console.error('Container not found');
        return;
    }
    
    container.innerHTML = '';
    
    certificatesData.forEach(certificate => {
        const certificateCard = createCertificateCard(certificate);
        container.appendChild(certificateCard);
    });
    
    console.log('Certificates initialized:', certificatesData.length);
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
            ${pdfIconSVG}
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
                ${pdfIconSVG}
                Открыть PDF
            </button>
            <button class="certificate-btn secondary" onclick="downloadPdf('${certificate.file}', '${certificate.title}')">
                ${downloadIconSVG}
                Скачать
            </button>
        `;
    } else {
        actions.innerHTML = `
            <button class="certificate-btn primary" onclick="viewCertificate('${certificate.file}', '${certificate.title}')">
                ${expandIconSVG}
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

// PDF functions
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
