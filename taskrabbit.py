import os.path

# noinspection PyUnresolvedReferences
import cchardet  # https://beautiful-soup-4.readthedocs.io/en/latest/#improving-performance
# noinspection PyUnresolvedReferences
import lxml  # https://beautiful-soup-4.readthedocs.io/en/latest/#improving-performance
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from textblob import TextBlob

PATH = './taskrabbit_services.html'

options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")


class Main:
    def __init__(self):
        page_source = self.load('https://www.taskrabbit.co.uk/services')
        soup = self.make_soup(page_source)
        items = soup.findAll('div', attrs={'class': 'mg-panel-item'})
        dataframe = {
            "Category": [],
            "Sub Category": []
        }
        for section in items:
            title_container = section.find('div', attrs={'class': 'mg-panel__title'})
            titleBlob = TextBlob(title_container.a.text)
            sub_items = section.findAll('li', attrs={'class': 'mg-panel__template-item'})
            for sub_section in sub_items:
                subtitleBlob = TextBlob(sub_section.a.text)
                dataframe['Category'].append(" ".join(titleBlob.words[:-1] + titleBlob.words[-1:].singularize()))
                dataframe['Sub Category'].append(
                    " ".join(subtitleBlob.words[:-1] + subtitleBlob.words[-1:].singularize()))

        df = pd.DataFrame(dataframe)
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        writer = pd.ExcelWriter('categories_taskrabbit.xlsx', engine='xlsxwriter')

        # Convert the dataframe to an XlsxWriter Excel object.
        df.to_excel(writer, sheet_name='Categories')

        # Close the Pandas Excel writer and output the Excel file.
        writer.close()

    @staticmethod
    def load(url):
        if not os.path.isfile(PATH):
            driver = webdriver.Firefox(options=options)  # Optional argument, if not specified will search path.

            driver.get(url)

            source = driver.page_source

            driver.quit()
            with open(PATH, 'w') as fp:
                fp.write(source)
                fp.close()
        else:
            with open(PATH) as fp:
                source = fp.read()

        return source

    @staticmethod
    def make_soup(source):
        return BeautifulSoup(source, "lxml")


if __name__ == '__main__':
    main = Main()
