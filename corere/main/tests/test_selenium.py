import time, unittest
from django.test import LiveServerTestCase
#from seleniumrequests import Chrome
from seleniumwire import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

from corere.main import models as m
from corere.main import constants as c
from corere.apps.wholetale import models as wtm

# Part of this testing is based upon finding elements. If they aren't available, the test errors out.
# TODO: Future tests streamline login: https://stackoverflow.com/questions/22494583/login-with-code-when-using-liveservertestcase-with-django
class LoggingInTestCase(LiveServerTestCase):
    def setUp(self):
        self.options = Options()
        self.options.headless = True
        self.selenium = webdriver.Chrome(options=self.options)
        m.User.objects.create_superuser('admin', 'admin@test.test', 'password')

        #We need add the other option for compute env with the current implementation
        wtm.ImageChoice.objects.get_or_create(wt_id="Other", name="Other", show_last=True)

        super(LoggingInTestCase, self).setUp()

    def tearDown(self):
        self.selenium.quit()
        super(LoggingInTestCase, self).tearDown()

    # This tests most of the flow with all actions done by an admin.
    # Not tested: Edition, Dataverse, Files, Whole Tale
    # TODO: Hardcode no edition setting
    # TODO: UNDO THIS SKIP
    @unittest.skip("testing others now")
    def test_admin_only_mostly_full_workflow(self):
        selenium = self.selenium

        ##### ADMIN LOGIN #####

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

        manuscript = m.Manuscript.objects.latest('updated_at')
        selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/addauthor/")
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

        
        selenium.get(self.live_server_url+"/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
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

        selenium.get(self.live_server_url + "/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
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


    #TODO: Test non-logged-in user?

    # This tests most of the flow, with actions done by an admin-curator and a non-admin verifier (with access).
    # This includes inviting the users to CORE2 via the UI
    # Tests are also done with a verifier with no access to ensure privacy 
    # This uses selenium-wire to get responses, which is technically bad form for selenium but is helpful for us
    # Not tested: Edition, Dataverse, Files, Whole Tale
    # ...
    # This code does deep access tests as the manuscript/submission status changes
    # TODO: Hardcode no edition setting
    #@unittest.skip("testing others now")
    def test_3_user_workflow_with_access_checks(self):
        admin_selenium = self.selenium

        ##### ADMIN LOGIN #####

        admin_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", admin_selenium.title)
        current_url = admin_selenium.current_url
        username = admin_selenium.find_element_by_id('id_username')
        password = admin_selenium.find_element_by_id('id_password')
        username.send_keys('admin')
        password.send_keys('password')
        admin_login_submit = admin_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("ion | Django site admin", admin_selenium.title)

        ##### ADMIN CREATE CURATOR_ADMIN #####

        curator_admin = m.User.objects.create_superuser('curatoradmin', 'curatoradmin@test.test', 'password') 
        role_c = m.Group.objects.get(name=c.GROUP_ROLE_CURATOR) 
        role_a = m.Group.objects.get(name=c.GROUP_ROLE_AUTHOR) 
        role_e = m.Group.objects.get(name=c.GROUP_ROLE_EDITOR) 
        role_c.user_set.add(curator_admin) 
        role_a.user_set.add(curator_admin) 
        role_e.user_set.add(curator_admin) 

        ##### CURATOR_ADMIN LOGIN #####

        c_selenium = webdriver.Chrome(options=self.options) #webdriver.Chrome()

        c_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", c_selenium.title)
        current_url = c_selenium.current_url
        username = c_selenium.find_element_by_id('id_username')
        password = c_selenium.find_element_by_id('id_password')
        username.send_keys('curatoradmin')
        password.send_keys('password')
        admin_login_submit = c_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("ion | Django site admin", c_selenium.title)

        ##### CURATOR_ADMIN VERIFIER_IN CREATION #####

        #This verifier will have verifier to the tested manuscript
        c_selenium.get(self.live_server_url + "/site_actions/inviteverifier/")
        c_selenium.find_element_by_id('id_first_name').send_keys('verifier_in')
        c_selenium.find_element_by_id('id_last_name').send_keys('last_name')
        c_selenium.find_element_by_id('id_email').send_keys('verifier_in@test.test')

        verifier_in_create_button = c_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        verifier_in_create_button.send_keys(Keys.RETURN)

        verifier_in = m.User.objects.get(email='verifier_in@test.test')
        verifier_in.set_password('password')
        verifier_in.username = 'verifier_in'
        verifier_in.is_staff = True #allows admin login without oauth
        verifier_in.save()

        ##### VERIFIER IN LOGIN #####

        v_in_selenium = webdriver.Chrome(options=self.options)

        v_in_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", v_in_selenium.title)
        current_url = v_in_selenium.current_url
        username = v_in_selenium.find_element_by_id('id_username')
        password = v_in_selenium.find_element_by_id('id_password')
        username.send_keys('verifier_in')
        password.send_keys('password')
        admin_login_submit = v_in_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("ion | Django site admin", v_in_selenium.title)

        ##### CURATOR_ADMIN VERIFIER_OUT CREATION #####
        
        #This verifier will have no access to the tested manuscript
        c_selenium.get(self.live_server_url + "/site_actions/inviteverifier/")
        c_selenium.find_element_by_id('id_first_name').send_keys('verifier_out')
        c_selenium.find_element_by_id('id_last_name').send_keys('last_name')
        c_selenium.find_element_by_id('id_email').send_keys('verifier_out@test.test')

        verifier_out_create_button = c_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        verifier_out_create_button.send_keys(Keys.RETURN)

        verifier_out = m.User.objects.get(email='verifier_out@test.test')
        verifier_out.set_password('password')
        verifier_out.username = 'verifier_out'
        verifier_out.is_staff = True #allows admin login without oauth
        verifier_out.save()

        ##### VERIFIER_OUT LOGIN #####

        v_out_selenium= webdriver.Chrome(options=self.options)

        v_out_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", v_out_selenium.title)
        current_url = v_out_selenium.current_url
        username = v_out_selenium.find_element_by_id('id_username')
        password = v_out_selenium.find_element_by_id('id_password')
        username.send_keys('verifier_in')
        password.send_keys('password')
        admin_login_submit = v_out_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("ion | Django site admin", v_out_selenium.title)

        ##### ANON BROWSER (NO LOGIN) #####

        # This non-logged-in browser has no access to the system
        anon_selenium = webdriver.Chrome(options=self.options)
        #anon_selenium.get(self.live_server_url+"/manuscript/create/") #If we don't go to a page once, we can run into cookie issues while testing later

        #############################################
        ##### CURATOR_ADMIN MANUSCRIPT CREATION #####
        #############################################

        c_selenium.get(self.live_server_url+"/manuscript/create/")

        c_selenium.find_element_by_id('id_pub_name').send_keys('pub_name')
        c_selenium.find_element_by_id('id_pub_id').send_keys('pub_id')
        c_selenium.find_element_by_id('id_description').send_keys('description')
        c_selenium.find_element_by_id('id_additional_info').send_keys('additional_info')
        c_selenium.find_element_by_id('id_contact_first_name').send_keys('curatoradmin')
        c_selenium.find_element_by_id('id_contact_last_name').send_keys('contact_last_name')
        c_selenium.find_element_by_id('id_contact_email').send_keys('curatoradmin@test.test')
        Select(c_selenium.find_element_by_id('id_compute_env')).select_by_visible_text("Other") # select unneeded currently because its the only option
        c_selenium.find_element_by_id('id_operating_system').send_keys('operating_system')
        c_selenium.find_element_by_id('id_packages_info').send_keys('packages_info')
        c_selenium.find_element_by_id('id_software_info').send_keys('software_info')
        #NOTE: The selenium test doesn't seem to do JS the same, so our janky formsets don't have a row displayed unless we click
        manuscript_create_add_author_link_button = c_selenium.find_element_by_xpath('//*[@id="author_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_author_link_button.send_keys(Keys.RETURN)
        c_selenium.find_element_by_id('id_author_formset-0-first_name').send_keys('author_0_first_name')
        c_selenium.find_element_by_id('id_author_formset-0-last_name').send_keys('author_0_last_name')
        manuscript_create_add_data_source_link_button = c_selenium.find_element_by_xpath('//*[@id="data_source_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_data_source_link_button.send_keys(Keys.RETURN)
        c_selenium.find_element_by_id('id_data_source_formset-0-text').send_keys('data_source_0_text')
        manuscript_create_add_keyword_link_button = c_selenium.find_element_by_xpath('//*[@id="keyword_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_keyword_link_button.send_keys(Keys.RETURN)
        c_selenium.find_element_by_id('id_keyword_formset-0-text').send_keys('keyword_0_text')

        manuscript_create_submit_continue = c_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_create_submit_continue.send_keys(Keys.RETURN) 

        ##### UPLOAD MANUSCRIPT FILES (skipping for now) #####

        ##### CURATOR_ADMIN VERIFIER ADD #####

        # NOTE: For some reason our verifiers don't show up as options for the assignverifier page
        #       This may be because of the javascript/ajax(?)
        #       So instead we'll assign via the backend, but this is a TODO for later
        #       - When we do this, we may want to move where it happens in the flow

        #c_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/assignverifier/") 

        manuscript = m.Manuscript.objects.latest('updated_at')
        group_manuscript_verifier = m.Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id)) 
        group_manuscript_verifier.user_set.add(verifier_in) 
        
        ##### TEST ACCESS MANUSCRIPT : NEW #####

        #TODO: When should I be testing g_dict? Not every phase :P
        self.assertEqual(manuscript._status, m.Manuscript.Status.NEW)

        self.check_access(anon_selenium, assert_dict=g_dict_no_access_anon)
        self.check_access(anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)

        #TODO: I need to figure out how I'm handling pages that are only available at certain phases
        #      ...
        #      I could create separate dictionaries for each phase at the bottom
        #      I could interweave the changes in the tests
        #      ...
        #      I think the former is better, capturing all the logic in one place?

        # ALSO

        #TODO SATURDAY
        # - Implement a different way to do non-get requests in selenium
        #   - https://stackoverflow.com/questions/5660956/is-there-any-way-to-start-with-a-post-request-using-selenium
        #     - It looks like you can eval javascript to do other request types...


        self.check_access(c_selenium, assert_dict=g_dict_admin_access)
        #time.sleep(500000)
        self.check_access(c_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)
        # At this point both verifiers should be the same
        self.check_access(v_in_selenium, assert_dict=g_dict_normal_access)
        self.check_access(v_in_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        self.check_access(v_out_selenium, assert_dict=g_dict_normal_access)
        self.check_access(v_out_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)

        ##### ASSIGN AUTHOR (SELF) TO MANUSCRIPT #####

        c_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/addauthor/")
        #We don't fill out any fields for this form beacuse it is auto-populated with manuscript info
        manuscript_add_author_submit = c_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        manuscript_add_author_submit.send_keys(Keys.RETURN)
        c_selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING #####

        manuscript_create_submit_continue = c_selenium.find_element_by_id('createSubmissionButton')
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        # TODO create submission etc
        #     - When are we testing access for the two verifiers?
        #       - Ideal is when there is a sub/manuscript status change? But is that too messy?
        #         - Maybe we should create a separate function that calls all our endpoints (pass browser (e.g. user), manuscript or submission)

        #time.sleep(500000)

    ## Old check_access using selenium_requests which didn't work great
    ## Not a test, but a helper
    ## assert_dict example: {'edit': 200, 'update': 500}
    # def check_access(self, browser, manuscript=None, submission=None, assert_dict=None):
    #     if assert_dict == None:
    #         raise Exception('assert_dict must be set for check_access')            
    #     if manuscript != None and submission != None:
    #         raise Exception('both manuscript and submission cannot be set at the same time for check_access')

    #     if manuscript != None:
    #         url_pre = '/manuscript/' + str(manuscript.id) + '/'
    #     elif submission != None:
    #         url_pre = '/submission/' + str(submission.id) + '/'
    #     else:
    #         url_pre = '/'

    #     for url_post, status_dict in assert_dict.items():
    #         full_url = self.live_server_url + url_pre + url_post
    #         for method, status_code in status_dict.items():
    #             print(full_url)
    #             print("...")
    #             try:
    #                 response = browser.request(method, full_url)
    #             except Exception as e:
    #                 print("Error in check_access request. URL: {}, Method: {}".format(full_url, method))
    #                 raise e
    #             if status_code == 302:
    #                 #If we expect a 302, we look for it in the history
    #                 if response.history:
    #                     self.assertEqual(response.history[0].status_code, status_code, msg="Checking 302 status in history. URL: {}, Method: {}".format(full_url, method))
    #                     self.assertEqual(response.status_code, 200, msg="Checking 200 status on current page. URL: {}, Method: {}".format(full_url, method))
    #                 else: 
    #                     print(full_url)
    #                     #time.sleep(500000)
    #                     self.fail("Checking 302 status, there was no history. This means that there was no 302. Status: {}, URL: {}, Method: {}".format(response.status_code, full_url, method))
    #             else:
    #                 # print(response.__dict__)
    #                 # print(response.history[0].status_code)
    #                 self.assertEqual(response.status_code, status_code, msg=method + ": " + full_url)

    # Not a test, but a helper
    # assert_dict example: {'edit': 200, 'update': 500}
    def check_access(self, browser, manuscript=None, submission=None, assert_dict=None):
        if assert_dict == None:
            raise Exception('assert_dict must be set for check_access')            
        if manuscript != None and submission != None:
            raise Exception('both manuscript and submission cannot be set at the same time for check_access')

        if manuscript != None:
            url_pre = '/manuscript/' + str(manuscript.id) + '/'
        elif submission != None:
            url_pre = '/submission/' + str(submission.id) + '/'
        else:
            url_pre = '/'

        del browser.requests #clear previous built up requests

        for url_post, status_dict in assert_dict.items():
            full_url = self.live_server_url + url_pre + url_post
            for method, status_code in status_dict.items():
                print(full_url)
                print("...")
                
                if method == 'GET':
                    browser.get(full_url)
                    
                    for request in browser.requests:
                        if(request.response):
                            print("{} - {}".format(request.url, request.response.status_code))
                    for request in browser.requests:
                        if request.url == full_url and request.response:
                            self.assertEqual(request.response.status_code, status_code, msg=full_url)
                            del browser.requests
                else:
                    raise Exception("NO OTHER METHODS SUPPORTED")
                # try:
                #     response = browser.request(method, full_url)
                # except Exception as e:
                #     print("Error in check_access request. URL: {}, Method: {}".format(full_url, method))
                #     raise e
                # if status_code == 302:
                #     #If we expect a 302, we look for it in the history
                #     if response.history:
                #         self.assertEqual(response.history[0].status_code, status_code, msg="Checking 302 status in history. URL: {}, Method: {}".format(full_url, method))
                #         self.assertEqual(response.status_code, 200, msg="Checking 200 status on current page. URL: {}, Method: {}".format(full_url, method))
                #     else: 
                #         print(full_url)
                #         #time.sleep(500000)
                #         self.fail("Checking 302 status, there was no history. This means that there was no 302. Status: {}, URL: {}, Method: {}".format(response.status_code, full_url, method))
                # else:
                #     # print(response.__dict__)
                #     # print(response.history[0].status_code)
                #     self.assertEqual(response.status_code, status_code, msg=method + ": " + full_url)


#TODO: How am I testing when a request gets a 200 but is sent to login?
#      - I think a special "access code" constant that indicates to test for 200 but login
#          - Does this mean we should test 200 without login for the other 200s?
#      - We can test a 302 by looking for it in the history


###############################
##### ACCESS DICTIONARIES #####
###############################

# These dictionaries are used with check_access to test endpoints throughout the workflow.
# We use "inheritance" to define some of the dictionaries as slight alterations of other ones.
# These dictionaries don't check everything, as some endpoints progress code when called.

#TODO: What are we doing about get/post/put/delete
#      - Nested dictionary

##### General Access #####

# This is the parent of all general access dictionaries
# We don't have a g_dict_no_access because that case does not exist. If you don't have general access you aren't logged in and should get 302'ed

g_dict_admin_access = { #'': {'GET': 200}, #blows up due to oauth code
    #'manuscript_table/': {'GET': 200}, 
    'manuscript/create/': {'GET': 200}, #UNDO
    #'account_user_details/': {'GET': 200}, #blow up due to oauth code
    'notifications/': {'GET': 200}, 
    'site_actions/': {'GET': 200}, 
    'site_actions/inviteeditor/': {'GET': 200}, 
    'site_actions/invitecurator/': {'GET': 200}, 
    'site_actions/inviteverifier/': {'GET': 200}, 
    'user_table/': {'GET': 200}
}

#Takes all the keys and sets their values to `{'GET': 302}`
g_dict_no_access_anon = dict.fromkeys(g_dict_admin_access, {'GET': 302})

g_dict_normal_access = g_dict_admin_access.copy()
g_dict_normal_access.update({
    # 'manuscript_table/': {'GET': 200},
    # 'notifications/': {'GET': 200}, 
    # 'user_table/': {'GET': 200}
    'manuscript/create/': {'GET': 404}, 
    'site_actions/': {'GET': 404}, 
    'site_actions/inviteeditor/': {'GET': 404}, 
    'site_actions/invitecurator/': {'GET': 404}, 
    'site_actions/inviteverifier/': {'GET': 404}, 
})

g_dict_normal_editor_access = g_dict_normal_access.copy()
g_dict_normal_editor_access.update({
    'manuscript/create/': {'GET': 200}, 
})

##### Manuscript Access #####

m_dict_no_access = {
    '': {'GET': 404},
    #'submission_table': {'GET': 404}, #TODO: No access verifier gets a 200. Should this instead error? I need to check the content returned.
    'edit/': {'GET': 404}, #TODO: No access anon gets 500?
    'update/': {'GET': 404},
    'uploadfiles/': {'GET': 404},
    'uploader/': {'GET': 404},
    'fileslist/': {'GET': 404},
    'view/': {'GET': 404},
    'viewfiles/': {'GET': 404},
    'inviteassignauthor/': {'GET': 404},
    'addauthor/': {'GET': 404},
    #'unassignauthor/': {'GET': 404}, #this needs a user id
    'assigneditor/': {'GET': 404},
    #'unassigneditor/': {'GET': 404}, #this needs a user id
    'assigncurator/': {'GET': 404},
    #'unassigncurator/': {'GET': 404}, #this needs a user id
    'assignverifier/': {'GET': 404},
    #'unassignverifier/': {'GET': 404}, #this needs a user id
    'deletefile/': {'GET': 404},
    'downloadfile/': {'GET': 404},
    'downloadall/': {'GET': 404},
    'reportdownload/': {'GET': 404},
    #'deletenotebook/': {'GET': 404}, #TODO: This errors asking for a cookie (WT). Should this work on a get? I may have done that out of laziness.
    #'file_table/': {'GET': 404},  #TODO: No access verifier gets a 200. Should this instead error? I need to check the content returned.
    'confirm/': {'GET': 404},
    'pullcitation/': {'GET': 404}
    }

m_dict_no_access_anon = dict.fromkeys(m_dict_no_access, {'GET': 302})

#TODO: This is probably wrong, depending on the phase. If not, for verifiers a similar approach will definitely not work.
#      We need a way to
m_dict_admin_access = dict.fromkeys(m_dict_no_access, {'GET': 200})

##### Submission Access #####

s_dict_no_access = {
    'info/': {'GET': 404},
    'uploadfiles/': {'GET': 404},
    'confirmfiles/': {'GET': 404},
    'uploader/': {'GET': 404},
    'fileslist/': {'GET': 404},
    'view/': {'GET': 404},
    'viewfiles/': {'GET': 404},
    'deletefile/': {'GET': 404},
    'deleteallfiles/': {'GET': 404},
    'downloadfile/': {'GET': 404},
    'downloadall/': {'GET': 404},
    'sendreport/': {'GET': 404},
    'finish/': {'GET': 404},
    'notebook/': {'GET': 404},
    'notebooklogin/': {'GET': 404},
    'newfilecheck/': {'GET': 404},
    'wtstream/': {'GET': 404},
    'wtdownloadall/': {'GET': 404},
    'file_table/': {'GET': 404}
}



















