from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
import time
import json
import sys
import argparse

SITE_URL = "https://scholar.google.com"

class InfoExtractor:
    def __init__(self, soup_elem):
        self.soup_elem = soup_elem
        self.info = {}
        self.__extract_info()

    def __extract_name(self):
        name = self.soup_elem.find('div', id="gsc_prf_in")
        if name != None:
            self.info['name'] = name.get_text()
    
    def __extract_title(self):
        title = self.soup_elem.find('div', class_="gsc_prf_il")
        if title != None:
            self.info['title'] = title.get_text()

    def __extract_info(self):
        self.__extract_name()
        self.__extract_title()
        
    def is_valid(self):
        pass    

    def extract(self):
        return self.info

class PubExtractor:
    def __init__(self, soup_elem):
        self.soup_elem = soup_elem
        self.info = {}
        self.__extract_info()

    def __extract_title(self):
        title = self.soup_elem.find('a', class_="gsc_a_at")
        if title != None:
            self.info['title'] = title.get_text()
            link = f"{title['href']}"
            if link.startswith("/"):
                link = SITE_URL + link
            self.info['link'] = link
            self.info['id'] = link.split("=")[-1]
    
    def __extract_gray(self):
        grays = self.soup_elem.find_all('div', class_="gs_gray")
        if len(grays) > 0:
            self.info['authors'] = grays[0].get_text()
        if len(grays) > 1:
            self.info['venue'] = grays[1].get_text()
    
    def __extract_numc(self):
        numc = self.soup_elem.find('a', class_="gsc_a_ac")
        if numc != None:
            numc_str = numc.get_text()
            if numc_str == "":
                self.info['citation'] = 0
            else:
                self.info['citation'] = numc_str
                self.info['citation_link'] = f"{numc['href']}"

    def __extract_year(self):
        year = self.soup_elem.find('td', class_="gsc_a_y")
        if year != None:
            self.info['year'] = year.get_text()

    def __extract_info(self):
        self.__extract_title()
        self.__extract_year()
        self.__extract_numc()
        self.__extract_gray()
        
    def is_valid(self):
        id = self.info['id']
        return id is not None and id != ""

    def extract(self):
        return self.info

def can_button_click(elem):
    if elem == None:
        print("[WARNING] No button found")
        return False
    attr = elem.get_attribute('disabled')
    return attr == None

def scroll_for_all_pubs(browser):
    time.sleep(1)
    button = browser.find_element_by_id('gsc_bpf_more')
    while (can_button_click(button)):
        button.click()
        time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description='Crawler for Google Scholar Pages')
    parser.add_argument('scholar_id', help='the ID of the scholar assigned by Google Scholar')
    parser.add_argument('--info', '-i', action='store_true', help="Only get Metadata of Scholar")
    parser.add_argument('--output', '-o', help="Output File, default stdout", required=False)
    args = parser.parse_args()

    options = Options()
    options.headless = True
    browser = webdriver.Firefox(options=options)
    browser.get(f'https://scholar.google.com/citations?user={args.scholar_id}&sortby=pubdate')

    # Check if page exist
    if '404' in browser.title:
        print("[ERROR] 404")
        exit(-1)

    # Click "Show More Results", skip if just retrieve info
    if not args.info:
        scroll_for_all_pubs(browser)

    # Fetch Page
    html = browser.page_source
    soup = BeautifulSoup(html, 'html.parser')
    pubs = soup.find_all('tr', class_="gsc_a_tr")

    # Info
    if args.info:
        info = soup.find('div', id="gsc_prf")
        ie = InfoExtractor(info)
        if args.output == None:
            json.dump(ie.extract(), sys.stdout, sort_keys=True, ensure_ascii=False, indent=2)
        else:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(ie.extract(), f, sort_keys=True, ensure_ascii=False, indent=2)
    # Publications
    else:
        papers = []
        for pub in pubs:
            pe = PubExtractor(pub)
            if pe.is_valid():
                papers.append(pe.extract())
        print(f"[INFO] found {len(papers)} publications")
        if args.output == None:
            json.dump({'papers': papers}, sys.stdout, sort_keys=True, ensure_ascii=False, indent=2)
        else:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({'papers': papers}, f, sort_keys=True, ensure_ascii=False, indent=2)

    browser.close()

if __name__ == "__main__":
    main()
