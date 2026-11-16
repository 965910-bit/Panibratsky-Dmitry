// Chat Bot Functionality
class ChatBot {
    constructor() {
        this.isOpen = false;
        this.messages = [];
        this.initializeBot();
    }

    initializeBot() {
        this.createChatBotHTML();
        this.bindEvents();
        this.addWelcomeMessage();
    }

    createChatBotHTML() {
        const chatbotHTML = `
            <div class="chatbot-container">
                <button class="chatbot-button">
                    💬
                </button>
                <div class="chatbot-window">
                    <div class="chatbot-header">
                        <h3>Помощник Дмитрия</h3>
                        <button class="chatbot-close">×</button>
                    </div>
                    <div class="chatbot-messages"></div>
                    <div class="chatbot-input">
                        <input type="text" placeholder="Введите ваш вопрос..." maxlength="500">
                        <button class="chatbot-send">➤</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', chatbotHTML);
        
        this.elements = {
            button: document.querySelector('.chatbot-button'),
            window: document.querySelector('.chatbot-window'),
            close: document.querySelector('.chatbot-close'),
            messages: document.querySelector('.chatbot-messages'),
            input: document.querySelector('.chatbot-input input'),
            send: document.querySelector('.chatbot-send')
        };
    }

    bindEvents() {
        this.elements.button.addEventListener('click', () => this.toggleChat());
        this.elements.close.addEventListener('click', () => this.closeChat());
        this.elements.send.addEventListener('click', () => this.sendMessage());
        this.elements.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // Close chat when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.chatbot-container') && this.isOpen) {
                this.closeChat();
            }
        });
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        this.elements.button.classList.toggle('active', this.isOpen);
        this.elements.window.classList.toggle('active', this.isOpen);
        
        if (this.isOpen) {
            this.elements.input.focus();
            this.scrollToBottom();
        }
    }

    closeChat() {
        this.isOpen = false;
        this.elements.button.classList.remove('active');
        this.elements.window.classList.remove('active');
    }

    addWelcomeMessage() {
        const welcomeMessage = {
            type: 'bot',
            content: 'Привет! Я ваш помощник. Чем могу помочь?',
            time: new Date()
        };
        
        this.messages.push(welcomeMessage);
        this.displayMessage(welcomeMessage);
        this.showQuickQuestions();
    }

    showQuickQuestions() {
        const quickQuestions = [
            "Какие услуги вы предоставляете?",
            "Как с вами связаться?",
            "Расскажите о вашем опыте",
            "Какие технологии вы используете?"
        ];

        const questionsHTML = quickQuestions.map(question => 
            `<button class="quick-question" data-question="${question}">${question}</button>`
        ).join('');

        const quickQuestionsHTML = `
            <div class="quick-questions">
                ${questionsHTML}
            </div>
        `;

        this.elements.messages.insertAdjacentHTML('beforeend', quickQuestionsHTML);

        // Add event listeners to quick questions
        document.querySelectorAll('.quick-question').forEach(button => {
            button.addEventListener('click', (e) => {
                const question = e.target.getAttribute('data-question');
                this.elements.input.value = question;
                this.sendMessage();
            });
        });
    }

    sendMessage() {
        const messageText = this.elements.input.value.trim();
        
        if (!messageText) return;

        // Add user message
        const userMessage = {
            type: 'user',
            content: messageText,
            time: new Date()
        };

        this.messages.push(userMessage);
        this.displayMessage(userMessage);
        this.elements.input.value = '';
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Simulate bot response after delay
        setTimeout(() => {
            this.removeTypingIndicator();
            const botResponse = this.generateResponse(messageText);
            this.messages.push(botResponse);
            this.displayMessage(botResponse);
        }, 1000 + Math.random() * 1000);
    }

    showTypingIndicator() {
        const typingHTML = `
            <div class="message bot">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        this.elements.messages.insertAdjacentHTML('beforeend', typingHTML);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const typingIndicator = this.elements.messages.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.parentElement.remove();
        }
    }

    generateResponse(userMessage) {
        const responses = {
            'привет': 'Привет! Рад вас видеть. Чем могу помочь?',
            'здравствуйте': 'Здравствуйте! Как я могу помочь вам сегодня?',
            'услуги': 'Я предоставляю услуги веб-разработки, создание пользовательских интерфейсов, оптимизацию производительности и консультации по техническим вопросам.',
            'опыт': 'У меня более 5 лет опыта в веб-разработке. Работал над проектами различной сложности, от лендингов до корпоративных приложений.',
            'технологии': 'Основные технологии: HTML5, CSS3, JavaScript, React, Vue.js, Node.js, Python. Также работаю с системами контроля версий и инструментами сборки.',
            'контакты': 'Вы можете связаться со мной через форму на сайте, по электронной почте или в социальных сетях. Все контакты есть в разделе "Контакты".',
            'проекты': 'Посмотреть мои проекты можно в соответствующем разделе. Там представлены кейсы с описанием технологий и результатов.',
            'стоимость': 'Стоимость работы зависит от сложности проекта и сроков. Для точного расчета предлагаю обсудить детали проекта.',
            'время': 'Я работаю по будням с 9:00 до 18:00. Быстро отвечаю на сообщения в рабочее время.'
        };

        const lowerMessage = userMessage.toLowerCase();
        let response = 'Извините, я не совсем понял ваш вопрос. Можете переформулировать?';

        // Check for exact matches first
        for (const [key, value] of Object.entries(responses)) {
            if (lowerMessage.includes(key)) {
                response = value;
                break;
            }
        }

        // Check for similar phrases
        if (lowerMessage.includes('как связать') || lowerMessage.includes('контакт')) {
            response = responses['контакты'];
        } else if (lowerMessage.includes('сколько стоит') || lowerMessage.includes('цена') || lowerMessage.includes('стоимос')) {
            response = responses['стоимость'];
        } else if (lowerMessage.includes('работа') || lowerMessage.includes('опыт')) {
            response = responses['опыт'];
        } else if (lowerMessage.includes('технолог') || lowerMessage.includes('стек')) {
            response = responses['технологии'];
        }

        return {
            type: 'bot',
            content: response,
            time: new Date()
        };
    }

    displayMessage(message) {
        const timeString = message.time.toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        const wrapper = document.createElement('div');
        wrapper.className = `message ${message.type === 'user' ? 'user' : 'bot'}`;
        const content = document.createElement('div');
        content.className = 'message-content';
        content.appendChild(document.createTextNode(String(message.content)));
        const time = document.createElement('div');
        time.className = 'message-time';
        time.textContent = timeString;
        content.appendChild(time);
        wrapper.appendChild(content);
        this.elements.messages.appendChild(wrapper);
        this.scrollToBottom();
    }

    scrollToBottom() {
        this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new ChatBot();
});
