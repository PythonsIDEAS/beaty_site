import json
import asyncio
from pyppeteer import launch
from datetime import datetime

async def scrape_2gis_reviews(url):
    browser = None
    
    try:
        # Launch browser
        browser = await launch({
            'headless': True,
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080'
            ]
        })
        
        # Create new page
        page = await browser.newPage()
        
        # Set viewport
        await page.setViewport({'width': 1920, 'height': 1080})
        
        # Set user agent
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Navigate to URL
        print('Navigating to URL...')
        await page.goto(url, {'waitUntil': 'networkidle0', 'timeout': 60000})
        
        # Wait for reviews to load
        print('Waiting for reviews to load...')
        await page.waitForSelector('._1msln3t, [data-test-id="review_card"]', {'timeout': 45000})
        
        # Get total review count
        total_reviews = await page.evaluate('''
            () => {
                const countElement = document.querySelector('span._1xhlznaa');
                return countElement ? parseInt(countElement.textContent) : 0;
            }
        ''')
        print(f'Total reviews to load: {total_reviews}')
        
        # Scroll to load all reviews
        print('Loading all reviews...')
        last_height = await page.evaluate('document.documentElement.scrollHeight')
        scroll_attempts = 0
        max_scroll_attempts = 300  # Further increased limit for more reviews
        last_review_count = 0
        stall_count = 0
        
        while scroll_attempts < max_scroll_attempts:
            # Get current number of loaded reviews
            current_reviews = await page.evaluate('''
                () => document.querySelectorAll('._1msln3t, [data-test-id="review_card"]').length
            ''')
            print(f'Currently loaded reviews: {current_reviews}/{total_reviews}')
            
            if current_reviews >= total_reviews:
                print('All reviews loaded successfully')
                break
            
            # Check if we're making progress
            if current_reviews == last_review_count:
                stall_count += 1
                if stall_count >= 5:  # If stuck for 5 attempts, try clicking 'Show more'
                    try:
                        show_more = await page.querySelector("button._1w5tmsk")
                        if show_more:
                            await show_more.click()
                            await asyncio.sleep(2)  # Wait after clicking
                            stall_count = 0  # Reset stall count after clicking
                    except Exception as e:
                        print(f'Show more button error: {str(e)}')
                        pass
            else:
                stall_count = 0  # Reset stall count if we loaded new reviews
                
            last_review_count = current_reviews
            
            # Scroll in smaller increments
            for _ in range(3):  # Scroll 3 times with smaller steps
                await page.evaluate('window.scrollBy(0, 300)')
                await asyncio.sleep(1)  # Short pause between small scrolls
            
            await asyncio.sleep(2)  # Additional wait after scroll sequence
            
            # Get new scroll height
            new_height = await page.evaluate('document.documentElement.scrollHeight')
            
            # Break if we've reached the bottom and can't load more
            if new_height == last_height and stall_count >= 10:
                print('Reached bottom of page, no more reviews loading')
                break
                
            last_height = new_height
            scroll_attempts += 1
        
        # Get the full HTML content
        print('Getting page HTML...')
        html_content = await page.content()
        
        # Save HTML to file
        with open('2gis_reviews.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print('HTML content saved to 2gis_reviews.html')
        
        return True
    except Exception as e:
        print(f'Error during scraping: {str(e)}')
        return False
    
    finally:
        if browser:
            await browser.close()
            print('Browser closed')

if __name__ == '__main__':
    url = 'https://2gis.kz/astana/firm/70000001075828225/tab/reviews'
    print('Starting HTML scraping...')
    
    async def main():
        return await scrape_2gis_reviews(url)
    
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if 'Event loop is closed' in str(e):
            # Create a new event loop if the current one is closed
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(main())
            loop.close()
        else:
            raise