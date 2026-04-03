const fs = require('fs');
const path = require('path');
const axios = require('axios');

const NEWS_FILE = path.join(__dirname, '..', 'data', 'news.json');
const SENT_FILE = path.join(__dirname, '..', 'data', 'sent_news.json');
const DATA_DIR = path.join(__dirname, '..', 'data');

const TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;
const TELEGRAM_API = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;

const MAX_NEWS_PER_RUN = 5;

function ensureDataDir() {
    if (!fs.existsSync(DATA_DIR)) {
        fs.mkdirSync(DATA_DIR, { recursive: true });
    }
}

function loadSentNews() {
    ensureDataDir();
    if (fs.existsSync(SENT_FILE)) {
        try {
            return JSON.parse(fs.readFileSync(SENT_FILE, 'utf8'));
        } catch (e) {
            return [];
        }
    }
    return [];
}

function saveSentNews(sentLinks) {
    try {
        fs.writeFileSync(SENT_FILE, JSON.stringify(sentLinks, null, 2), 'utf8');
    } catch (e) {
        console.error('Ошибка сохранения sent_news.json', e);
    }
}

function loadNews() {
    if (!fs.existsSync(NEWS_FILE)) {
        console.log('Файл news.json не найден');
        return [];
    }
    try {
        const data = fs.readFileSync(NEWS_FILE, 'utf8');
        return JSON.parse(data);
    } catch (e) {
        console.error('Ошибка чтения news.json:', e);
        return [];
    }
}

function addUTM(url, campaign, medium) {
    if (!url) return url;
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}utm_source=telegram&utm_medium=${medium}&utm_campaign=${campaign}`;
}

function formatPost(item) {
    const title = item.title || '';
    const description = (item.description || '').slice(0, 200);
    const link = item.link || '';
    const source = item.source || '';
    const campaign = `news_${Date.now()}_${encodeURIComponent(source)}`;
    const siteUrl = 'https://scm-news.ru/trends.html';

    const text = `📰 *${title}*\n\n${description}\n\n🏷️ *${source}*`;
    const keyboard = {
        inline_keyboard: [
            [
                { text: "🔗 Читать на сайте", url: addUTM(siteUrl, campaign, "read_more") },
                { text: "📄 Подробнее", url: addUTM(link, campaign, "source") }
            ],
            [
                { text: "🔁 Поделиться", url: `https://t.me/share/url?url=${encodeURIComponent(addUTM(siteUrl, campaign, "share"))}&text=${encodeURIComponent(title)}` }
            ]
        ]
    };
    return { text, reply_markup: keyboard, campaign, link, title };
}

async function sendToTelegram(formatted) {
    try {
        await axios.post(TELEGRAM_API, {
            chat_id: TELEGRAM_CHAT_ID,
            text: formatted.text,
            parse_mode: 'Markdown',
            reply_markup: JSON.stringify(formatted.reply_markup),
            disable_web_page_preview: false
        });
        console.log(`Отправлено: ${formatted.title}`);
        return true;
    } catch (err) {
        console.error(`Ошибка отправки: ${formatted.title}`, err.response?.data || err.message);
        return false;
    }
}

async function main() {
    if (!TELEGRAM_TOKEN || !TELEGRAM_CHAT_ID) {
        console.error('Отсутствуют TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID');
        process.exit(1);
    }

    console.log('Загрузка новостей из news.json...');
    const allNews = loadNews();
    if (allNews.length === 0) {
        console.log('Нет новостей для отправки.');
        return;
    }

    // Сортируем по дате (новые сверху)
    allNews.sort((a, b) => new Date(b.pubDate) - new Date(a.pubDate));

    let sentLinks = loadSentNews();
    const newNews = allNews.filter(item => !sentLinks.includes(item.link)).slice(0, MAX_NEWS_PER_RUN);

    if (newNews.length === 0) {
        console.log('Новых новостей нет.');
        return;
    }

    console.log(`Новых новостей: ${newNews.length}`);
    let successCount = 0;
    for (const news of newNews) {
        const formatted = formatPost(news);
        const ok = await sendToTelegram(formatted);
        if (ok) {
            sentLinks.push(news.link);
            successCount++;
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    saveSentNews(sentLinks);
    console.log(`Отправлено ${successCount} из ${newNews.length}`);
}

main().catch(err => {
    console.error('Критическая ошибка:', err);
    process.exit(1);
});
