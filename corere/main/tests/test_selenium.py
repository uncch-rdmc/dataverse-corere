from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
import time, unittest
from selenium.webdriver.support.ui import WebDriverWait, Select

from corere.main import models as m
from corere.apps.wholetale import models as wtm


# Part of this testing is based upon finding elements. If they aren't available, the test errors out.
# TODO: Future tests streamline login: https://stackoverflow.com/questions/22494583/login-with-code-when-using-liveservertestcase-with-django
#@unittest.skip("Don't want to test, broke after applying bootstrap, will come back to it when we do more exhaustive testing")
class LoggingInTestCase(LiveServerTestCase):
    def setUp(self):
        self.selenium = webdriver.Chrome()
        m.User.objects.create_superuser('admin', 'admin@admin.com', 'password')
        #We need add the other option for compute env with the current implementation
        wtm.ImageChoice.objects.get_or_create(wt_id="Other", name="Other", show_last=True)

        super(LoggingInTestCase, self).setUp()

    def tearDown(self):
        self.selenium.quit()
        super(LoggingInTestCase, self).tearDown()

    #@unittest.skip("Don't want to test")
    def test_admin_full_workflow_no_edition_no_dataverse(self):
        selenium = self.selenium

        ##### ADMIN LOG IN #####

        selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", selenium.title)
        current_url = selenium.current_url
        username = selenium.find_element_by_id('id_username')
        password = selenium.find_element_by_id('id_password')
        username.send_keys('admin')
        password.send_keys('password')
        admin_login_submit = selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("ion | Django site admin", selenium.title)

        #TODO: Investigate a way for the non-oauth user to skip being forced to select an oauth on the index page.
        #      We can't do any tests on it currently

        #############################
        ##### CREATE MANUSCRIPT #####
        #############################

        selenium.get(self.live_server_url+"/manuscript/create/")

        #NOTE: Not all fields for form are in this list. Exemptions, most env_info
        selenium.find_element_by_id('id_pub_name').send_keys('pub_name')
        selenium.find_element_by_id('id_pub_id').send_keys('pub_id')
        selenium.find_element_by_id('id_description').send_keys('description')
        #selenium.find_element_by_id('id_subject').send_keys('test') #DROPDOWN FIX
        selenium.find_element_by_id('id_additional_info').send_keys('additional_info')
        selenium.find_element_by_id('id_contact_first_name').send_keys('contact_first_name')
        selenium.find_element_by_id('id_contact_last_name').send_keys('contact_last_name')
        selenium.find_element_by_id('id_contact_email').send_keys('contact_email@test.test')
        Select(selenium.find_element_by_id('id_compute_env')).select_by_visible_text("Other") # select unneeded currently because its the only option
        selenium.find_element_by_id('id_operating_system').send_keys('operating_system')
        selenium.find_element_by_id('id_packages_info').send_keys('packages_info')
        selenium.find_element_by_id('id_software_info').send_keys('software_info')
        #operating system, required packages, statistical software
        #NOTE: The selenium test doesn't seem to do JS the same, so our janky formsets don't have a row displayed unless we click
        manuscript_create_add_author_link_button = selenium.find_element_by_xpath('//*[@id="author_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_author_link_button.send_keys(Keys.RETURN)
        selenium.find_element_by_id('id_author_formset-0-first_name').send_keys('author_0_first_name')
        selenium.find_element_by_id('id_author_formset-0-last_name').send_keys('author_0_last_name')
        #selenium.find_element_by_id('id_author_formset-0-identifier').send_keys('author_0_identifier')
        manuscript_create_add_data_source_link_button = selenium.find_element_by_xpath('//*[@id="data_source_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_data_source_link_button.send_keys(Keys.RETURN)
        selenium.find_element_by_id('id_data_source_formset-0-text').send_keys('data_source_0_text')
        manuscript_create_add_keyword_link_button = selenium.find_element_by_xpath('//*[@id="keyword_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_keyword_link_button.send_keys(Keys.RETURN)
        selenium.find_element_by_id('id_keyword_formset-0-text').send_keys('keyword_0_text')

        manuscript_create_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ##### UPLOAD MANUSCRIPT FILES (skipping for now) #####

        ##### ASSIGN AUTHOR TO MANUSCRIPT #####

        selenium.get(self.live_server_url+"/manuscript/1/addauthor/")
        #We don't fill out any fields for this form beacuse it is auto-populated with manuscript info
        manuscript_add_author_submit = selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        manuscript_add_author_submit.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING #####
        manuscript_create_submit_continue = selenium.find_element_by_id('createSubmissionButton')
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ###############################
        ##### CREATE SUBMISSION 1 #####
        ###############################

        Select(selenium.find_element_by_id('id_subject')).select_by_visible_text("Agricultural Sciences")
        manuscript_update_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### UPLOAD SUBMISSION FILES (skipping for now) #####

        ##### ADD SUBMISSION NOTES #####

        selenium.get(self.live_server_url+"/submission/1/info/")
        submission_info_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[5]')
        submission_info_submit_continue.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()
        
        ##### MANUSCRIPT LANDING REVIEW CURATION #####

        manuscript_review_submission = selenium.find_element_by_id('reviewSubmissionButtonMain')
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### CURATOR REVIEW - ISSUES #####
        #NOTE: Editor review is disabled for our install currently. When its re-enabled this will break. We should actually be testing both

        Select(selenium.find_element_by_id('id_curation_formset-0-_status')).select_by_visible_text("Minor Issues") 
        selenium.find_element_by_id('id_curation_formset-0-report').send_keys('report')
        selenium.find_element_by_id('id_curation_formset-0-needs_verification').click()
        Select(selenium.find_element_by_id('id_submission_editor_date_formset-0-editor_submit_date_month')).select_by_visible_text("January") 
        Select(selenium.find_element_by_id('id_submission_editor_date_formset-0-editor_submit_date_day')).select_by_visible_text("1") 
        Select(selenium.find_element_by_id('id_submission_editor_date_formset-0-editor_submit_date_year')).select_by_visible_text("2020") 
        submission_info_submit_continue_curation = selenium.find_element_by_id('submit_progress_curation_button')
        submission_info_submit_continue_curation.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING REVIEW VERIFICATION #####

        manuscript_review_submission = selenium.find_element_by_id('reviewSubmissionButtonMain')
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### VERIFIER REVIEW - ISSUES #####

        Select(selenium.find_element_by_id('id_verification_formset-0-_status')).select_by_visible_text("Minor Issues") 
        selenium.find_element_by_id('id_verification_formset-0-code_executability').send_keys('report')
        selenium.find_element_by_id('id_verification_formset-0-report').send_keys('report')
        submission_info_submit_continue_verification = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[14]')
        submission_info_submit_continue_verification.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING / GENERATE REPORT / RETURN SUBMISSION #####

        manuscript_send_report_button = selenium.find_element_by_id('sendReportButton')
        manuscript_send_report_button.send_keys(Keys.RETURN)
        time.sleep(.5) #Needed to wait for this button to appear on the same page
        manuscript_return_submission_button = selenium.find_element_by_id('returnSubmissionButton')
        manuscript_return_submission_button.send_keys(Keys.RETURN)
        time.sleep(.5) #Needed to wait for this button to appear on the same page
        manuscript_create_submit_continue = selenium.find_element_by_id('createSubmissionButton')
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ###############################
        ##### CREATE SUBMISSION 2 #####
        ###############################

        Select(selenium.find_element_by_id('id_subject')).select_by_visible_text("Agricultural Sciences")
        manuscript_update_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### UPLOAD SUBMISSION FILES (skipping for now) #####

        ##### ADD SUBMISSION NOTES #####

        selenium.get(self.live_server_url+"/submission/2/info/")
        submission_info_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[5]')
        submission_info_submit_continue.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING REVIEW CURATION #####

        manuscript_review_submission = selenium.find_element_by_id('reviewSubmissionButtonMain')
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### CURATOR REVIEW - NO ISSUES #####
        #NOTE: Editor review is disabled for our install currently. When its re-enabled this will break. We should actually be testing both

        Select(selenium.find_element_by_id('id_curation_formset-0-_status')).select_by_visible_text("No Issues") 
        selenium.find_element_by_id('id_curation_formset-0-report').send_keys('report')
        selenium.find_element_by_id('id_curation_formset-0-needs_verification').click()
        Select(selenium.find_element_by_id('id_submission_editor_date_formset-0-editor_submit_date_month')).select_by_visible_text("January") 
        Select(selenium.find_element_by_id('id_submission_editor_date_formset-0-editor_submit_date_day')).select_by_visible_text("2") 
        Select(selenium.find_element_by_id('id_submission_editor_date_formset-0-editor_submit_date_year')).select_by_visible_text("2020") 
        submission_info_submit_continue_curation = selenium.find_element_by_id('submit_progress_curation_button')
        submission_info_submit_continue_curation.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING REVIEW VERIFICATION #####

        manuscript_review_submission = selenium.find_element_by_id('reviewSubmissionButtonMain')
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### VERIFIER REVIEW - NO ISSUES #####

        Select(selenium.find_element_by_id('id_verification_formset-0-_status')).select_by_visible_text("Success") 
        selenium.find_element_by_id('id_verification_formset-0-code_executability').send_keys('report')
        selenium.find_element_by_id('id_verification_formset-0-report').send_keys('report')
        submission_info_submit_continue_verification = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[14]')
        submission_info_submit_continue_verification.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING / CONFIRM DATAVERSE NEXT STEP #####

        dataverse_upload_manuscript_button = selenium.find_element_by_id('dataverseUploadManuscriptButtonMain')
        dataverse_upload_manuscript_button.send_keys(Keys.RETURN)

        #time.sleep(500000)






        




























