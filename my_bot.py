from playwright.async_api import async_playwright
import asyncio
from slugify import slugify
import re
import json
import os
import time
import csv
start_time = time.time()

def check_cookies_for_ga(cookie_array):
    regex_pattern = r'ga|gid'
    has_ga_cookie = False

    for cookie in cookie_array:
        if re.search(regex_pattern, cookie['name'], re.IGNORECASE):
            has_ga_cookie = True
            break

    return has_ga_cookie
async def search_for_code(source_code):
    patterns = {
        'phone': r'<a[^>]*?href="(?:tel|phone):([^"]+)">',
        'email': r'<a[^>]*?href="mailto:([^"]+)">',
        'gtag': r'(?i)<script[^>]*>[\s\S]*?gtag\(.*[\'"]G-[0-9]++[\'"].*\)[\s\S]*?</script>',
        'gtm': r'GTM-',
        'ua': r'UA-\d+-\d+',
        'wordpress': r'wp-content',
        'facebook': r'(facebook\.com/[^/\s]+)',
        'meta-pixel': r'(fbq|fbevents.js|pixelIds|)',
        'pixel': r'(pixel)',
        'instagram': r'(instagram\.com/[^/\s]+)',
        'linkedin': r'(linkedin\.com/in/[^/\s]+)',
        'edrone': r'edrone',
        'getresponse': r'getresponse',
        'salesmanago': r'salesmanago',
        'shop': r'class="[^"]*price[^"]*"|id="[^"]*price[^"]*"',
        'woocommerce': r'woocommerce',
        'idosell': r'idosell',
        'shopify': r'shopify.com',
        'magento': r'magento|Magento',
        'shoper': r'shoper|Shoper'
    }
    results = {
        'phone': None,
        'email': None,
        'gtag': False,
        'gtm': False,
        'ua': False,
        'wordpress': False,
        'facebook': None,
        'meta-pixel': False,
        'pixel': False,
        'instagram': None,
        'linkedin': None,
        'edrone': False,
        'getresponse': False,
        'salesmanago': False,
        'shop': False,
        'woocommerce': False,
        'idosell': False,
        'shopify': False,
        'magento': False,
        'shoper': False
    }
    for key,val in patterns.items():
        match = re.search(val, source_code)
        
        if match:
            if key == 'phone' or key == 'email' or key == 'facebook' or key == 'instagram' or key == 'linkedin':
                results[key] = match.group(1)
            else:
                results[key] = True
        else:
            if key == 'shop':
                break
    
        
    return results

            

async def to_csv(url_obj):
    with open("all.csv", mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if file.tell() == 0:
            header_row = ['adres']+ list(url_obj['codes'].keys())
            writer.writerow(header_row)
        data_row = [url_obj['name']]+ list(url_obj['codes'].values())
        writer.writerow(data_row)

async def simulate_user_behaviour(page):
    await page.evaluate('window.scrollBy(0, 500)')
    await page.wait_for_timeout(2000)
    
    await page.evaluate('window.scrollTo(0, 0)')

async def open_url(url, url_list):
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)
            await simulate_user_behaviour(page)
            print(url+' is processing...')
            await asyncio.sleep(2)


            page.on("request", lambda req: url_list.append(req.url))

            domain = list(
                set(
                    map(
                        lambda r:
                            re.search("https?://(?:www.)?([^\/]+\.[^\/]+)",r).group(1), url_list
                        )
                    )
            )
            source_code = await page.content()
            cookies = await page.context.cookies()

            injected_code = await search_for_code(source_code)

            url_obj = {
                'id': 1,
                'name': url,
                'third_part_domain': domain,
                'cookies': cookies,
                'codes': injected_code
            }
            has_wrong_cookies = False

            has_wrong_cookies = check_cookies_for_ga(cookies)
            if has_wrong_cookies ==True:
                if url_obj['codes']['gtm'] == True and url_obj['codes']['wordpress'] == True and has_wrong_cookies == True:
                    with open("easy.csv", mode="a", newline="", encoding="utf-8") as file:
                        writer = csv.writer(file)

                        if file.tell() == 0:
                            header_row = ['adres']+ list(url_obj['codes'].keys())
                            writer.writerow(header_row)
                        data_row = [url]+ list(url_obj['codes'].values())
                        writer.writerow(data_row)
            await to_csv(url_obj)
            regex = r"https?://(?:www\.)?([^\/]+)\.[^\/]+"
            match = re.search(regex, url)
            
            if match:
                folder = match.group(1)
            if not os.path.exists('urls/'+folder):
                os.makedirs('urls/'+folder)

            filename ='desktop.png'
            screenshot_path =os.path.join('urls',folder,filename)

            json_filename = slugify(url)+ '.json'
            json_path=os.path.join('urls',folder,json_filename)
            await page.screenshot(path=screenshot_path)


            await browser.close()

            # mobile view
            iphone13 = playwright.devices['iPhone 13']
            mobile_browser = await playwright.chromium.launch()
            mobile_context = await mobile_browser.new_context(**iphone13,)
            mobile_page = await mobile_context.new_page()
        
            await mobile_page.goto(url)
            await simulate_user_behaviour(mobile_page)
            print(url+' mobile is processing...')
            await asyncio.sleep(2)

            mobile_filename = 'mobile.png'
            mobile_screenshot_path =os.path.join('urls',folder,mobile_filename)
            await mobile_page.screenshot(path=mobile_screenshot_path)
            print(url+' mobile is done!')
            await mobile_browser.close()

            # write to json
            with open(json_path, 'w') as json_file:
                json.dump(url_obj, json_file)
            print(url+' is done!')
            return url
    except Exception as e:
        print('Błąd! '+url)
        with open('pominiete2.txt', 'a') as file:
            file.write(url + '\n')

async def main():
    urls = []
    with open('adresy.txt', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    max_concurrent_windows = 8
    url_list = []  
    open_windows=[]

    for url in urls:
        while len(open_windows) >= max_concurrent_windows:
            open_windows = [window for window in open_windows if not window.done()]

            await asyncio.sleep(0.1)
        window = asyncio.create_task(open_url(url,url_list))
        open_windows.append(window)

    await asyncio.gather(*open_windows)

asyncio.run(main())
print("it took: "+str((time.time()-start_time)/60))
