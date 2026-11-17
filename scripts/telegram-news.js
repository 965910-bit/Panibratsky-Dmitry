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
    if (fs.existsSync(SENT_FILE)) {
        try {
            const sent = JSON.parse(fs.readFileSync(SENT_FILE, 'utf8'));
            if (!Array.isArray(sent) || !sent.every(link => typeof link === 'string')) throw new Error('invalid state');
            return sent;
        } catch (e) {
            throw new Error('Не удалось прочитать состояние отправок; остановка для предотвращения дубликатов');
        }
    }
    return [];
}

function saveSentNews(sentLinks) {
    try {
        ensureDataDir();
        fs.writeFileSync(SENT_FILE, JSON.stringify(sentLinks, null, 2), 'utf8');
    } catch (e) {
        throw new Error('Не удалось сохранить список отправленных новостей: ' + e.message);
    }
}

function loadNews() {
    if (!fs.existsSync(NEWS_FILE)) {
        throw new Error('Файл news.json не найден');
    }
    try {
        const data = fs.readFileSync(NEWS_FILE, 'utf8');
        const news = JSON.parse(data);
        if (!Array.isArray(news)) throw new Error('ожидался список новостей');
        return news;
    } catch (e) {
        throw new Error('Ошибка чтения news.json: ' + e.message);
    }
}

function addUTM(value, campaign, medium) {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Недопустимый адрес новости');
    url.searchParams.set('utm_source', 'telegram');
    url.searchParams.set('utm_medium', medium);
    url.searchParams.set('utm_campaign', campaign);
    return url.href;
}

// Heuristic, not a classifier: accept explicit operational vocabulary in the
// actual headline/description, not alert labels, tags or source category prefixes.
function isRelevant(item) {
    const title = typeof item.title === 'string' ? item.title.trim() : '';
    let description = typeof item.description === 'string' ? item.description.trim() : '';
    const isAlert = /^оповещение google\s*[–—-]/iu.test(title);
    if (/^google alert по теме:/iu.test(description)) description = '';
    if (/^АТИ/iu.test(String(item.source || ''))) description = description.replace(/^[^:]{1,80}:\s*/u, '');
    const content = `${isAlert ? '' : title} ${description}`;
    return /(?:склад|логистик|грузоперевоз|грузов(?:ые|ых|ого|ым) перевоз|перевозк[аиу] груз|постав(?:ка|ки|ок|кам|ках|щик)|цеп(?:ь|и|ей) постав|управлени[ея] запас|товарн(?:ые|ых|ого) запас|снабжени|транспортн(?:ая|ой|ые|ых|ую) логистик|инвентаризаци|распределительн(?:ый|ого|ом) центр|фулфилмент|\bwms\b|\btms\b|supply chain|warehouse|freight)/iu.test(content);
}

function formatPost(item) {
    const rawTitle = typeof item.title === 'string' ? item.title.trim() : '';
    // Google Alerts subjects identify a search, not the article headline.
    const title = rawTitle.replace(/^оповещение google\s*[–—-]\s*/iu, 'Google Alerts · тема: ').slice(0, 300);
    const description = (typeof item.description === 'string' ? item.description : '').slice(0, 200);
    const link = item.link || '';
    const source = (typeof item.source === 'string' ? item.source : '').slice(0, 100);
    const campaign = `news_${Date.now()}_${source}`;
    const site = new URL('https://scm-news.ru/trends.html');
    // The fragment stays on the browser and is matched against the current feed.
    // Telegram limits button URLs; fall back to the feed for unusually long links.
    site.hash = new URLSearchParams({ news: link }).toString();
    const feedUrl = 'https://scm-news.ru/trends.html';
    const siteUrl = site.href.length <= 1400 ? site.href : feedUrl;
    let shareUrl = `https://t.me/share/url?url=${encodeURIComponent(addUTM(siteUrl, campaign, "share"))}&text=${encodeURIComponent(title)}`;
    // Double-encoding a fragment can exceed Telegram's inline button URL limit.
    if (shareUrl.length > 2048) shareUrl = `https://t.me/share/url?url=${encodeURIComponent(addUTM(feedUrl, campaign, "share"))}`;

    const text = `📰 ${title}\n\n${description}\n\n🏷️ ${source}`;
    const keyboard = {
        inline_keyboard: [
            [
                { text: site.hash && siteUrl === site.href ? "🔗 Найти в ленте" : "🔗 Все новости", url: addUTM(siteUrl, campaign, "read_more") },
                { text: "📄 Подробнее", url: addUTM(link, campaign, "source") }
            ],
            [
                { text: "🔁 Поделиться", url: shareUrl }
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
            reply_markup: JSON.stringify(formatted.reply_markup),
            disable_web_page_preview: false
        });
        console.log(`Отправлено: ${formatted.title}`);
        return true;
    } catch (err) {
        console.error(`Ошибка отправки: ${formatted.title}; статус: ${err.response?.status || 'сетевой сбой'}`);
        return false;
    }
}

async function main() {
    const args = process.argv.slice(2);
    if (args.length > 1 || args.some(arg => !['--preview', '--initialize-journal'].includes(arg))) {
        throw new Error('Неизвестный аргумент. Используйте --preview или --initialize-journal.');
    }
    const preview = args.includes('--preview');
    const initialize = args.includes('--initialize-journal');
    if (!preview && !initialize && (!TELEGRAM_TOKEN || !TELEGRAM_CHAT_ID)) {
        console.error('Отсутствуют TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID');
        process.exit(1);
    }

    console.log('Загрузка новостей из news.json...');
    const allNews = loadNews();
    if (initialize) {
        if (fs.existsSync(SENT_FILE)) throw new Error('Журнал уже существует. Инициализация отменена без изменений.');
        const links = [...new Set(allNews.filter(item => {
            if (!item || typeof item.link !== 'string') return false;
            try { const url = new URL(item.link); return ['http:', 'https:'].includes(url.protocol) && !!url.hostname; }
            catch (_) { return false; }
        }).map(item => item.link))];
        if (!links.length) throw new Error('В ленте нет ссылок: безопасно инициализировать журнал нельзя.');
        ensureDataDir();
        // Exclusive create prevents overwriting a journal that appeared concurrently.
        fs.writeFileSync(SENT_FILE, JSON.stringify(links, null, 2), { encoding: 'utf8', flag: 'wx' });
        console.log(`Инициализирован журнал: ${links.length} ссылок текущей ленты исключены из отправки. Сообщения не отправлены.`);
        return;
    }
    if (!preview && !fs.existsSync(SENT_FILE)) {
        throw new Error('Журнал отправок отсутствует: рассылка остановлена, чтобы избежать повторов. Восстановите журнал или осознанно инициализируйте его по инструкции.');
    }
    if (allNews.length === 0) {
        console.log('Нет новостей для отправки.');
        return;
    }

    // Сортируем по дате (новые сверху)
    const dateValue = item => {
        const value = item && typeof item.pubDate === 'string' ? Date.parse(item.pubDate) : NaN;
        return Number.isFinite(value) ? value : -Infinity;
    };
    allNews.sort((a, b) => dateValue(b) - dateValue(a));

    const stateExists = fs.existsSync(SENT_FILE);
    let sentLinks = loadSentNews();
    if (preview && !stateExists) {
        console.log('Журнал отправок не найден: предпросмотр не может исключить уже опубликованные материалы.');
    }
    const seen = new Set(sentLinks);
    let skippedIrrelevant = 0;
    const newNews = allNews.filter(item => {
        if (!item || item.dead || typeof item.link !== 'string' || seen.has(item.link)) return false;
        try {
            const url = new URL(item.link);
            if (!['http:', 'https:'].includes(url.protocol)) return false;
        } catch (_) { return false; }
        seen.add(item.link);
        if (!isRelevant(item)) { skippedIrrelevant++; return false; }
        return true;
    }).slice(0, MAX_NEWS_PER_RUN);

    console.log(`Пропущено по тематическому фильтру: ${skippedIrrelevant}. Это эвристика, не редакторская проверка.`);
    if (preview && newNews.length === 0) console.log('ПРЕДПРОСМОТР: сообщения не отправляются, журнал не изменяется.');
    if (newNews.length === 0) {
        console.log('Нет новых новостей, прошедших тематический фильтр.');
        return;
    }

    console.log(`Новых новостей: ${newNews.length}`);
    if (preview) {
        console.log('ПРЕДПРОСМОТР: сообщения не отправляются, журнал не изменяется.');
        for (const item of newNews) {
            const post = formatPost(item);
            // JSON escapes newlines and GitHub Actions command syntax in untrusted text.
            console.log('ПРЕДПРОСМОТР ' + JSON.stringify({ text: post.text, source_url: item.link, buttons: post.reply_markup.inline_keyboard }));
        }
        return;
    }
    let successCount = 0;
    for (const news of newNews) {
        const formatted = formatPost(news);
        const ok = await sendToTelegram(formatted);
        if (ok) {
            sentLinks.push(news.link);
            saveSentNews(sentLinks);
            successCount++;
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    saveSentNews(sentLinks);
    console.log(`Отправлено ${successCount} из ${newNews.length}`);
    if (successCount !== newNews.length) throw new Error('Не все новости доставлены; успешные отправки сохранены');
}

main().catch(err => {
    console.error('Критическая ошибка:', err);
    process.exit(1);
});
