import dotenv from 'dotenv';
import { chromium } from 'playwright';
import logger from './utils/logger.js';

// Load environment variables
dotenv.config();

const config = {
  headless: process.env.BROWSER_HEADLESS === 'true',
  timeout: parseInt(process.env.BROWSER_TIMEOUT) || 30000,
  port: process.env.PORT || 3000,
  interval: parseInt(process.env.AUTOMATION_INTERVAL) || 60000,
};

let browser = null;
let isRunning = true;

/**
 * Initialize browser instance
 */
async function initializeBrowser() {
  try {
    logger.info('Initializing Playwright browser...');
    browser = await chromium.launch({
      headless: config.headless,
      args: [
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
      ],
    });
    logger.info('Browser initialized successfully');
    return browser;
  } catch (error) {
    logger.error(`Failed to initialize browser: ${error.message}`);
    throw error;
  }
}

/**
 * Main automation logic
 */
async function runAutomation() {
  let page = null;
  try {
    if (!browser) {
      await initializeBrowser();
    }

    const context = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    });

    page = await context.newPage();
    page.setDefaultTimeout(config.timeout);
    page.setDefaultNavigationTimeout(config.timeout);

    logger.info('Starting automation task...');

    // TODO: Add your automation logic here
    // Example:
    // await page.goto('https://example.com');
    // await page.fill('input[name="username"]', process.env.TARGET_USERNAME);

    logger.info('Automation task completed successfully');

    await context.close();
  } catch (error) {
    logger.error(`Automation error: ${error.message}`);
  } finally {
    if (page) {
      await page.close().catch(() => {});
    }
  }
}

/**
 * Graceful shutdown
 */
async function shutdown() {
  logger.info('Shutting down gracefully...');
  isRunning = false;

  if (browser) {
    await browser.close().catch((error) => {
      logger.error(`Error closing browser: ${error.message}`);
    });
  }

  process.exit(0);
}

/**
 * Main loop
 */
async function main() {
  try {
    await initializeBrowser();

    // Run automation on interval
    while (isRunning) {
      await runAutomation();
      logger.info(`Next run scheduled in ${config.interval / 1000} seconds`);
      await new Promise((resolve) => setTimeout(resolve, config.interval));
    }
  } catch (error) {
    logger.error(`Fatal error: ${error.message}`);
    process.exit(1);
  }
}

// Handle signals
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

// Start application
logger.info('Web Automation Bot starting...');
main().catch((error) => {
  logger.error(`Startup error: ${error.message}`);
  process.exit(1);
});

export { browser, runAutomation };
