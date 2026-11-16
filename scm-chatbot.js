// SCM ChatBot - Intelligent Assistant
class SCMChatBot {
    constructor() {
        this.isVisible = false;
        this.isTyping = false;
        this.messageHistory = [];
        this.init();
    }

    init() {
        this.createWidget();
        this.loadFromLocalStorage();
        this.bindEvents();
        this.showWelcomeMessage();
    }

    createWidget() {
        // Создаем контейнер чат-бота
        this.container = document.createElement('div');
        this.container.id = 'scm-chatbot';
        this.container.innerHTML = `
            <div class="chatbot-header">
                <div class="chatbot-header-content">
                    <div class="chatbot-avatar">SCM</div>
                    <div class="chatbot-title">
                        <h3>SCM Assistant</h3>
                        <div class="status">
                            <span class="status-dot"></span>
                            Online
                        </div>
                    </div>
                </div>
                <button class="close-btn" title="Закрыть">×</button>
            </div>
            <div class="chatbot-body">
                <div class="messages-container" id="chatbot-messages">
                    <!-- Сообщения будут здесь -->
                </div>
                <div class="quick-options">
                    <div class="quick-options-title">Можете спросить:</div>
                    <div class="quick-options-buttons">
                        <button class="quick-option" data-option="projects">📁 Проекты</button>
                        <button class="quick-option" data-option="technologies">⚡ Технологии</button>
                        <button class="quick-option" data-option="contacts">📞 Контакты</button>
                        <button class="quick-option" data-option="services">🛠️ Услуги</button>
                    </div>
                </div>
                <div class="input-area">
                    <input type="text" id="chatbot-input" placeholder="Напишите ваше сообщение..." maxlength="500">
                    <button id="chatbot-send" title="Отправить">➤</button>
                </div>
            </div>
        `;
        
        // Создаем кнопку для открытия чата
        this.toggleBtn = document.createElement('button');
        this.toggleBtn.id = 'scm-chatbot-toggle';
        this.toggleBtn.innerHTML = '💬';
        this.toggleBtn.title = 'SCM Assistant';
        this.toggleBtn.classList.add('pulse');

        document.body.appendChild(this.toggleBtn);
        document.body.appendChild(this.container);
    }

    bindEvents() {
        // Кнопка открытия/закрытия
        this.toggleBtn.addEventListener('click', () => this.toggle());
        this.container.querySelector('.close-btn').addEventListener('click', () => this.hide());

        // Быстрые опции
        this.container.querySelectorAll('.quick-option').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const option = e.target.dataset.option;
                this.handleQuickOption(option);
            });
        });

        // Отправка сообщения
        this.container.querySelector('#chatbot-send').addEventListener('click', () => this.sendMessage());
        
        const input = this.container.querySelector('#chatbot-input');
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        input.addEventListener('input', () => {
            const sendBtn = this.container.querySelector('#chatbot-send');
            sendBtn.disabled = !input.value.trim();
        });

        // Закрытие по клику вне чата
        document.addEventListener('click', (e) => {
            if (this.isVisible && 
                !this.container.contains(e.target) && 
                !this.toggleBtn.contains(e.target)) {
                this.hide();
            }
        });

        // Обработка Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isVisible) {
                this.hide();
            }
        });
    }

    toggle() {
        this.isVisible = !this.isVisible;
        this.container.classList.toggle('active', this.isVisible);
        this.toggleBtn.classList.toggle('pulse', !this.isVisible);
        
        if (this.isVisible) {
            this.container.querySelector('#chatbot-input').focus();
        }
    }

    hide() {
        this.isVisible = false;
        this.container.classList.remove('active');
        this.toggleBtn.classList.add('pulse');
    }

    showWelcomeMessage() {
        if (this.messageHistory.length === 0) {
            this.addMessage('Добро пожаловать! Я SCM Assistant. Готов помочь с вопросами о наших проектах, технологиях и услугах.', 'bot');
        } else {
            // Показываем историю сообщений
            this.messageHistory.forEach(msg => {
                this.addMessage(msg.text, msg.sender, false);
            });
        }
    }

    handleQuickOption(option) {
        const optionTexts = {
            projects: 'Проекты',
            technologies: 'Технологии', 
            contacts: 'Контакты',
            services: 'Услуги'
        };

        this.addMessage(optionTexts[option], 'user');
        this.showTypingIndicator();
        
        setTimeout(() => {
            this.removeTypingIndicator();
            const response = this.generateResponse(option);
            this.addMessage(response, 'bot');
        }, 1000 + Math.random() * 1000);
    }

    sendMessage() {
        const input = this.container.querySelector('#chatbot-input');
        const message = input.value.trim();
        
        if (message && !this.isTyping) {
            this.addMessage(message, 'user');
            input.value = '';
            this.container.querySelector('#chatbot-send').disabled = true;
            
            this.showTypingIndicator();
            
            // Имитация задержки ответа
            setTimeout(() => {
                this.removeTypingIndicator();
                const response = this.generateResponse(message);
                this.addMessage(response, 'bot');
            }, 1000 + Math.random() * 2000);
        }
    }

    showTypingIndicator() {
        if (this.isTyping) return;
        
        this.isTyping = true;
        const messagesContainer = this.container.querySelector('#chatbot-messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    removeTypingIndicator() {
        this.isTyping = false;
        const typingIndicator = this.container.querySelector('#typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    generateResponse(message) {
        const lowerMessage = typeof message === 'string' ? message.toLowerCase() : message;
        
        const responses = {
            projects: `🚀 **Наши ключевые проекты:**\n\n• **SCM Analytics Platform** - платформа для анализа цепочек поставок с AI\n• **Logistics Optimizer** - система оптимизации маршрутов и запасов\n• **Blockchain Tracker** - отслеживание товаров через блокчейн\n• **IoT Monitoring** - мониторинг условий хранения и транспортировки\n\nКакой проект вас интересует больше?`,

            technologies: `⚡ **Используемые технологии:**\n\n• **Искусственный интеллект** - прогнозирование спроса и оптимизация\n• **Blockchain** - прозрачность и безопасность цепочек\n• **IoT** - датчики для мониторинга в реальном времени\n• **Cloud Computing** - масштабируемая инфраструктура\n• **Big Data Analytics** - анализ больших объемов данных\n\nХотите узнать подробнее о конкретной технологии?`,

            contacts: `📞 **Контакты для связи:**\n\n**Телефон:** +7 (999) 123-45-67\n**Email:** info@scm-company.ru\n**Адрес:** Москва, ул. Логистическая, 15\n**Website:** www.scm-company.ru\n\n⏰ **Часы работы:**\nПн-Пт: 9:00-18:00\nСб-Вс: выходной\n\nПредпочитаете онлайн-встречу?`,

            services: `🛠️ **Наши услуги:**\n\n• **SCM консалтинг** - анализ и оптимизация цепочек\n• **Внедрение систем** - автоматизация процессов\n• **Аналитика** - отчетность и прогнозирование\n• **Обучение** - тренинг для вашей команды\n• **Поддержка** - техническая поддержка 24/7\n\nКакая услуга вас интересует?`
        };

        // Если message - это ключ из responses
        if (responses[lowerMessage]) {
            return responses[lowerMessage];
        }

        // Обработка текстовых сообщений
        if (lowerMessage.includes('привет') || lowerMessage.includes('здравств') || lowerMessage.includes('добрый')) {
            return 'Здравствуйте! Рад вас видеть. Чем могу помочь? Можете спросить о наших проектах, технологиях или услугах.';
        } else if (lowerMessage.includes('проект')) {
            return responses.projects;
        } else if (lowerMessage.includes('технолог')) {
            return responses.technologies;
        } else if (lowerMessage.includes('контакт') || lowerMessage.includes('связаться') || lowerMessage.includes('телефон')) {
            return responses.contacts;
        } else if (lowerMessage.includes('услуг') || lowerMessage.includes('сервис')) {
            return responses.services;
        } else if (lowerMessage.includes('спасибо') || lowerMessage.includes('благодар')) {
            return 'Пожалуйста! Всегда рад помочь. Если возникнут еще вопросы - обращайтесь! 😊';
        } else if (lowerMessage.includes('пока') || lowerMessage.includes('до свидан')) {
            return 'До свидания! Буду рад помочь снова. Хорошего дня! 👋';
        } else {
            return 'Интересный вопрос! Пока я могу помочь с информацией о проектах, технологиях, услугах или контактах. Что именно вас интересует?';
        }
    }

    addMessage(text, sender, saveToHistory = true) {
        const messagesContainer = this.container.querySelector('#chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const time = new Date().toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        messageDiv.innerHTML = `
            <div class="message-text">${this.formatMessage(text)}</div>
            <div class="message-time">${time}</div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Сохраняем в историю
        if (saveToHistory) {
            this.messageHistory.push({
                text: text,
                sender: sender,
                time: time
            });
            this.saveToLocalStorage();
        }
    }

    formatMessage(text) {
        // Простой markdown-like форматирование
        return String(text).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'})[c])
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    saveToLocalStorage() {
        try {
            localStorage.setItem('scm-chatbot-history', JSON.stringify(this.messageHistory));
        } catch (e) {
            console.warn('Не удалось сохранить историю чата:', e);
        }
    }

    loadFromLocalStorage() {
        try {
            const saved = localStorage.getItem('scm-chatbot-history');
            if (saved) {
                this.messageHistory = JSON.parse(saved);
                // Ограничиваем историю последними 50 сообщениями
                if (this.messageHistory.length > 50) {
                    this.messageHistory = this.messageHistory.slice(-50);
                }
            }
        } catch (e) {
            console.warn('Не удалось загрузить историю чата:', e);
            this.messageHistory = [];
        }
    }

    // Дополнительные методы для управления извне
    show() {
        this.isVisible = true;
        this.container.classList.add('active');
        this.toggleBtn.classList.remove('pulse');
        this.container.querySelector('#chatbot-input').focus();
    }

    // Метод для програмного вызова ответов
    triggerResponse(option) {
        this.handleQuickOption(option);
    }
}

// Автоматическая инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    window.scmChatBot = new SCMChatBot();
    
    // Добавляем глобальные методы для управления ботом
    window.showSCMChat = function() {
        window.scmChatBot.show();
    };
    
    window.hideSCMChat = function() {
        window.scmChatBot.hide();
    };
});

// Поддержка модульной системы
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SCMChatBot;
}
