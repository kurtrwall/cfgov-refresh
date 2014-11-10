# import nose

# from selenose.cases import SeleniumTestCase
# from nose.plugins.attrib import attr
# from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as ec

def click_filter_posts_dropdown(test):
    """Finds dropdown button then clicks it"""
    test.filter_dropdown_button = test.driver.find_element_by_xpath('//button[contains(text(), "Filter posts")]')
    if test.filter_dropdown_button.get_attribute('aria-pressed') == 'false':
        test.filter_dropdown_button.click()

def coerce_category_for_dom(category):
    if category.find(' ') != -1:
        category = category.replace(' ', '+')
    elif category.find('+') != -1:
        category = category.replace('+', ' ')

    return category

def scroll(driver):
    body = driver.find_element_by_xpath('//body')
    body.send_keys(Keys.SPACE)