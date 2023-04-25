# Author: Aljosa Janjic
# Date: 2023-04
# Version: 1.0.2

import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
from twilio.rest import Client
import random
from lxml import html
from urllib.parse import urlparse, parse_qs


def get_drvier():
  # Set options to make browsing easier
  options = webdriver.ChromeOptions()
  options.add_argument("disable-infobars")
  options.add_argument("start-maximized")
  options.add_argument("disable-dev-shm-usage")
  options.add_argument("no-sandbox")
  options.add_experimental_option("excludeSwitches", ["enable-automation"])
  options.add_argument("disable-blink-features=AutomationControlled")
  driver = webdriver.Chrome(options=options)
  driver.get(f"{url}")
  return driver


def send_sms(itemColor, itemSize, product_name, url):
  account_sid = os.environ['TWILIO_ACCOUNT_SID']
  auth_token = os.environ['TWILIO_AUTH_TOKEN']
  client = Client(account_sid, auth_token)

  message = client.messages \
                  .create(
                       body=f"""
                       {itemColor} {product_name} Size: {itemSize} is now avaiable. Buy it now on: {url}
                       """,
                       from_= os.getenv('TWILIO_NUMBER'),
                       to= os.getenv('RECIVER_NUMBER')
                   )

  print(message.sid)


def send_email(url, itemColor, itemSize, sms):

  sender = os.getenv('GOLDEN_MAIL')
  # Add variable for  reciver email address
  receiver = os.getenv('RECEIVER_MAIL')
  password = os.getenv('GOLDEN_PASSWORD')

  product_name = ''
  match = re.search(r"/([^/]+)-p\d+\.html", url)
  if match:
    product_name = match.group(1).replace("-", " ").upper()

  message = MIMEMultipart()
  message['From'] = sender
  message['To'] = receiver
  message[
    'Subject'] = f'{itemColor} {product_name} is available. Size: {itemSize}'

  body = f"""
    <h2>{itemColor} {product_name} is available. Size: {itemSize}</h2>
    
    {product_name} je na stanju
    <a href={url}'> Kupi odmah! </a>
    """
  mimetext = MIMEText(body, 'html')
  message.attach(mimetext)

  server = smtplib.SMTP('smtp.office365.com', 587)
  server.starttls()
  server.login(sender, password)
  message_text = message.as_string()
  server.sendmail(sender, receiver, message_text)
  server.quit()
  print('Mail sent')
  global found
  found = True
  if sms == 'DA':
    print('Bupi-bupi saljem SMS ali moras ukloniti komentar iz koda')
    #send_sms(itemColor, itemSize, product_name, url)


def buy_product(driver, soup, itemSize, itemColor):
  # Close first cookies

  driver.find_element(by='id', value='onetrust-close-btn-container').click()

  # Continue in Slovakia
  driver.find_element(
    by='xpath',
    value=
    '/html/body/div[1]/div[1]/div[2]/div[2]/div/div/div/div[2]/section[1]/button[1]'
  ).click()

  page_content = driver.page_source

  # Parse the page content as an HTML tree
  tree = html.fromstring(page_content)

  # List of colors and select color
  colors_available = tree.xpath(
    '//div[@class="product-detail-color-selector__color-area"]//span[@class="screen-reader-text"]'
  )
  for index, element in enumerate(colors_available):
    value = f'//*[@id="main"]/article/div[2]/div[1]/div[2]/div[1]/div[4]/div/ul/li[{index + 1}]/button/div[1]'
    if itemColor == element.text:
      driver.find_element(by='xpath', value=value).click()

  time.sleep(2)
  # List of sizes and select size
  sizes = tree.xpath('//span[@class="product-size-info__main-label"]')

  for index, size in enumerate(sizes):
    value = f'//*[@id="product-size-selector-{v1_param}-item-{index}"]/div/div/span'
    if itemSize == size.text:
      driver.find_element(by='xpath', value=value).click()

  time.sleep(3)
  # Add to cart
  driver.find_element(
    by='xpath',
    value='//*[@id="main"]/article/div[2]/div[1]/div[2]/div[1]/div[6]/button'
  ).click()

  time.sleep(3)


def get_krpu(url, itemColor='', itemSize='', buy='', sms=''):
  if itemColor == '' or itemSize == '':
    itemColor = input("Koju boju proizvoda zelis?: ")
    itemSize = input(
      'Koju velicinu zelis? (Za ispis svih velicina unesi "X"): ').upper()
    sms = input('Poslati SMS poruku? (Da/Ne): ').upper()
    # if itemSize != 'X':
    #     buy = input('Zelis li da proizvod bude kupljen "da/ne"?: ').lower()

  driver = get_drvier()

  content = driver.page_source

  soup = BeautifulSoup(content, 'html.parser')

  with open('dostupnost.txt', 'w+') as f:
    f.write(str(soup))
    f.seek(0)
    content = f.read()

  # Extract the relevant information

  first_name_index = content.find(f'"name":"{itemColor}","reference"')
  last_name_index = first_name_index + len('"name": ') + len(itemColor)

  first_object_index = content.find('"sizes":[{', first_name_index)
  last_object_index = content.find('],"description"', first_object_index)

  result = {
    'name': content[first_name_index + 8:last_name_index],
    'sizes': content[first_object_index + 9:last_object_index]
  }

  sizes = '[' + result['sizes'] + ']'
  result['sizes'] = json.loads(sizes)

  # Print the result
  for size in result['sizes']:
    if size['name'] == itemSize:
      if size['availability'] != 'in_stock':
        global atempt
        print(f'Not available {atempt}')
        time.sleep(random.randint(30, 60))
      else:
        send_email(url, itemColor, itemSize, sms)
        time.sleep(2)
        if buy == 'da':
          buy_product(driver, soup, itemSize, itemColor)
  if itemSize == 'X':
    print(result)


found = False
atempt = 1

url = input('Koji proizvod zelis (URL link)?: ')

headers = {
  "User-Agent":
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36"
}

# Parse the URL and extract the query string
parsed_url = urlparse(url)
query_string = parsed_url.query

# Parse the query string and extract the v1 parameter value
query_params = parse_qs(query_string)
v1_param = query_params.get('v1', [None])[0]

while found == False:
  get_krpu(url)
  atempt += 1
