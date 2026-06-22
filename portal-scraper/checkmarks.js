const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const axios = require('axios');

// CONFIGURATION
const CAS_URL = process.env.CAS_URL;
const USERNAME = process.env.CAS_USERNAME;
const PASSWORD = process.env.CAS_PASSWORD;
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

const CACHE_FILE = path.join(__dirname, 'marks_cache.json');
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Helper function to send Telegram notifications
async function sendTelegramAlert(message) {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
  
  const payload = {
    chat_id: TELEGRAM_CHAT_ID,
    text: message,
    parse_mode: "Markdown" 
  };

  try {
    await axios.post(url, payload);
    console.log("Telegram notification dispatched successfully!");
  } catch (error) {
    console.error("❌ Failed to deliver Telegram alert:", error.response?.data || error.message);
  }
}

(async () => {
  const browser = await puppeteer.launch({
      args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.browserContexts()[0].newPage();
  
  try {
    console.log("Navigating to CAS login page...");
    await page.goto(CAS_URL, { waitUntil: 'networkidle2' });

    console.log("Entering credentials...");
    await page.waitForSelector('#username'); 
    await page.waitForSelector('#password');
    await page.type('#username', USERNAME);
    await page.type('#password', PASSWORD);

    console.log("Submitting login form...");
    await Promise.all([
      page.click('button[type="submit"]'), 
      page.waitForNavigation({ waitUntil: 'networkidle0' })
    ]);

    console.log('Accessing portal menu...');
    await page.waitForSelector('a[href="notes"]');
    await page.click('a[href="notes"]');

    await page.waitForFunction(() => {
      return Array.from(document.querySelectorAll('a')).some(el => el.textContent.includes('2ème année Informatique'));
    });
    await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('a'));
      const targetLink = links.find(el => el.textContent.trim().includes('2ème année Informatique'));
      if (targetLink) targetLink.click();
    });

    await page.waitForSelector('tr.dwebmodule');

    const targetModules = [
      "Programmation Objet avec C++",
      "Bases de données relationnelles",
      "Système d'exploitation 2",
      "Programmation Web 2",
      "Structures de données",
      "Analyse Numérique",
      "Français"
    ];

    const currentResults = await page.evaluate((modulesToFind) => {
      const cleanText = (str) => str.replace(/\s+/g, ' ').trim();
      const rows = Array.from(document.querySelectorAll('tr.dwebmodule'));
      let trackingList = {};

      rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 5) {
          const rawTitle = cells[2].textContent;
          const normalizedTitle = cleanText(rawTitle);
          const session1Mark = cleanText(cells[3].textContent);
          const resultStatus = cleanText(cells[4].textContent);

          const matchedModule = modulesToFind.find(m => cleanText(m) === normalizedTitle);
          if (matchedModule) {
            trackingList[matchedModule] = {
              posted: session1Mark !== "", 
              mark: session1Mark || null,
              status: resultStatus || null
            };
          }
        }
      });
      return trackingList;
    }, targetModules);

    let cachedResults = {};
    if (fs.existsSync(CACHE_FILE)) {
      cachedResults = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
    }

    let alertsToSend = [];
    targetModules.forEach(modName => {
      const currentData = currentResults[modName];
      const cachedData = cachedResults[modName];

      if (currentData && currentData.posted) {
        const wasPreviouslyPosted = cachedData && cachedData.posted;
        if (!wasPreviouslyPosted) {
          alertsToSend.push(`🔔 *NEW MARK POSTED!*\n *Module:* ${modName}\n`);
        }
      }
    });

    if (alertsToSend.length > 0) {
      console.log(`Found ${alertsToSend.length} new update(s)!`);
      for (const alertMsg of alertsToSend) {
        await sendTelegramAlert(alertMsg);
        await delay(2000); 
      }
    } else {
      console.log("No new grades posted.");
    }

    fs.writeFileSync(CACHE_FILE, JSON.stringify(currentResults, null, 2), 'utf8');

  } catch (error) {
    console.error("An error occurred:", error);
  } finally {
    await browser.close();
  }
})();
