const fs = require('fs');
const path = require('path');
const axios = require('axios');
const FeedParser = require('feedparser');
const { pipeline } = require('stream');
const { promisify } = require('util');
const streamPipeline = promisify(pipeline);

const RSS_SOURCES = [
    { name: 'Логистика 360', url: 'https://logistics360.ru/feed/' }
];

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
    const campaign = `news_${Date.now()}`;
    const siteUrl = 'https://965910-bit.github.io/Panibratsky-Dmitry/trends.html';

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
