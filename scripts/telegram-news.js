const fs = require('fs');
const path = require('path');
const axios = require('axios');
const FeedParser = require('feedparser');
const { pipeline } = require('stream');
const { promisify } = require('util');
const streamPipeline = promisify(pipeline);

// ========== НАСТРОЙКИ ==========
const RSS_SOURCES = [
    { name: 'Logirus', url: 'https://logirus.ru/rss' },
    { name: 'Логистика 360', url: 'https://logistics360.ru/feed/' },
    { name: 'Zakupki.gov.ru', url: 'https://zakupki.gov.ru/epz/main/public/rss' },
    { name: 'Retail & Logistics', url: 'https://retail-loyalty.org/rss/' },
    { name: 'Склад & Логистика', url: 'https://logistics.ru/rss' },
    { name: 'MarketInfo', url: 'https://marketinfo.pro/rss' }
];

const SENT_FILE = path.join(__dirname, '..', 'data', 'sent_news.json');
const DATA_DIR = path.join(__dirname, '..', 'data');

const TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;
const TELEGRAM_API = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;

const MAX_NEWS_PER_RUN = 5;

// ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
function ensureDataDir() {
    if (!fs.existsSync(DATA_DIR)) {
        fs.mkdirSync(DATA_DIR, { recursive: true });
    }
}

function loadSentNews() {
    ensureDataDir();
    if (fs.existsSync(SENT_FILE)) {
        try {
            const data = fs.readFileSync(SENT_FILE, 'utf8');
            const parsed = JSON.parse(data);
            // Гарантируем, что это массив строк (ссылок)
            if (Array.isArray(parsed)) {
                return parsed;
            }
        } catch (e) {
            console.error('Ошибка чтения sent_news.json, создаём новый', e);
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

async function fetchRSSItems(sourceUrl) {
    return new Promise((resolve, reject) => {
        const items = [];
        axios({
            method: 'get',
            url: sourceUrl,
            responseType: 'stream',
            timeout: 10000
        }).then(response => {
            const feedparser = new FeedParser({ addmeta: false });
            streamPipeline(response.data, feedparser).catch(reject);
            feedparser.on('readable', function() {
                let item;
                while (item = this.read()) {
                    items.push({
                        title: item.title,
                        link: item.link,
                        pubDate: item.pubDate,
                        description: (item.description || '').replace(/<[^>]*>/g, '').slice(0, 200)
                    });
                }
            });
            feedparser.on('end', () => resolve(items));
            feedparser.on('error', reject);
        }).catch(reject);
    });
}

async function sendToTelegram(news) {
    const text = `📰 *${news.title}*\n\n${news.description}\n\n🔗 [Читать далее](${news.link})`;
    try {
        await axios.post(TELEGRAM_API, {
            chat_id: TELEGRAM_CHAT_ID,
            text: text,
            parse_mode: 'Markdown',
            disable_web_page_preview: false
        });
        console.log(`Отправлено: ${news.title}`);
        return true;
    } catch (err) {
        console.error(`Ошибка отправки: ${news.title}`, err.response?.data || err.message);
        return false;
    }
}

// ========== ОСНОВНАЯ ФУНКЦИЯ ==========
async function main() {
    if (!TELEGRAM_TOKEN || !TELEGRAM_CHAT_ID) {
        console.error('Отсутствуют TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID в секретах GitHub');
        process.exit(1);
    }

    console.log('Сбор новостей для Telegram...');
    let allNews = [];
    for (const src of RSS_SOURCES) {
        try {
            const items = await fetchRSSItems(src.url);
            console.log(`Загружено ${items.length} из ${src.name}`);
            allNews.push(...items);
        } catch (err) {
            console.error(`Ошибка ${src.name}:`, err.message);
        }
    }

    // Сортируем по дате (новые сверху)
    allNews.sort((a, b) => new Date(b.pubDate) - new Date(a.pubDate));

    // Загружаем историю отправленных ссылок
    let sentLinks = loadSentNews();

    // Фильтруем новости, которые ещё не отправлялись
    const newNews = allNews.filter(item => !sentLinks.includes(item.link)).slice(0, MAX_NEWS_PER_RUN);

    if (newNews.length === 0) {
        console.log('Новых новостей нет.');
        return;
    }

    console.log(`Найдено новых новостей: ${newNews.length}`);
    let successCount = 0;
    for (const news of newNews) {
        const ok = await sendToTelegram(news);
        if (ok) {
            sentLinks.push(news.link);
            successCount++;
        }
        await new Promise(resolve => setTimeout(resolve, 1000)); // пауза между отправками
    }

    // Сохраняем обновлённую историю
    saveSentNews(sentLinks);
    console.log(`Отправлено ${successCount} из ${newNews.length} новостей.`);
}

main().catch(err => {
    console.error('Критическая ошибка:', err);
    process.exit(1);
});
