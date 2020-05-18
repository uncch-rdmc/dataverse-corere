from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.support.ui import WebDriverWait
from corere.main import models as m
#from selenium.webdriver.support import expected_conditions as EC

# Part of this testing is based upon finding elements. If they aren't available, the test errors out.
# TODO: Future tests streamline login: https://stackoverflow.com/questions/22494583/login-with-code-when-using-liveservertestcase-with-django
class LoggingInTestCase(LiveServerTestCase):
    def setUp(self):
        self.selenium = webdriver.Chrome()
        m.User.objects.create_superuser('admin', 'admin@admin.com', 'password')
        super(LoggingInTestCase, self).setUp()

    def tearDown(self):
        self.selenium.quit()
        super(LoggingInTestCase, self).tearDown()

    def test_admin_login(self):
        selenium = self.selenium

        selenium.get(self.live_server_url) #root, not logged in
        selenium.find_element_by_id("sidebar")
        with self.assertRaises(NoSuchElementException):
            selenium.find_element_by_id("manuscript_table")
        
        selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", selenium.title)
        current_url = selenium.current_url
        username = selenium.find_element_by_id('id_username')
        password = selenium.find_element_by_id('id_password')
        username.send_keys('admin')
        password.send_keys('password')
        submit = selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        submit.send_keys(Keys.RETURN)

        self.assertIn("ion | Django site admin", selenium.title)

        selenium.get(self.live_server_url) #root, not logged in
        selenium.find_element_by_id("sidebar")
        #now we can find the table
        selenium.find_element_by_id("manuscript_table")








