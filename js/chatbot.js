// SCM ChatBot - отдельный файл для всех страниц
class SCMChatBot {
    constructor() {
        this.isVisible = false;
        this.isTyping = false;
        this.conversationHistory = [];
        this.init();
    }

    init() {
        this.createChatbotHTML();
        this.bindEvents();
        this.loadFromLocalStorage();
    }

    createChatbotHTML() {
        // Создаем контейнер чат-бота
        const chatbotContainer = document.createElement('div');
        chatbotContainer.id = 'chatbot-container';
        chatbotContainer.innerHTML = `
            <!-- Кнопка открытия чата -->
            <div id="chatbot-toggle">
                <i class="fas fa-robot"></i>
                <span class="chatbot-pulse"></span>
            </div>

            <!-- Окно чата -->
            <div id="chatbot-window">
                <!-- Заголовок -->
                <div id="chatbot-header">
                    <div class="chatbot-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="chatbot-info">
                        <h4>SCM Assistant</h4>
                        <span class="status online">Online</span>
                    </div>
                    <button id="chatbot-close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <!-- Сообщения -->
                <div id="chatbot-messages">
                    <div class="message bot-message">
                        <div class="message-avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="message-content">
                            <p>Привет! Я SCM Assistant 🤖</p>
                            <p>Помогу вам связаться с Дмитрием или ответить на вопросы по управлению цепями поставок. Чем могу помочь?</p>
                            <div class="quick-replies">
                                <button class="quick-reply" data-reply="Связаться с Дмитрием">👋 Связаться</button>
                                <button class="quick-reply" data-reply="SCM экспертиза">📊 SCM экспертиза</button>
                                <button class="quick-reply" data-reply="Опыт работы">💼 Опыт работы</button>
                            </div>
                            <span class="message-time">${new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                    </div>
                </div>

                <!-- Поле ввода -->
                <div id="chatbot-input-container">
                    <div class="input-wrapper">
                        <input type="text" id="chatbot-input" placeholder="Напишите ваше сообщение..." maxlength="500">
                        <button id="chatbot-send">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                    <div class="chatbot-suggestions">
                        <span>Можете спросить:</span>
                        <button class="suggestion" data-question="Какие проекты вы реализовали?">Проекты</button>
                        <button class="suggestion" data-question="Какие технологии используете?">Технологии</button>
                        <button class="suggestion" data-question="Как с вами связаться?">Контакты</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(chatbotContainer);
    }

    bindEvents() {
        const chatbotToggle = document.getElementById('chatbot-toggle');
        const chatbotWindow = document.getElementById('chatbot-window');
        const chatbotClose = document.getElementById('chatbot-close');
        const chatbotInput = document.getElementById('chatbot-input');
        const chatbotSend = document.getElementById('chatbot-send');

        // Открытие/закрытие чата
        chatbotToggle.addEventListener('click', () => this.toggleChat());
        chatbotClose.addEventListener('click', () => this.hideChat());

        // Отправка сообщения
        chatbotSend.addEventListener('click', () => this.sendMessage());
        chatbotInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // Быстрые ответы
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-reply')) {
                const reply = e.target.getAttribute('data-reply');
                this.handleQuickReply(reply);
            }
        });

        // Подсказки
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion')) {
                const question = e.target.getAttribute('data-question');
                document.getElementById('chatbot-input').value = question;
                document.getElementById('chatbot-input').focus();
            }
        });

        // Закрытие по клику вне чата
        document.addEventListener('click', (e) => {
            if (this.isVisible && 
                !document.getElementById('chatbot-container').contains(e.target)) {
                this.hideChat();
            }
        });

        // Обработка Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isVisible) {
                this.hideChat();
            }
        });
    }

    toggleChat() {
        this.isVisible = !this.isVisible;
        const chatbotWindow = document.getElementById('chatbot-window');
        chatbotWindow.classList.toggle('active');
        
        if (this.isVisible) {
            document.getElementById('chatbot-input').focus();
        }
    }

    hideChat() {
        this.isVisible = false;
        document.getElementById('chatbot-window').classList.remove('active');
    }

    sendMessage() {
        const input = document.getElementById('chatbot-input');
        const message = input.value.trim();
        
        if (message && !this.isTyping) {
            this.addMessage(message, 'user');
            input.value = '';
            this.simulateTyping();
            setTimeout(() => this.handleBotResponse(message), 1000);
        }
    }

    handleQuickReply(reply) {
        this.addMessage(reply, 'user');
        this.simulateTyping();
        setTimeout(() => this.handleBotResponse(reply), 1000);
    }

    addMessage(text, sender) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const time = new Date().toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-${sender === 'user' ? 'user' : 'robot'}"></i>
            </div>
            <div class="message-content">
                <p>${text}</p>
                <span class="message-time">${time}</span>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Сохраняем в историю
        this.conversationHistory.push({ sender, text, time });
        this.saveToLocalStorage();
    }

    simulateTyping() {
        if (this.isTyping) return;
        
        this.isTyping = true;
        const messagesContainer = document.getElementById('chatbot-messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message';
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;

        messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }

    handleBotResponse(userMessage) {
        this.isTyping = false;
        
        // Удаляем индикатор печати
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.parentElement.parentElement.remove();
        }

        const response = this.generateBotResponse(userMessage.toLowerCase());
        this.addMessage(response.text, 'bot');

        // Если есть быстрые ответы, добавляем их
        if (response.quickReplies) {
            setTimeout(() => this.addQuickReplies(response.quickReplies), 300);
        }

        // Если нужно отправить в Telegram (для сложных вопросов)
        if (response.forwardToTelegram) {
            this.sendToTelegram(userMessage);
        }
    }

    generateBotResponse(message) {
        const responses = {
            greetings: {
                patterns: ['привет', 'здравствуйте', 'добрый день', 'hello', 'hi', 'начать', 'start'],
                response: `Рад вас видеть! Я SCM Assistant - ваш помощник по вопросам управления цепями поставок и цифровой трансформации. 

Чем конкретно могу помочь?`,
                quickReplies: ['SCM экспертиза', 'Опыт работы', 'Связаться с Дмитрием']
            },
            contact: {
                patterns: ['связаться', 'контакты', 'телефон', 'email', 'связь', 'свяжитесь'],
                response: `Конечно! Вот контакты Дмитрия:

📞 Телефон: +7 (928) 581-07-87
📧 Email: dmitriy.panibratskiy@yandex.ru
📍 Локация: Сургут / Санкт-Петербург

Также вы можете заполнить форму обратной связи на сайте, и Дмитрий свяжется с вами в ближайшее время.`,
                quickReplies: ['Заполнить форму', 'SCM экспертиза', 'Проекты']
            },
            expertise: {
                patterns: ['экспертиза', 'scm', 'поставки', 'логистика', 'цепь поставок', 'оптимизация'],
                response: `Дмитрий специализируется на:
                
• Управлении цепями поставок (SCM)
• Цифровой трансформации бизнеса  
• Внедрении AI и аналитики
• Оптимизации бизнес-процессов
• Управлении проектами

Более 10 лет опыта в крупных международных компаниях.`,
                quickReplies: ['Опыт работы', 'Технологии', 'Проекты']
            },
            experience: {
                patterns: ['опыт', 'резюме', 'background', 'работал', 'квалификация'],
                response: `Профессиональный опыт Дмитрия:

🎯 10+ лет в управлении цепями поставок
🏢 Опыт в FMCG, ритейле, логистике
🌍 Международные проекты
📈 Успешная реализация +15 крупных проектов
🎓 Профильное образование и сертификаты

Подробнее в разделе "Опыт" на сайте.`,
                quickReplies: ['Проекты', 'SCM экспертиза', 'Контакты']
            },
            projects: {
                patterns: ['проекты', 'реализовал', 'кейсы', 'примеры'],
                response: `Ключевые реализованные проекты:

• Внедрение WMS системы - экономия 15% на складе
• Оптимизация транспортных маршрутов -20% затрат
• Цифровизация цепочки поставок +30% эффективности
• Внедрение AI для прогнозирования спроса

Каждый проект принес значимый бизнес-результат.`,
                quickReplies: ['Технологии', 'SCM экспертиза', 'Связаться']
            },
            technologies: {
                patterns: ['технологии', 'инструменты', 'программы', 'software', 'ai'],
                response: `Используемые технологии и инструменты:

🤖 AI/ML: прогнозирование спроса, оптимизация
📊 Аналитика: Power BI, Tableau, Python
🔄 SCM системы: SAP, Oracle, 1C
🚚 WMS/TMS: собственные и коммерческие решения
☁️ Cloud: Azure, AWS, Google Cloud

Постоянное изучение новых технологий.`,
                quickReplies: ['Проекты', 'SCM экспертиза', 'Контакты']
            },
            default: {
                response: `Интересный вопрос! Дмитрий имеет обширный опыт в этой области, но для точного ответа лучше обсудить детали персонально.

Могу предложить:
• Связаться с Дмитрием для консультации
• Изучить раздел "Опыт" на сайте
• Посмотреть реализованные проекты

Какой вариант вам подходит?`,
                quickReplies: ['Связаться с Дмитрием', 'SCM экспертиза', 'Опыт работы'],
                forwardToTelegram: true
            }
        };

        // Поиск подходящего ответа
        for (const [key, config] of Object.entries(responses)) {
            if (key === 'default') continue;
            
            if (config.patterns.some(pattern => message.includes(pattern))) {
                return config;
            }
        }

        return responses.default;
    }

    addQuickReplies(replies) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="quick-replies">
                    ${replies.map(reply => 
                        `<button class="quick-reply" data-reply="${reply}">${reply}</button>`
                    ).join('')}
                </div>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    sendToTelegram(question) {
        const TELEGRAM_TOKEN = '8414212107:AAF2UAhSin1_m8HuASJ-aqhrwsGPs0WyxGA';
        const CHAT_ID = '2032477871';
        
        const text = `❓ Сложный вопрос из чат-бота:\n\n${question}\n\n💬 История чата:\n${this.conversationHistory.slice(-5).map(msg => `${msg.sender === 'user' ? '👤' : '🤖'} ${msg.text}`).join('\n')}`;

        fetch(`https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: CHAT_ID,
                text: text
            })
        }).catch(err => console.error('Ошибка отправки в Telegram:', err));
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('chatbot-messages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    saveToLocalStorage() {
        try {
            localStorage.setItem('scm-chatbot-history', JSON.stringify(this.conversationHistory));
        } catch (e) {
            console.warn('Не удалось сохранить историю чата:', e);
        }
    }

    loadFromLocalStorage() {
        try {
            const saved = localStorage.getItem('scm-chatbot-history');
            if (saved) {
                this.conversationHistory = JSON.parse(saved);
                // Ограничиваем историю последними 50 сообщениями
                if (this.conversationHistory.length > 50) {
                    this.conversationHistory = this.conversationHistory.slice(-50);
                }
                
                // Восстанавливаем историю в чате
                this.restoreChatHistory();
            }
        } catch (e) {
            console.warn('Не удалось загрузить историю чата:', e);
            this.conversationHistory = [];
        }
    }

    restoreChatHistory() {
        const messagesContainer = document.getElementById('chatbot-messages');
        messagesContainer.innerHTML = '';
        
        this.conversationHistory.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${msg.sender}-message`;
            
            messageDiv.innerHTML = `
                <div class="message-avatar">
                    <i class="fas fa-${msg.sender === 'user' ? 'user' : 'robot'}"></i>
                </div>
                <div class="message-content">
                    <p>${msg.text}</p>
                    <span class="message-time">${msg.time}</span>
                </div>
            `;

            messagesContainer.appendChild(messageDiv);
        });
        
        this.scrollToBottom();
    }
}

// Инициализация чат-бота при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    window.scmChatBot = new SCMChatBot();
});
