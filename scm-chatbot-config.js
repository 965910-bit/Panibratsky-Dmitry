// Конфигурация SCM ChatBot
const SCM_CHATBOT_CONFIG = {
    // Основные настройки
    companyName: "SCM Company",
    primaryColor: "#007bff",
    secondaryColor: "#0056b3",
    
    // Настройки бота
    botName: "SCM Assistant",
    welcomeMessage: "Добро пожаловать! Я SCM Assistant. Готов помочь с вопросами о наших проектах, технологиях и услугах.",
    
    // Контакты
    contacts: {
        phone: "+7 (999) 123-45-67",
        email: "info@scm-company.ru",
        address: "Москва, ул. Логистическая, 15",
        website: "www.scm-company.ru"
    },
    
    // Функциональность
    features: {
        saveHistory: true,
        typingIndicator: true,
        quickReplies: true,
        autoOpen: false // Автоматическое открытие при загрузке
    },
    
    // Тексты ответов
    responses: {
        projects: "...", // можно вынести тексты сюда
        technologies: "...",
        contacts: "...",
        services: "..."
    }
};
