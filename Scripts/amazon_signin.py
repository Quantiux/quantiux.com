#!/usr/bin/env python3

import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


# main class to run Amazon auto sign-in script
class AmazonAPI:
    # initializer
    def __init__(self, browser, url, wait) -> None:
        self.browser = browser
        self.url = url
        self.wait = wait
        self.userId, self.password = "<your_userID>", "<your_password>"  # amazon login info

    # method to load 'Sign in' page
    def loadSigninPage(self) -> None:
        # load amazon.com main page
        self.browser.get(self.url)
        logging.info("Signing into Amazon...")

        # click 'Sign in' box at top-right
        signin_box = self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, '//span[@id="nav-link-accountList-nav-line-1"]')
            )
        )
        signin_box.click()

    # method to enter user ID
    def enterUserID(self) -> None:
        # send account userID to user ID window
        signin_elem = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[@id="ap_email"]'))
        )
        signin_elem.send_keys(self.userId)

        # click Continue button
        continue_elem = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[@id="continue"]'))
        )
        continue_elem.click()

    # method to enter password
    def enterPassword(self) -> None:
        # send account password to password window
        password_elem = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[@id="ap_password"]'))
        )
        password_elem.send_keys(self.password)

        # click 'Sign in' button
        signin_button = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[@id="signInSubmit"]'))
        )
        signin_button.click()

    # method to enter OTP
    def enterOTP(self) -> None:
        # send OTP to OTP code box
        otp_box = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[@id="auth-mfa-otpcode"]'))
        )
        otp_string = input("Enter OTP from phone: ")
        otp_box.send_keys(otp_string)

        # click OTP button
        otp_button = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[@id="auth-signin-button"]'))
        )
        otp_button.click()
        logging.info("Signed in successfully.")


def main() -> None:
    # set logging config
    logging.basicConfig(
        level=logging.INFO,
        format="(%(levelname)s) %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # initialize variables
    url = "https://www.amazon.com"
    chromePath = "/usr/bin/google-chrome-stable"  # location of browser binary
    options = webdriver.ChromeOptions()
    options.binary_location = chromePath
    browser = webdriver.Chrome(options=options)
    browser.set_page_load_timeout(5)  # wait-time for page loading
    wait = WebDriverWait(browser, 5)  # wait-time for XPath element extraction

    # run codes
    amazon = AmazonAPI(browser, url, wait)  # create AmazonAPI() object
    amazon.loadSigninPage()
    amazon.enterUserID()
    amazon.enterPassword()
    amazon.enterOTP()  # comment this line if OTP is not needed


# run main function
if __name__ == "__main__":
    main()
