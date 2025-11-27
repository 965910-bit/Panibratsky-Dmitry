// scm-chatbot.js
class SCMChatBot {
    constructor() {
        this.isVisible = false;
        this.init();
    }

    init() {
        this.createWidget();
        this.addStyles();
        this.bindEvents();
    }

    createWidget() {
        // Создаем контейнер чат-бота
        this.container = document.createElement('div');
        this.container.id = 'scm-chatbot';
        this.container.innerHTML = `
            <div class="chatbot-header">
                <h3>SCM Assistant</h3>
                <span class="status">Online</span>
                <button class="close-btn">×</button>
            </div>
            <div class="chatbot-body">
                <div class="messages" id="chatbot-messages">
                    <div class="bot-message">Добро пожаловать! Чем могу помочь?</div>
                </div>
                <div class="quick-options">
                    <button class="quick-option" data-option="projects">Проекты</button>
                    <button class="quick-option" data-option="technologies">Технологии</button>
                    <button class="quick-option" data-option="contacts">Контакты</button>
                </div>
                <div class="input-area">
                    <input type="text" id="chatbot-input" placeholder="Напишите ваше сообщение...">
                    <button id="chatbot-send">➤</button>
                </div>
            </div>
        `;
        
        // Создаем кнопку для открытия чата
        this.toggleBtn = document.createElement('button');
        this.toggleBtn.id = 'scm-chatbot-toggle';
        this.toggleBtn.innerHTML = '💬';
        this.toggleBtn.title = 'SCM Assistant';

        document.body.appendChild(this.toggleBtn);
        document.body.appendChild(this.container);
    }

    addStyles() {
        const styles = `
            #scm-chatbot {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 350px;
                height: 500px;
                background: white;
                border: 1px solid #ddd;
                border-radius: 10px;
                box-shadow: 0 5px 25px rgba(0,0,0,0.1);
                display: none;
                flex-direction: column;
                z-index: 10000;
                font-family: Arial, sans-serif;
            }

            #scm-chatbot.active {
                display: flex;
            }

            #scm-chatbot-toggle {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: #007bff;
                color: white;
                border: none;
                font-size: 24px;
                cursor: pointer;
                box-shadow: 0 3px 15px rgba(0,123,255,0.3);
                z-index: 10001;
                transition: transform 0.3s;
            }

            #scm-chatbot-toggle:hover {
                transform: scale(1.1);
            }

            .chatbot-header {
                background: #007bff;
                color: white;
                padding: 15px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .chatbot-header h3 {
                margin: 0;
                font-size: 16px;
            }

            .status {
                font-size: 12px;
                opacity: 0.8;
            }

            .close-btn {
                background: none;
                border: none;
                color: white;
                font-size: 20px;
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
            }

            .chatbot-body {
                flex: 1;
                display: flex;
                flex-direction: column;
                padding: 15px;
            }

            .messages {
                flex: 1;
                overflow-y: auto;
                margin-bottom: 15px;
                border: 1px solid #eee;
                border-radius: 5px;
                padding: 10px;
                background: #f9f9f9;
            }

            .bot-message {
                background: #e3f2fd;
                padding: 8px 12px;
                border-radius: 15px;
                margin: 5px 0;
                max-width: 80%;
            }

            .quick-options {
                display: flex;
                flex-direction: column;
                gap: 8px;
                margin-bottom: 15px;
            }

            .quick-option {
                padding: 10px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                cursor: pointer;
                text-align: left;
                transition: background 0.3s;
            }

            .quick-option:hover {
                background: #e9ecef;
            }

            .input-area {
                display: flex;
                gap: 8px;
            }

            #chatbot-input {
                flex: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }

            #chatbot-send {
                padding: 10px 15px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
        `;

        const styleSheet = document.createElement('style');
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
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
        this.container.querySelector('#chatbot-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }

    toggle() {
        this.isVisible = !this.isVisible;
        this.container.classList.toggle('active', this.isVisible);
    }

    hide() {
        this.isVisible = false;
        this.container.classList.remove('active');
    }

    handleQuickOption(option) {
        const responses = {
            projects: 'Наши последние проекты:\n• Система управления цепочками поставок\n• Платформа аналитики в реальном времени\n• Мобильное приложение для логистов',
            technologies: 'Используемые технологии:\n• AI/ML для прогнозирования\n• Blockchain для отслеживания\n• Cloud computing\n• IoT датчики',
            contacts: 'Контакты для связи:\n📞 +7 (999) 123-45-67\n📧 info@scm-company.ru\n🏠 Москва, ул. Логистическая, 15'
        };

        this.addMessage(option, 'user');
        setTimeout(() => {
            this.addMessage(responses[option], 'bot');
        }, 500);
    }

    sendMessage() {
        const input = this.container.querySelector('#chatbot-input');
        const message = input.value.trim();
        
        if (message) {
            this.addMessage(message, 'user');
            input.value = '';
            
            // Имитация ответа бота
            setTimeout(() => {
                const response = this.generateResponse(message);
                this.addMessage(response, 'bot');
            }, 1000);
        }
    }

    generateResponse(message) {
        const lowerMessage = message.toLowerCase();
        
        if (lowerMessage.includes('проект')) {
            return 'Мы разрабатываем инновационные решения для управления цепочками поставок. Хотите узнать о конкретном проекте?';
        } else if (lowerMessage.includes('технолог')) {
            return 'Используем передовые технологии: AI, блокчейн, IoT. Какая технология вас интересует?';
        } else if (lowerMessage.includes('контакт') || lowerMessage.includes('связаться')) {
            return 'Свяжитесь с нами по телефону +7 (999) 123-45-67 или email info@scm-company.ru';
        } else if (lowerMessage.includes('привет') || lowerMessage.includes('здравств')) {
            return 'Здравствуйте! Я SCM Assistant. Чем могу помочь?';
        } else {
            return 'Извините, я еще учусь. Можете спросить о проектах, технологиях или контактах.';
        }
    }

    addMessage(text, sender) {
        const messagesContainer = this.container.querySelector('#chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = sender === 'user' ? 'user-message' : 'bot-message';
        messageDiv.style.cssText = sender === 'user' ? 
            'background: #007bff; color: white; margin-left: auto;' : 
            'background: #e3f2fd;';
        messageDiv.textContent = text;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Инициализация чат-бота при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    window.scmChatBot = new SCMChatBot();
});
