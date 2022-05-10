import time, unittest
from django.test import LiveServerTestCase, override_settings
from seleniumwire import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

from corere.main.tests.selenium_access_utils import *
from corere.main import models as m
from corere.main import constants as c
from corere.apps.wholetale import models as wtm

# Part of this testing is based upon finding elements. If they aren't available, the test errors out.
# NOTE: Use the --keepdb flag between runs. The actions in the tests (creating accounts etc) get rolled back from the db each run
# TODO: Future tests streamline login: https://stackoverflow.com/questions/22494583/login-with-code-when-using-liveservertestcase-with-django
# TODO: Maybe use sys.argv to detect verbose and run print statements: https://www.knowledgehut.com/blog/programming/sys-argv-python-examples
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
    @unittest.skip("This test is not required, all functionality is covered by test_3_user. Can be used if that fails to help isolate issues.")
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

        ##### ADD SUBMISSION NOTES (none currently) #####

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

        ##### ADD SUBMISSION NOTES (none currently) #####

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

    # This tests most of the flow, with actions done by an admin-curator and a non-admin verifier (with access).
    # This includes inviting the users to CORE2 via the UI
    # Tests are also done with a verifier with no access to ensure privacy 
    # This uses selenium-wire to get responses, which is technically bad form for selenium but is helpful for us
    # Not tested: Edition, Dataverse, Files, Whole Tale
    # ...
    # This code does deep access tests as the manuscript/submission status changes
    # ...
    # This code only does one submission
    # TODO: Hardcode no edition setting
    # TODO: This test downloads zips, do we need to get rid of them?
    # TODO: This doesn't test access to previous submissions yet
    #@unittest.skip("testing others now")
    def test_3_user_workflow_with_access_checks(self):
        admin_selenium = self.selenium
        anon_selenium = webdriver.Chrome(options=self.options)
        v_out_selenium= webdriver.Chrome(options=self.options)
        v_in_selenium = webdriver.Chrome(options=self.options)
        c_selenium = webdriver.Chrome(options=self.options)

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

        v_out_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", v_out_selenium.title)
        current_url = v_out_selenium.current_url
        username = v_out_selenium.find_element_by_id('id_username')
        password = v_out_selenium.find_element_by_id('id_password')
        username.send_keys('verifier_out')
        password.send_keys('password')
        admin_login_submit = v_out_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("ion | Django site admin", v_out_selenium.title)

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

        ##### ADD VERIFIER AND CURATOR(ADMIN) TO MANUSCRIPT #####

        # NOTE: For some reason our verifiers don't show up as options for the assignverifier page
        #       This may be because of the javascript/ajax(?)
        #       So instead we'll assign via the backend, but this is a TODO for later
        #       - When we do this, we may want to move where it happens in the flow

        #c_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/assignverifier/") 

        manuscript = m.Manuscript.objects.latest('updated_at')
        group_manuscript_verifier = m.Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id)) 
        group_manuscript_verifier.user_set.add(verifier_in) 
        group_manuscript_curator = m.Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id)) 
        group_manuscript_curator.user_set.add(curator_admin) 
        
        ##### TEST GENERAL CORE2 ACCESS #####

        check_access(self, anon_selenium, assert_dict=g_dict_no_access_anon)
        check_access(self, v_out_selenium, assert_dict=g_dict_normal_access)
        check_access(self, v_in_selenium, assert_dict=g_dict_normal_access)
        check_access(self, c_selenium, assert_dict=g_dict_admin_access)

        ##### TEST ACCESS MANUSCRIPT : NEW #####

        self.assertEqual(manuscript._status, m.Manuscript.Status.NEW)

        check_access(self, anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)
        check_access(self, v_out_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, v_in_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, c_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)

        ##### ASSIGN AUTHOR (SELF) TO MANUSCRIPT #####

        c_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/addauthor/")
        #We don't fill out any fields for this form beacuse it is auto-populated with manuscript info
        manuscript_add_author_submit = c_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        manuscript_add_author_submit.send_keys(Keys.RETURN)
        c_selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING #####

        manuscript_create_submit_continue = c_selenium.find_element_by_id('createSubmissionButton')
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS MANUSCRIPT : AWAITING_INITIAL #####

        manuscript = m.Manuscript.objects.latest('updated_at')
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_INITIAL)

        check_access(self, anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)
        check_access(self, v_out_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, v_in_selenium, manuscript=manuscript, assert_dict=m_dict_verifier_access__out_of_phase)
        check_access(self, c_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)

        ###############################
        ##### CREATE SUBMISSION 1 #####
        ###############################

        Select(c_selenium.find_element_by_id('id_subject')).select_by_visible_text("Agricultural Sciences")
        manuscript_update_submit_continue = c_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS SUBMISSION : NEW #####

        submission = m.Submission.objects.latest('updated_at')
        self.assertEqual(submission._status, m.Submission.Status.NEW)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_out_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_in_selenium, submission=submission, assert_dict=s_dict_verifier_access__out_of_phase)
        check_access(self, c_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### ADD SUBMISSION NOTES (none currently) #####

        c_selenium.get(self.live_server_url+"/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
        submission_info_submit_continue = c_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[5]')
        submission_info_submit_continue.send_keys(Keys.RETURN)
        c_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_CURATION #####

        time.sleep(.5) #wait for status to update in db
        manuscript = m.Manuscript.objects.latest('updated_at')
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest('updated_at')
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_CURATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_out_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_in_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING REVIEW CURATION #####

        manuscript_review_submission = c_selenium.find_element_by_id('reviewSubmissionButtonMain')
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### CURATOR REVIEW - ISSUES #####
        
        Select(c_selenium.find_element_by_id('id_curation_formset-0-_status')).select_by_visible_text("No Issues") 
        c_selenium.find_element_by_id('id_curation_formset-0-report').send_keys('report')
        c_selenium.find_element_by_id('id_curation_formset-0-needs_verification').click()
        Select(c_selenium.find_element_by_id('id_submission_editor_date_formset-0-editor_submit_date_month')).select_by_visible_text("January") 
        Select(c_selenium.find_element_by_id('id_submission_editor_date_formset-0-editor_submit_date_day')).select_by_visible_text("1") 
        Select(c_selenium.find_element_by_id('id_submission_editor_date_formset-0-editor_submit_date_year')).select_by_visible_text("2020") 
        submission_info_submit_continue_curation = c_selenium.find_element_by_id('submit_progress_curation_button')
        submission_info_submit_continue_curation.send_keys(Keys.RETURN)
        c_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_VERIFICATION #####

        time.sleep(.5) #wait for status to update in db
        manuscript = m.Manuscript.objects.latest('updated_at')
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest('updated_at')
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_VERIFICATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_out_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_in_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING REVIEW VERIFICATION #####

        manuscript = m.Manuscript.objects.latest('updated_at')
        v_in_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = v_in_selenium.find_element_by_id('reviewSubmissionButtonMain')
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### VERIFIER REVIEW - ISSUES #####

        Select(v_in_selenium.find_element_by_id('id_verification_formset-0-_status')).select_by_visible_text("Success") 
        v_in_selenium.find_element_by_id('id_verification_formset-0-code_executability').send_keys('report')
        v_in_selenium.find_element_by_id('id_verification_formset-0-report').send_keys('report')        
        submission_info_submit_continue_verification = v_in_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[12]')
        submission_info_submit_continue_verification.send_keys(Keys.RETURN)
        v_in_selenium.switch_to.alert.accept()           

        ##### TEST ACCESS SUBMISSION : COMPLETED #####

        time.sleep(.5) #wait for status to update in db
        manuscript = m.Manuscript.objects.latest('updated_at')
        self.assertEqual(manuscript._status, m.Manuscript.Status.COMPLETED)
        submission = m.Submission.objects.latest('updated_at')
        self.assertEqual(submission._status, m.Submission.Status.REVIEWED_AWAITING_REPORT)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_out_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_in_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_selenium, submission=submission, assert_dict=s_dict_admin_access__completed)

        ##### NOTE: Test ends here because we don't test the dataverse steps currently #####



        # ##### MANUSCRIPT GENERATE REPORT #####

        # c_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id)) #Re-get the page to get the updated buttons
        # manuscript_send_report_button = c_selenium.find_element_by_id('sendReportButton')
        # manuscript_send_report_button.send_keys(Keys.RETURN)

        # ##### TEST ACCESS SUBMISSION : REVIEWED_AWAITING_REPORT #####

        # time.sleep(.5) #wait for status to update in db
        # manuscript = m.Manuscript.objects.latest('updated_at')
        # self.assertEqual(manuscript._status, m.Manuscript.Status.COMPLETED)
        # submission = m.Submission.objects.latest('updated_at')
        # self.assertEqual(submission._status, m.Submission.Status.REVIEWED_REPORT_AWAITING_APPROVAL)

        # check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        # check_access(self, v_out_selenium, submission=submission, assert_dict=s_dict_no_access)
        # check_access(self, v_in_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        # check_access(self, c_selenium, submission=submission, assert_dict=s_dict_admin_access)




