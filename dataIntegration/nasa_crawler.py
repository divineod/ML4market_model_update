import configparser
import os
import shutil

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from datetime import datetime
from time import sleep
from typing import List


class NASADataDownloader:

    def __init__(self, driver_path, download_path, config_path):
        self.download_path = download_path
        self.driver_path = driver_path
        self.driver = None
        self.market_info = self._read_market_config(config_path)


    @staticmethod
    def _read_market_config(file_path):
        config = configparser.ConfigParser()
        config.read(file_path)

        market_data = {}
        for section in config.sections():
            state, district, market = section.split(", ")
            coordinates = config[section]["coordinates"]
            full_address = f"{state}, {district}, {market}"
            lat, lon = coordinates.split(", ")
            market_data[full_address] = [float(lat.split("°")[0]), float(lon.split("°")[0])]

        return market_data

    def _initiate_driver(self, driver_path, download_path):
        chrome_options = Options()
        prefs = {
            'download.default_directory': download_path,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True
        }
        chrome_options.add_experimental_option('prefs', prefs)
        service = Service(driver_path)
        return webdriver.Chrome(service=service, options=chrome_options)

    def _accept_user_terms(self):
        try:
            agree_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'enable-btn')))
            agree_button.click()
        except Exception as e:
            print(f"Error accepting user terms: {e}")

    def _select_community(self, value='re'):
        community_dropdown = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'usercommunity')))
        Select(community_dropdown).select_by_value(value)

    def _select_data_option(self, value='daily'):
        data_dropdown = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'usertemporal')))
        Select(data_dropdown).select_by_value(value)

    def _set_coordinates(self, lat: int, lon: int):
        lat_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'latdaily')))
        lat_input.clear()
        lat_input.send_keys(str(lat))

        lon_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'londaily')))
        lon_input.clear()
        lon_input.send_keys(str(lon))

    def _set_date_range(self, start_date="01/01/2019", end_date=None):
        if not end_date:
            end_date = datetime.now().strftime('%d/%m/%Y')

        start_date_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'datepickerstart')))
        start_date_input.clear()
        start_date_input.send_keys(start_date)

        end_date_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'datepickerend')))
        end_date_input.clear()
        end_date_input.send_keys(end_date)

        # Click outside the calendar to close it
        somewhere_outside = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        somewhere_outside.click()

    def _select_parameter_tree(self):

        # List of root nodes (parameters)
        root_parameters = ['Temperatures', 'Humidity/Precipitation']

        for parameter in root_parameters:
            # Check if the parameter is in closed state (needs to be expanded)
            sleep(5)
            param_element = self.driver.find_element(By.ID, parameter)
            if 'jstree-closed' in param_element.get_attribute('class'):

                self.driver.execute_script("arguments[0].click();", param_element)
                param_element.click()
                # Allow some time for the tree to expand (can adjust based on actual behavior)
                sleep(5)  # can use explicit waits or WebDriverWait as a more robust solution

    def _select_file_format(self, value='CSV'):
        dropdown = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'userformat')))
        Select(dropdown).select_by_value(value)

    def _download_data(self, market_name: str):
        submit_btn = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'submitbutton')))
        submit_btn.click()

        # Wait for the download link to appear and then download the file
        sleep(5)
        download_button = WebDriverWait(self.driver, 60).until(EC.presence_of_element_located((By.ID, 'exportCSV')))
        download_button.click()
        print(f"Data for {market_name} has been scraped")

    def _rename_file(self, files_before: List[str], market_name: str):

        # Wait for a new file to appear in the download directory
        while True:
            files_after = os.listdir(self.download_path)
            new_files = set(files_after) - set(files_before)
            if new_files:
                # A new file has appeared, so the download is complete
                break
            sleep(1)  # Wait for 1 second before checking again

        # Rename the latest download file to correspond to the particular market
        shutil.move(f"{self.download_path}/{new_files.pop()}", f"{self.download_path}/{market_name.replace(', ', '_')}.csv")


    def fetch_data(self):

        for market, coords in self.market_info.items():
            print("Scraping new source")
            self.driver = self._initiate_driver(self.driver_path, self.download_path)
            self.driver.get('https://power.larc.nasa.gov/data-access-viewer/')
            self._accept_user_terms()
            self._select_community()
            self._select_data_option()
            self._set_coordinates(*coords)
            self._set_date_range()
            self._select_file_format()
            self._select_parameter_tree()

            # Handle the file download and renaming
            files_before = os.listdir(self.download_path)    # Get a list of all files in the download directory before starting the download
            self._download_data(market_name=market)
            self._rename_file(files_before=files_before, market_name=market)

            # Pause before next iteration to avoid overwhelming the server
            sleep(10)

        self.driver.quit()


if __name__ == "__main__":
    # Change paths as necessary
    DRIVER_PATH = ('/Users/divinefavourodion/Documents/YourVirtualColdChainAssistant/ML4market-Nigeria/production_nig'
                   '/chromedriver 4')
    DOWNLOAD_PATH = '/Users/divinefavourodion/Documents/ML4market_model_update/data'
    CONFIG_PATH = '/Users/divinefavourodion/Documents/ML4market_model_update/dataIntegration/config.ini'

    downloader = NASADataDownloader(DRIVER_PATH, DOWNLOAD_PATH, CONFIG_PATH)
    downloader.fetch_data()


