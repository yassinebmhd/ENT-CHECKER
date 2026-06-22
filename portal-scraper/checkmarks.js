const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const axios = require('axios');

// CONFIGURATION
const CAS_URL = process.env.CAS_URL;
const USERNAME = process.env.CAS_USERNAME;
const PASSWORD = process.env.CAS_PASSWORD;

// WhatsApp (GREEN-API) Settings
const GREEN_API_INSTANCE_ID = process.env.GREEN_API_INSTANCE_ID;
const GREEN_API_TOKEN_INSTANCE = process.env.GREEN_API_TOKEN_INSTANCE;
const TARGET_PHONE_NUMBER = process.env.TARGET_PHONE_NUMBER;

// Telegram Settings
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

const CACHE_FILE = path.join(__dirname, 'marks_cache.json');
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function sendWhatsAppAlert(target, message) {
  const url = `https://api.green-api.com/waInstance${GREEN_API_INSTANCE_ID}/sendMessage/${GREEN_API_TOKEN_INSTANCE}`;
  const chatId = target.includes('@') ? target : `${target}@c.us`;
  try {
    await axios.post(url, { chatId, message });
    console.log(`WhatsApp sent to ${target}`);
  } catch (error) { console.error(`WhatsApp error: ${error.message}`); }
}

async function sendTelegramAlert(message) {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
  
  try {
    // We send the message as plain text to avoid Markdown parsing errors
    await axios.post(url, { 
      chat_id: TELEGRAM_CHAT_ID, 
      text: message 
    });
    
    console.log("Telegram notification sent successfully!");
  } catch (error) {
    // This logs the specific error returned by Telegram's API
    if (error.response) {
      console.error("Telegram error details:", JSON.stringify(error.response.data, null, 2));
    } else {
      console.error("Telegram error message:", error.message);
    }
  }
}

(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.browserContexts()[0].newPage();
  
  try {
    await page.goto(CAS_URL, { waitUntil: 'networkidle2' });
    await page.type('#username', USERNAME);
    await page.type('#password', PASSWORD);
    await Promise.all([page.click('button[type="submit"]'), page.waitForNavigation({ waitUntil: 'networkidle0' })]);
    
    await page.click('a[href="notes"]');
    await page.waitForFunction(() => Array.from(document.querySelectorAll('a')).some(el => el.textContent.includes('2ème année Informatique')));
    await page.evaluate(() => {
      const targetLink = Array.from(document.querySelectorAll('a')).find(el => el.textContent.trim().includes('2ème année Informatique'));
      if (targetLink) targetLink.click();
    });

    await page.waitForSelector('tr.dwebmodule');
    const targetModules = ["Programmation Objet avec C++", "Bases de données relationnelles", "Système d'exploitation 2", "Programmation Web 2", "Structures de données", "Analyse Numérique", "Français"];

    const currentResults = await page.evaluate((modulesToFind) => {
      const cleanText = (str) => str.replace(/\s+/g, ' ').trim();
      const rows = Array.from(document.querySelectorAll('tr.dwebmodule'));
      let list = {};
      rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 5) {
          const mod = modulesToFind.find(m => cleanText(m) === cleanText(cells[2].textContent));
          if (mod) list[mod] = { posted: cleanText(cells[3].textContent) !== "", mark: cleanText(cells[3].textContent) };
        }
      });
      return list;
    }, targetModules);

    let cachedResults = fs.existsSync(CACHE_FILE) ? JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8')) : {};
    
    for (const modName of targetModules) {
      if (currentResults[modName]?.posted && !cachedResults[modName]?.posted) {
        const data = currentResults[modName];

        // Short message for Telegram
        const telegramMsg = `🔔 *NEW MARK POSTED!*\n *Module:* ${modName}`;

        // Detailed message for WhatsApp
        const whatsappMsg = `🔔 *NEW MARK POSTED!*\n` +
                            `*Module:* ${modName}\n` +
                            `*Mark:* ${data.mark || 'N/A'}\n` +
                            `*Status:* ${data.status || 'N/A'}`;
        
        // Notify Telegram (Short)
        await sendTelegramAlert(telegramMsg);
        
        // Notify WhatsApp (Detailed)
        await sendWhatsAppAlert(TARGET_PHONE_NUMBER.trim(), whatsappMsg);
        
        await delay(2000);
      }
    }

    fs.writeFileSync(CACHE_FILE, JSON.stringify(currentResults, null, 2), 'utf8');
  } catch (e) { console.error(e); } finally { await browser.close(); }
})();
