#!/usr/bin/env python

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
import time
import json
import sys
import argparse
import datetime
import uuid
import hashlib

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
    
    def __extract_avatar(self):
        container = self.soup_elem.find('div', id="gsc_prf_pua")
        img = container.find('img')
        if img != None:
            self.info['avatar'] = f"{img['src']}"
        
    def __extract_info(self):
        self.__extract_name()
        self.__extract_title()
        self.__extract_avatar()
        
    def is_valid(self):
        pass    

    def extract(self):
        return self.info

class DetailExtractor:
    def __init__(self, soup_elem):
        self.soup_elem = soup_elem
        self.info = {}
        self.__extract_info()

    def __extract_link(self):
        group = self.soup_elem.find('div', id="gsc_oci_title_gg")
        if group != None:
            link = group.find('a')
            if link != None:
                self.info['ext_text'] = link.get_text()
                self.info['ext_link'] = link['href']
    
    def __extract_authors(self):
        pairs = self.soup_elem.find_all('div', class_="gs_scl")
        for pair in pairs:
            key = pair.find('div', class_='gsc_oci_field').get_text()
            value = pair.find('div', class_='gsc_oci_value')
            if "Authors" in key:
                self.info['authors'] = value.get_text()
            if "date" in key:
                self.info['pub_date'] = value.get_text()
            if "articles" in key:
                link = value.find('a')
                if link != None:
                    href = link['href']
                    if href != None and '&cluster' in href:
                        parts = href.split('&')
                        for part in parts:
                            if 'cluster=' in part:
                                seg = part.split("=")
                                self.info['id'] = seg[1]
    
    def __extract_desc(self):
        desc = self.soup_elem.find('div', id="gsc_oci_descr")
        if desc != None:
            self.info['desc'] = desc.get_text()
        
    def __extract_info(self):
        self.__extract_link()
        self.__extract_authors()
        self.__extract_desc()
        
    def is_valid(self):
        id = self.info['id']
        return id is not None and id != ""

    def extract(self):
        return self.info


class PubExtractor:
    def __init__(self, soup_elem, browser):
        self.soup_elem = soup_elem
        self.browser = browser
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
            self.info['local_id'] = link.split("=")[-1]
    
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

    def __extract_detail(self):
        if self.info['local_id'] != None:
            url = f'https://scholar.google.com/citations?view_op=view_citation&citation_for_view={self.info["local_id"]}'
            self.browser.get(url)
            # Check if page exist
            if '404' in self.browser.title:
                self.info.clear()
                print("[non-fatal ERROR] 404")
            # Fetch Page
            html = self.browser.page_source
            soup = BeautifulSoup(html, 'html.parser')
            detl = soup.find('div', id="gsc_vcpb")
            if detl != None:
                ie = DetailExtractor(detl)
                if ie.is_valid():
                    self.info = {**self.info, **ie.extract()}
                else:
                    self.info.clear()
            else:
                uid = uuid.uuid1()
                print(f"[WARNING] URL '{url}' has no details")
                with open(f"warning_{uid}.html", "w") as text_file:
                    text_file.write(html)

    def __extract_info(self):
        self.__extract_title()
        self.__extract_year()
        self.__extract_numc()
        self.__extract_gray()
        # self.__extract_detail() Turned off for performance reasons
        
    def is_valid(self):
        id = self.info['local_id']
        title = self.info['title']
        year = self.info['year']
        return id is not None and id != "" \
               and title is not None and title != "" \
               and year is not None and year != ""

    def extract(self):
        self.info['hash_id'] = hashlib.sha256(f"{self.info['title']} - {self.info['year']}".encode('utf-8')).hexdigest()
        return self.info

def can_button_click(elem):
    if elem == None:
        print("[WARNING] No button found")
        return False
    attr = elem.get_attribute('disabled')
    return attr == None

def scroll_for_all_pubs(browser):
    button = browser.find_element_by_id('gsc_bpf_more')
    while (can_button_click(button)):
        button.click()
        time.sleep(0.5)

def output_dict(dict_, output_f=None):
    if output_f == None:
        json.dump(dict_, sys.stdout, sort_keys=True, ensure_ascii=False, indent=2)
    else:
        with open(output_f, 'w', encoding='utf-8') as f:
            json.dump(dict_, f, sort_keys=True, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Crawler for Google Scholar Pages')
    parser.add_argument('scholar_id', help='the ID of the scholar assigned by Google Scholar')
    parser.add_argument('--info', '-i', action='store_true', help="Only get Metadata of Scholar")
    parser.add_argument('--output', '-o', help="Output File, default stdout", required=False)
    args = parser.parse_args()

    curr_date = datetime.datetime.now()

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
    info = soup.find('div', id="gsc_prf")
    ie = InfoExtractor(info)
    metadata = ie.extract()
    metadata['time'] = f"{curr_date}"
    
    # Publications
    if args.info:
        output_dict(metadata, output_f=args.output)
    else:
        papers = []
        for idx, pub in enumerate(pubs):
            pe = PubExtractor(pub, browser)
            if pe.is_valid():
                papers.append(pe.extract())
        print(f"[INFO] found {len(papers)} publications")
        output_dict({'metadata': metadata, 'papers': papers}, output_f=args.output)

    browser.close()

if __name__ == "__main__":
    main()
