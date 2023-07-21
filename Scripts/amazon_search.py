#!/usr/bin/env python3

import logging
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


# main class to run Amazon search
class AmazonAPI:
    # initializer
    def __init__(self, browser, url, wait) -> None:
        self.browser = browser
        self.url = url
        self.wait = wait

    # method to search and load 1st product list page
    def search_amazon(self, search_term, brand, rating, max_price) -> None:
        # load amazon.com
        self.browser.get(self.url)

        # send search term to search box
        search_box = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[@aria-label="Search Amazon"]'))
        )
        search_box.send_keys(search_term)

        # click search button
        search_button = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[@id="nav-search-submit-button"]'))
        )
        search_button.click()
        logging.info("Searching for '%s'...", search_term)

        # click brand name
        brand_box = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//span[text()="' + brand + '"]'))
        )
        brand_box.click()
        logging.info("Filtered by brand '%s'", brand)

        # click star rating
        rating_box = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//section[@aria-label="' + rating + '"]'))
        )
        rating_box.click()
        logging.info("Filtered by rating '%s'", rating)

        # send max price value to high-price box
        highprice_box = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[@id="high-price"]'))
        )
        highprice_box.send_keys(max_price)
        logging.info("Filtered by price range '$0-$%s'", max_price)

        # click 'Go' button (to load 1st search page)
        go_button = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, '//input[contains(@class,"a-button-input")]')
            )
        )
        go_button.click()

    # method to get item info (name, price, price/oz) for each item
    # called by get_items() below
    def get_item_info(self, item):
        # get item name
        name_elem = item.find_element(
            By.XPATH, './/div[contains(@class, "a-section a-spacing-none")]'
        )

        # get item price (assign None if no info is available)
        try:
            whole_price_elem = item.find_element(By.XPATH, './/span[@class="a-price-whole"]')
        except NoSuchElementException:
            whole_price_elem = []

        try:
            fraction_price_elem = item.find_element(By.XPATH, './/span[@class="a-price-fraction"]')
        except NoSuchElementException:
            fraction_price_elem = []

        if whole_price_elem != [] and fraction_price_elem != []:
            price = ".".join([whole_price_elem.text, fraction_price_elem.text])  # type: ignore
        else:
            price = None

        # get item price/oz (assign None if no info is available)
        try:
            rate_elem = item.find_element(
                By.XPATH, './/span[@class="a-size-base a-color-secondary"]'
            )
            rate = rate_elem.text
        except NoSuchElementException:
            rate = None

        # collect item info
        item_info = {
            "name": name_elem.text,
            "price": price,
            "price_per_oz": rate,
        }
        return item_info

    # method to cycle through pages and get item name, price and price/oz
    def get_items(self):
        item_list = []

        k = 1
        while True:  # loop through last page of product list
            # get elements for all items on current page
            item_elems = self.wait.until(
                EC.visibility_of_all_elements_located(
                    (
                        By.XPATH,
                        '//div[contains(@class,"puis-padding-left-small")]',
                    )
                )
            )

            # extract name, price, price/oz from each item_elem
            for item in item_elems:
                item_info = self.get_item_info(item)
                item_list.append(item_info)

            logging.info("Page #%s scanned", k)

            # get elements for 'Next' button (to go to next list page) and click it
            try:
                next_button = self.wait.until(
                    EC.visibility_of_element_located((By.XPATH, '//a[contains(text(),"Next")]'))
                )
            except TimeoutException:  # last page reached
                break  # exit while loop
            next_button.click()
            k += 1

        logging.info("All pages scanned (%s items found in %s pages)", len(item_list), k)

        return item_list

    # method to save data
    def save_data(self, item_list, file) -> None:
        logging.info("Saving data...")
        df = pd.DataFrame(item_list)
        df.to_csv(file)
        logging.info("Done.")


def main() -> None:
    # set logging config
    logging.basicConfig(
        level=logging.INFO,
        format="(%(levelname)s) %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # initialize variables
    url = "https://www.amazon.com"
    search_term = "wet cat food"
    brand = "Friskies"
    rating = "4 Stars & Up"
    max_price = 25

    # initialize Firefox browser (see https://stackoverflow.com/a/56502916)
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")  # use headless option
    browser = webdriver.Firefox(options=options)
    browser.set_page_load_timeout(5)  # wait-time for page loading
    wait = WebDriverWait(browser, 5)  # wait-time for XPath element extraction

    # run codes
    amazon = AmazonAPI(browser, url, wait)  # create AmazonAPI() object
    amazon.search_amazon(search_term, brand, rating, max_price)  # load 1st results page
    item_list = amazon.get_items()  # get item info for all search results
    with open("../Results/amazon.csv", "w") as fp:  # save data
        amazon.save_data(item_list, fp)


# run main function
if __name__ == "__main__":
    main()
