const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const axios = require('axios');

// =========================================================================
// CONFIGURATION: Set your credentials, portal URLs, and GREEN-API details
// =========================================================================
const CAS_URL = 'https://auth.univh2c.ma/cas5/login?service=https%3A%2F%2Fentv26.univh2c.ma%2FdossierPedago%2Flogin'; 
const USERNAME = 'YASSINE.BOUMAHDI2-ETU';                     
const PASSWORD = 'VVVocabulaire@123';                             

// GREEN-API Settings
const GREEN_API_INSTANCE_ID = '7107655886'; // e.g., '1101abcdef'
const GREEN_API_TOKEN_INSTANCE = '4bd04dee71ca4052aa5e8dc05ec4b172ea595e58e7004d4b85'; 
const TARGET_PHONE_NUMBER = '212617699682'; // Phone number with country code (no spaces or '+' sign)

const CACHE_FILE = path.join(__dirname, 'marks_cache.json');

// Helper function to send WhatsApp text alerts via GREEN-API
async function sendWhatsAppAlert(message) {
  const url = `https://api.green-api.com/waInstance${GREEN_API_INSTANCE_ID}/sendMessage/${GREEN_API_TOKEN_INSTANCE}`;
  const payload = {
    chatId: `${TARGET_PHONE_NUMBER}@c.us`,
    message: message
  };

  try {
    await axios.post(url, payload);
    console.log(`WhatsApp notification dispatched successfully!`);
  } catch (error) {
    console.error(`❌ Failed to deliver WhatsApp alert via GREEN-API:`, error.message);
  }
}

(async () => {
  const browser = await puppeteer.launch({ headless: true }); // Set to true to run cleanly in background/crontab
  const page = await browser.browserContexts()[0].newPage();
  
  try {
    // --- STEP 1: AUTOMATE CAS LOGIN ---
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

    // --- STEP 2: NAVIGATE TO NOTES AND RESULTS ---
    console.log('Accessing portal menu...');
    await page.waitForSelector('a[href="notes"]');
    await page.click('a[href="notes"]');

    // --- STEP 3: CLICK "2ÈME ANNÉE INFORMATIQUE" ---
    await page.waitForFunction(() => {
      return Array.from(document.querySelectorAll('a')).some(el => el.textContent.includes('2ème année Informatique'));
    });
    await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('a'));
      const targetLink = links.find(el => el.textContent.trim().includes('2ème année Informatique'));
      if (targetLink) targetLink.click();
    });

    // --- STEP 4: PARSE AND CHECK GRADES TABLE ---
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

    // --- STEP 5: LOAD CACHE & COMPARE FOR NEW GRADES ---
    let cachedResults = {};
    if (fs.existsSync(CACHE_FILE)) {
      cachedResults = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
    }

    let alertsToSend = [];

    targetModules.forEach(modName => {
      const currentData = currentResults[modName];
      const cachedData = cachedResults[modName];

      if (currentData && currentData.posted) {
        // Condition: Mark is live now, but wasn't in our previous check
        const wasPreviouslyPosted = cachedData && cachedData.posted;
        if (!wasPreviouslyPosted) {
          alertsToSend.push(`🔔 *NEW MARK POSTED!*\n📚 *Module:* ${modName}\n💯 *Mark:* ${currentData.mark}\n📊 *Status:* ${currentData.status}`);
        }
      }
    });

    // --- STEP 6: DISPATCH NOTIFICATIONS AND SAVE STATE ---
    if (alertsToSend.length > 0) {
      console.log(`Found ${alertsToSend.length} new update(s)! Sending notification alerts...`);
      for (const alertMsg of alertsToSend) {
        await sendWhatsAppAlert(alertMsg);
      }
    } else {
      console.log("No new grades posted since last check.");
    }

    // Always update cache snapshot to match the current live portal state
    fs.writeFileSync(CACHE_FILE, JSON.stringify(currentResults, null, 2), 'utf8');

  } catch (error) {
    console.error("An error occurred during verification:", error);
  } finally {
    await browser.close();
  }
})();