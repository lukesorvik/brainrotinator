"""This module implements uploading videos on YouTube via Selenium using metadata JSON file
    to extract its title, description etc."""

from typing import DefaultDict, Optional, Tuple
from selenium_firefox.firefox import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from collections import defaultdict
from datetime import datetime
import json
import time
from .Constant import *
from pathlib import Path
import logging
import platform

logging.basicConfig()

import random



#used to generate a random wait time to perform the actions on the browser
def random_time():
	rand : int = random.randint(1, 3)
	print("Random time: ", rand)
	return rand

def load_metadata(metadata_json_path: Optional[str] = None) -> DefaultDict[str, str]:
	if metadata_json_path is None:
		return defaultdict(str)
	with open(metadata_json_path, encoding='utf-8') as metadata_json_file:
		return defaultdict(str, json.load(metadata_json_file))


class InstagramUploader:
	"""A class for uploading videos on Instagram via Selenium using metadata JSON file
	to extract its title, description etc"""

	def __init__(self, video_path: str, metadata_json_path: Optional[str] = None,
	             thumbnail_path: Optional[str] = None,
	             profile_path: Optional[str] = str(Path.cwd()) + "/profile",
              headless : bool = True) -> None:
		self.video_path = video_path
		self.thumbnail_path = thumbnail_path
		self.metadata_dict = load_metadata(metadata_json_path)
		self.browser = Firefox(profile_path=profile_path, pickle_cookies=True, full_screen=False, headless=headless)
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.DEBUG)
		self.__validate_inputs()
		print("headless for instagram =" +str(headless))
			

		self.is_mac = False
		if not any(os_name in platform.platform() for os_name in ["Windows", "Linux"]):
			self.is_mac = True

		self.logger.debug("Use profile path: {}".format(self.browser.source_profile_path))

	def __validate_inputs(self):
		if not self.metadata_dict[Constant.VIDEO_TITLE]:
			self.logger.warning(
				"The video title was not found in a metadata file")
			self.metadata_dict[Constant.VIDEO_TITLE] = Path(
				self.video_path).stem
			self.logger.warning("The video title was set to {}".format(
				Path(self.video_path).stem))
		if not self.metadata_dict[Constant.VIDEO_DESCRIPTION]:
			self.logger.warning(
				"The video description was not found in a metadata file")

	def upload(self):
		try:
			self.login()
			return self.__upload()
		except Exception as e:
			print(e)
			self.__quit()
			raise

	def login(self):
		self.browser.get("https://www.instagram.com/")
		time.sleep(1)

		if self.browser.has_cookies_for_current_website():
			self.browser.load_cookies()
			self.logger.debug("Loaded cookies from {}".format(self.browser.cookies_folder_path))
			time.sleep(1)
			self.browser.refresh()
		else:
			self.logger.info('Please sign in and then press enter')
			input()
			self.browser.get("https://www.instagram.com/")
			time.sleep(3)
			self.browser.save_cookies()
			self.logger.debug("Saved cookies to {}".format(self.browser.cookies_folder_path))

	def __clear_field(self, field):
		field.click()
		time.sleep(3)
		if self.is_mac:
			field.send_keys(Keys.COMMAND + 'a')
		else:
			field.send_keys(Keys.CONTROL + 'a')
		time.sleep(2)
		field.send_keys(Keys.BACKSPACE)

	def __write_in_field(self, field, string, select_all=False):
		if select_all:
			self.__clear_field(field)
		else:
			field.click()
			time.sleep(random_time())

		field.send_keys(string)
	
	#find element, if not found, wait 3 seconds and try again
	#by - the type of element to find
	#value - the value of the element to find
	#name - the name of the element to find
	#return - the element found
	def find_element(self, by, value: str, name: str):
		element = None
		startTime = time.time()
		while element is None:
			element = self.browser.find(by, value)
			time.sleep(3)
			print(f"{name} not found")
			#if 1 minute has passed, break the loop
			if time.time() - startTime > 60:
				break

		print(f"{name} found")
		return element

	def __upload(self) -> bool:
		self.browser.get("https://www.instagram.com/?next=%2F")
		uploading_status_container = InstagramUploader.find_element(self,By.CSS_SELECTOR, 'button._a9--:nth-child(2)', "uploading status container")
		uploading_status_container.click()
		print("clicked no updates")
		time.sleep(2)
		upload_button = None
		upload_button = InstagramUploader.find_element(self,By.XPATH, '/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[2]/div[7]/div/span/div/a', "upload button")
		upload_button.click()
		print("clicked create")
		time.sleep(3)
		self.browser.find(By.XPATH, '/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[2]/div[7]/div/span/div/div/div/div[1]/a[1]').click()
		print("clicked post")
		time.sleep(3)

		absolute_video_path = str(Path.cwd() / self.video_path)
		videoUpload = InstagramUploader.find_element(self,By.CSS_SELECTOR,'._ac69', "video upload")
		videoUpload.send_keys(absolute_video_path)
		print("gave video path: ", absolute_video_path)
    
    
		time.sleep(3)
		next = InstagramUploader.find_element(self,By.CSS_SELECTOR, '._acap', "next")
		next.click()
		print("clicked next")
		time.sleep(3)
		size = InstagramUploader.find_element(self,By.CSS_SELECTOR, 'div.xnz67gz > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) > button:nth-child(1)', "size")
		size.click()
		print("clicked size")
		time.sleep(3)
		phone_resolution = InstagramUploader.find_element(self,By.CSS_SELECTOR, 'div.x1i10hfl:nth-child(5)', "phone resolution")
		phone_resolution.click()
		print("clicked phone resolution")

		clickOff = InstagramUploader.find_element(self,By.CSS_SELECTOR, 'div.xnz67gz > div:nth-child(1) > div:nth-child(3)', "click off")
		clickOff.click()
		time.sleep(3)
		next = InstagramUploader.find_element(self,By.CSS_SELECTOR, '.x1f6kntn', "next")
		next.click()
		print("clicked next")
		time.sleep(3)
		next = InstagramUploader.find_element(self,By.CSS_SELECTOR, '.xyamay9 > div:nth-child(1)', "next")
		next.click()
		print("clicked next")
		time.sleep(3)
		
		description_field = self.browser.find(By.XPATH, '/html/body/div[6]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[2]/div/div/div/div[1]/div[2]/div/div[1]/div[1]')
		
		video_description :str = self.metadata_dict[Constant.VIDEO_DESCRIPTION]
		video_description = video_description.replace("\n", Keys.ENTER)
		if video_description:
			description_field = self.browser.find(By.CSS_SELECTOR, '.x1hnll1o')
			print("Video Description: ", video_description)
			description_field.click()
			time.sleep(2)
			[description_field.send_keys(c) for c in video_description] #send_keys(video_description)
		print("Video description added")
		time.sleep(2)
		share = InstagramUploader.find_element(self,By.CSS_SELECTOR, '.x1f6kntn', "share")
		share.click()
		print("clicked share")
		
        #uploading_status_container = self.browser.find(By.XPATH, Constant.UPLOADING_STATUS_CONTAINER)
		uploading_status_container_done = InstagramUploader.find_element(self,By.CSS_SELECTOR, 'div.x5yr21d:nth-child(1) > div:nth-child(1) > div:nth-child(2)', "uploading status container done")
		
		self.__quit()
		return True

		


	def __get_video_id(self) -> Optional[str]:
		video_id = None
		try:
			video_url_container = self.browser.find(
				By.XPATH, Constant.VIDEO_URL_CONTAINER)
			video_url_element = self.browser.find(By.XPATH, Constant.VIDEO_URL_ELEMENT, element=video_url_container)
			video_id = video_url_element.get_attribute(
				Constant.HREF).split('/')[-1]
		except:
			self.logger.warning(Constant.VIDEO_NOT_FOUND_ERROR)
			pass
		return video_id

	def __quit(self):
		self.browser.driver.quit()
