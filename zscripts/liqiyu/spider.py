
import requests
from bs4 import BeautifulSoup
import pandas as pd


def get_carbon_price():
    # 1. send a request to the website
    url = 'https://tradingeconomics.com/commodity/carbon'
    response = requests.get(url)

    # 2. parse the html content of the web page with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # 3. Extract the carbon price
    price_div = soup.find('div', class_='table-responsive')
    price_table = price_div.find_all('td')
    price = [i.text for i in price_table]

    return price[1]


# print the price
print(get_carbon_price())
