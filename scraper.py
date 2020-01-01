import scrapy
import os
import sys
from inline_requests import inline_requests
import requests
from fpdf import FPDF
import datetime
import shutil
from scrapy.crawler import CrawlerProcess
import cv2

# from PIL import import Images

# from scrapy.utils.project import get_project_settings
# # useful if you have settings.py 
# settings = get_project_settings('settings')
if len(sys.argv) > 1:
    from_date = datetime.datetime.strptime(str(sys.argv[1]), '%Y-%m-%d').date()
else:
    from_date = datetime.date.today()

class EpaperSpider(scrapy.Spider):
    name = 'epaperspider'
    start_urls = []
    page_no = {
        'BENGALURU': 2,
        'HUBLI': 2,
        'MANGALORE': 2,
        'SHIMOGA': 2
    }
    curr_date = '0'
    last_date = ''
    # custom_settings = {
    #     'LOG_ENABLED': False,
    # }

    def parse(self, response):
        # print('A')
        curr_date = response.request.url.split('/')[5]
        return self.scrape_by_date(response, curr_date)
        # return self.create_pdf('2020-01-01','BENGALURU')

    def __init__(self,from_date):
        print('Adding URLs')
        to_date = datetime.date.today()
        # from_date = datetime.datetime.strptime(str(file.read()), '%Y-%m-%d').date()
        delta = to_date - from_date  # as timedelta
        for i in range(delta.days + 1):
            day = from_date + datetime.timedelta(days=i)
            EpaperSpider.start_urls.append('http://epaper.hosadigantha.com/epaper/archive/' + str(day))
        print(EpaperSpider.start_urls)
        EpaperSpider.last_date = to_date

    # def __del__(self):
    # print('Deleting Temporary Files')
    # path = 'temp/'
    # for i in os.listdir(path):
    #     shutil.rmtree(path+i)
    # print('Updating latest file')
    # if EpaperSpider.last_date not in os.listdir(path):
    #     file_path = 'latest.txt'
    # with open(file_path, 'w') as file:
    #     file.write(EpaperSpider.last_date)

    # @inline_requests
    def scrape_by_date(self, response, curr_date):
        editions = response.css('.epost-title a::text').extract()
        edition_links = response.css('.epost-title a::attr(href)').extract()
        # print(editions)
        # print(edition_links)
        for i in range(len(edition_links)):
            # print(i)
            # EpaperSpider.curr_edition = editions[i]
            link = 'http://epaper.hosadigantha.com' + edition_links[i]
            yield scrapy.Request(link, callback=self.download_images,
                                 meta={'edition': editions[i], 'date': curr_date, 'page_no': 1})

    def download_images(self, response):
        # print('B')
        image_link = response.css('img#print_img::attr(src)').extract_first()
        edition = response.meta.get('edition')
        curr_date = response.meta.get('date')
        page_no = response.meta.get('page_no')
        print('Downloading Page No.' + str(page_no) + ' for the edition ' + edition + ' dated ' + curr_date)
        temp_folder = os.listdir('temp/')
        if curr_date not in temp_folder:
            os.mkdir('temp/' + str(curr_date))
        # Creating the folder
        edition_folder = os.listdir(
            'temp/' + str(curr_date) + '/')
        if edition not in edition_folder:
            os.mkdir('temp/' + str(curr_date) + '/' + str(
                edition))
        # image download
        path = 'temp/' + str(curr_date) + '/' + str(
            edition) + '/page'
        if image_link is not None:
            img_data = requests.get(image_link).content
            # print('D')
            with open(path + str(page_no) + '.jpg', 'wb') as handler:
                handler.write(img_data)
        next_page = 'http://epaper.hosadigantha.com' + response.css('.next a::attr(href)').extract_first()
        total_pages = response.css('.text-center:nth-child(23)::text').extract_first()
        # print(total_pages)
        if page_no < int(total_pages):
            page_no += 1
            yield response.follow(next_page, callback=self.download_images,
                                  meta={'edition': edition, 'date': curr_date, 'page_no': page_no})
        else:
            return self.create_pdf(curr_date, edition)

    def create_pdf(self, date, edition):
        print('Creating pdf for ' + str(edition) + ' dated ' + str(date))
        date_folder = os.listdir('pdfs/')
        if date not in date_folder:
            os.mkdir('pdfs/' + str(date))
        images_list = os.listdir('temp/' + str(date) + '/' + str(edition) + '/')
        max_height = 0
        max_width = 0
        for image in images_list:
            img = cv2.imread('temp/' + str(date) + '/' + str(edition) + '/' + image)
            height, width, channels = img.shape
            if height > max_height:
                max_height = height
            if width > max_width:
                max_width = width
        pdf = FPDF(unit="pt", format=[max_width, max_height])
        # print(images_list)
        # os.chdir('temp/' + str(date) + '/' + str(
        #     edition) + '/')
        for i in range(1, len(images_list) + 1):
            pdf.add_page()
            # print(i)
            pdf.image('temp/' + str(date) + '/' + str(edition) + '/'+'page' + str(i) + '.jpg', 0, 0,max_width,max_height)
        pdf.output('pdfs/' + str(date) + '/' + str(
            edition) + '_' + str(date) + '_' + 'hosadigantha' + '.pdf', "F")
        print('PDF created for the edition ' +edition + ' dated '+date)
        self.delete_images(edition, date)
        return

    def delete_images(self, edition, date):
        print("Emptying temporary folder for " + str(date) +' '+ str(edition))
        images_list = os.listdir(
            'temp/' + str(date) + '/' + str(edition))
        for i in images_list:
            os.remove('temp/' + str(date) + '/' + str(
                edition) + '/' + i)
        return


process = CrawlerProcess()
process.crawl(EpaperSpider,from_date=from_date)
process.start()