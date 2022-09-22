import time, unittest, os
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from seleniumwire import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from webdriver_manager.chrome import ChromeDriverManager

from corere.main.tests.selenium_access_utils import *
from corere.main import models as m
from corere.main import constants as c
from corere.apps.wholetale import models as wtm

# NOTE: If testing gives you an "OSError: [Errno 24] Too many open files:" error, try upping your files with ulimit -n
# NOTE: Debug is enabled currently for the tests to get to 500 error full messages, but it causes noisy print statements in outputs. Maybe just disable
#       ... could also try: https://stackoverflow.com/questions/72116043/how-to-silence-print-statements-in-for-python-selenium

# Part of this testing is based upon finding elements. If they aren't available, the test errors out.
# NOTE: Use the --keepdb flag between runs. The actions in the tests (creating accounts etc) get rolled back from the db each run
# TODO: Future tests streamline login: https://stackoverflow.com/questions/22494583/login-with-code-when-using-liveservertestcase-with-django
# TODO: Maybe use sys.argv to detect verbose and run print statements: https://www.knowledgehut.com/blog/programming/sys-argv-python-examples
class LoggingInTestCase(StaticLiveServerTestCase):

    def setUp(self):
        # os.environ['WDM_LOG_LEVEL'] = '0' #Should Disable webdriver_manager print statements... but doesn't.
        self.options = Options()
        self.options.headless = True
        # This was enabled to fix CORS post errors after tests ran fine for a while. It may have been due to a refactor but it also seems likely that it was due to a chrome update
        self.options.add_argument("--disable-web-security")
        # self.options.add_argument("--user-data-dir=/tmp/chrome_dev_test")
        # self.selenium = webdriver.Chrome(options=self.options)

        #We create a dictionary of selenium instances to be able to clean them up when we close the test prematurely
        self.selenium_instances = {}
        self.selenium_instances['admin'] = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        self.selenium = self.selenium_instances['admin']

        m.User.objects.create_superuser("admin", "admin@test.test", "password")

        # We need add the other option for compute env with the current implementation
        wtm.ImageChoice.objects.get_or_create(wt_id="Other", name="Other", show_last=True)

        super(LoggingInTestCase, self).setUp()

    def tearDown(self):
        for s_instance in self.selenium_instances.values():
            s_instance.quit()
        super(LoggingInTestCase, self).tearDown()

    # This tests most of the flow with all actions done by an admin.
    # Not tested: Edition, Dataverse, Files, Whole Tale
    @unittest.skip("This test is not required, almost all functionality is covered by test_3_user (a few admin actions not covered). Can be used if that fails to help isolate issues.")
    @override_settings(SKIP_EDITION=True)
    @override_settings(DEBUG=True)
    def test_admin_only_mostly_full_workflow(self):
        selenium = self.selenium

        ##### ADMIN LOGIN #####

        selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", selenium.title)
        current_url = selenium.current_url
        username = selenium.find_element_by_id("id_username")
        password = selenium.find_element_by_id("id_password")
        username.send_keys("admin")
        password.send_keys("password")
        admin_login_submit = selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", selenium.title)

        # TODO: Investigate a way for the non-oauth user to skip being forced to select an oauth on the index page.
        #      We can't do any tests on it currently

        #############################
        ##### CREATE MANUSCRIPT #####
        #############################

        selenium.get(self.live_server_url + "/manuscript/create/")

        # NOTE: Not all fields for form are in this list. Exemptions, most env_info
        selenium.find_element_by_id("id_pub_name").send_keys("pub_name")
        selenium.find_element_by_id("id_pub_id").send_keys("pub_id")
        selenium.find_element_by_id("id_description").send_keys("description")
        # selenium.find_element_by_id('id_subject').send_keys('test') #DROPDOWN FIX
        # selenium.find_element_by_id('id_additional_info').send_keys('additional_info')
        selenium.find_element_by_id("id_contact_first_name").send_keys("contact_first_name")
        selenium.find_element_by_id("id_contact_last_name").send_keys("contact_last_name")
        selenium.find_element_by_id("id_contact_email").send_keys("contact_email@test.test")
        Select(selenium.find_element_by_id("id_compute_env")).select_by_visible_text("Other")  # select unneeded currently because its the only option
        selenium.find_element_by_id("id_operating_system").send_keys("operating_system")
        selenium.find_element_by_id("id_packages_info").send_keys("packages_info")
        selenium.find_element_by_id("id_software_info").send_keys("software_info")
        # operating system, required packages, statistical software
        # NOTE: The selenium test doesn't seem to do JS the same, so our janky formsets don't have a row displayed unless we click
        manuscript_create_add_author_link_button = selenium.find_element_by_xpath('//*[@id="author_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_author_link_button.send_keys(Keys.RETURN)
        selenium.find_element_by_id("id_author_formset-0-first_name").send_keys("author_0_first_name")
        selenium.find_element_by_id("id_author_formset-0-last_name").send_keys("author_0_last_name")
        # selenium.find_element_by_id('id_author_formset-0-identifier').send_keys('author_0_identifier')
        manuscript_create_add_data_source_link_button = selenium.find_element_by_xpath('//*[@id="data_source_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_data_source_link_button.send_keys(Keys.RETURN)
        selenium.find_element_by_id("id_data_source_formset-0-text").send_keys("data_source_0_text")
        manuscript_create_add_keyword_link_button = selenium.find_element_by_xpath('//*[@id="keyword_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_keyword_link_button.send_keys(Keys.RETURN)
        selenium.find_element_by_id("id_keyword_formset-0-text").send_keys("keyword_0_text")

        manuscript_create_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ##### UPLOAD MANUSCRIPT FILES (skipping for now) #####

        ##### ASSIGN AUTHOR TO MANUSCRIPT #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/addauthor/")
        # We don't fill out any fields for this form beacuse it is auto-populated with manuscript info
        manuscript_add_author_submit = selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        manuscript_add_author_submit.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING #####

        manuscript_create_submit_continue = selenium.find_element_by_id("createSubmissionButton")
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ###############################
        ##### CREATE SUBMISSION 1 #####
        ###############################

        Select(selenium.find_element_by_id("id_subject")).select_by_visible_text("Agricultural Sciences")
        manuscript_update_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### UPLOAD SUBMISSION FILES (skipping for now) #####

        ##### ADD SUBMISSION NOTES (none currently) #####

        selenium.get(self.live_server_url + "/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
        submission_info_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[5]')
        submission_info_submit_continue.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING REVIEW CURATION #####

        manuscript_review_submission = selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### CURATOR REVIEW - ISSUES #####
        # NOTE: Editor review is disabled for our install currently. When its re-enabled this will break. We should actually be testing both

        Select(selenium.find_element_by_id("id_curation_formset-0-_status")).select_by_visible_text("Minor Issues")
        selenium.find_element_by_id("id_curation_formset-0-report").send_keys("report")
        selenium.find_element_by_id("id_curation_formset-0-needs_verification").click()
        Select(selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_month")).select_by_visible_text("January")
        Select(selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_day")).select_by_visible_text("1")
        Select(selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_year")).select_by_visible_text("2020")
        submission_info_submit_continue_curation = selenium.find_element_by_id("submit_progress_curation_button")
        submission_info_submit_continue_curation.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING REVIEW VERIFICATION #####

        manuscript_review_submission = selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### VERIFIER REVIEW - ISSUES #####

        Select(selenium.find_element_by_id("id_verification_formset-0-_status")).select_by_visible_text("Minor Issues")
        selenium.find_element_by_id("id_verification_formset-0-code_executability").send_keys("report")
        selenium.find_element_by_id("id_verification_formset-0-report").send_keys("report")
        submission_info_submit_continue_verification = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[14]')
        submission_info_submit_continue_verification.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING / GENERATE REPORT / RETURN SUBMISSION #####

        manuscript_send_report_button = selenium.find_element_by_id("sendReportButton")
        manuscript_send_report_button.send_keys(Keys.RETURN)
        time.sleep(0.5)  # Needed to wait for this button to appear on the same page
        manuscript_return_submission_button = selenium.find_element_by_id("returnSubmissionButton")
        manuscript_return_submission_button.send_keys(Keys.RETURN)
        time.sleep(0.5)  # Needed to wait for this button to appear on the same page
        manuscript_create_submit_continue = selenium.find_element_by_id("createSubmissionButton")
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ###############################
        ##### CREATE SUBMISSION 2 #####
        ###############################

        Select(selenium.find_element_by_id("id_subject")).select_by_visible_text("Agricultural Sciences")
        manuscript_update_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### UPLOAD SUBMISSION FILES (skipping for now) #####

        ##### ADD SUBMISSION NOTES (none currently) #####

        selenium.get(self.live_server_url + "/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
        submission_info_submit_continue = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[5]')
        submission_info_submit_continue.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING REVIEW CURATION #####

        manuscript_review_submission = selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### CURATOR REVIEW - NO ISSUES #####
        # NOTE: Editor review is disabled for our install currently. When its re-enabled this will break. We should actually be testing both

        Select(selenium.find_element_by_id("id_curation_formset-0-_status")).select_by_visible_text("No Issues")
        selenium.find_element_by_id("id_curation_formset-0-report").send_keys("report")
        selenium.find_element_by_id("id_curation_formset-0-needs_verification").click()
        Select(selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_month")).select_by_visible_text("January")
        Select(selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_day")).select_by_visible_text("2")
        Select(selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_year")).select_by_visible_text("2020")
        submission_info_submit_continue_curation = selenium.find_element_by_id("submit_progress_curation_button")
        submission_info_submit_continue_curation.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING REVIEW VERIFICATION #####

        manuscript_review_submission = selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### VERIFIER REVIEW - NO ISSUES #####

        Select(selenium.find_element_by_id("id_verification_formset-0-_status")).select_by_visible_text("Success")
        selenium.find_element_by_id("id_verification_formset-0-code_executability").send_keys("report")
        selenium.find_element_by_id("id_verification_formset-0-report").send_keys("report")
        submission_info_submit_continue_verification = selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[14]')
        submission_info_submit_continue_verification.send_keys(Keys.RETURN)
        selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING / CONFIRM DATAVERSE NEXT STEP #####

        dataverse_upload_manuscript_button = selenium.find_element_by_id("dataverseUploadManuscriptButtonMain")
        dataverse_upload_manuscript_button.send_keys(Keys.RETURN)

    # This tests most of the flow, with actions done by an admin-curator and a non-admin verifier (with access).
    # This includes inviting the users to CORE2 via the UI
    # Tests are also done with a verifier with no access to ensure privacy
    # This uses selenium-wire to get responses, which is technically bad form for selenium but is helpful for us
    # Not tested: Edition, Dataverse, Files, Whole Tale
    # ...
    # This code does deep access tests as the manuscript/submission status changes
    # ...
    # TODO: Test across multiple submissions
    # TODO: This test downloads zips, do we need to get rid of them?
    # TODO: This doesn't test access to previous submissions yet
    @unittest.skip("Disabled for test writing")
    @override_settings(SKIP_EDITION=True)
    @override_settings(DEBUG=True)
    def test_3_user_workflow_with_access_checks(self):
        ## If you use these settings, you have to skip our POST test currently because they seem to be contigent on headless...
        # self.options_not_headless = Options()
        # self.options_not_headless.add_argument("--disable-web-security")
        # self.options_not_headless.add_argument("--user-data-dir=/tmp/chrome_dev_test")

        #Yes/No refers to their access to the manuscript
        admin_selenium = self.selenium
        anon_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        v_no_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        v_yes_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        c_admin_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options) #_not_headless)

        #Add our new instances to the dict for cleanup when closed via interrupt
        self.selenium_instances['anon'] = anon_selenium
        self.selenium_instances['v_no'] = v_no_selenium 
        self.selenium_instances['v_yes'] = v_yes_selenium
        self.selenium_instances['c_admin'] = c_admin_selenium 

        ##### ADMIN LOGIN #####

        admin_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", admin_selenium.title)
        current_url = admin_selenium.current_url
        username = admin_selenium.find_element_by_id("id_username")
        password = admin_selenium.find_element_by_id("id_password")
        username.send_keys("admin")
        password.send_keys("password")
        admin_login_submit = admin_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", admin_selenium.title)

        ############################
        ##### ACCOUNT CREATION #####
        ############################

        ##### ADMIN CREATE CURATOR_ADMIN #####

        curator_admin = m.User.objects.create_superuser("curatoradmin", "curatoradmin@test.test", "password")
        role_c = m.Group.objects.get(name=c.GROUP_ROLE_CURATOR)
        role_a = m.Group.objects.get(name=c.GROUP_ROLE_AUTHOR)
        role_e = m.Group.objects.get(name=c.GROUP_ROLE_EDITOR)
        role_c.user_set.add(curator_admin)
        role_a.user_set.add(curator_admin)
        role_e.user_set.add(curator_admin)

        ##### CURATOR_ADMIN LOGIN #####

        c_admin_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", c_admin_selenium.title)
        current_url = c_admin_selenium.current_url
        username = c_admin_selenium.find_element_by_id("id_username")
        password = c_admin_selenium.find_element_by_id("id_password")
        username.send_keys("curatoradmin")
        password.send_keys("password")
        admin_login_submit = c_admin_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", c_admin_selenium.title)

        ##### CURATOR_ADMIN VERIFIER_IN CREATION #####

        # This verifier will have verifier to the tested manuscript
        c_admin_selenium.get(self.live_server_url + "/site_actions/inviteverifier/")
        c_admin_selenium.find_element_by_id("id_first_name").send_keys("verifier_in")
        c_admin_selenium.find_element_by_id("id_last_name").send_keys("last_name")
        c_admin_selenium.find_element_by_id("id_email").send_keys("verifier_in@test.test")

        verifier_in_create_button = c_admin_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        verifier_in_create_button.send_keys(Keys.RETURN)

        verifier_in = m.User.objects.get(email="verifier_in@test.test")
        verifier_in.set_password("password")
        verifier_in.username = "verifier_in"
        verifier_in.is_staff = True  # allows admin login without oauth
        verifier_in.save()

        ##### VERIFIER IN LOGIN #####

        v_yes_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", v_yes_selenium.title)
        current_url = v_yes_selenium.current_url
        username = v_yes_selenium.find_element_by_id("id_username")
        password = v_yes_selenium.find_element_by_id("id_password")
        username.send_keys("verifier_in")
        password.send_keys("password")
        admin_login_submit = v_yes_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", v_yes_selenium.title)

        ##### CURATOR_ADMIN VERIFIER_OUT CREATION #####

        # This verifier will have no access to the tested manuscript
        c_admin_selenium.get(self.live_server_url + "/site_actions/inviteverifier/")
        c_admin_selenium.find_element_by_id("id_first_name").send_keys("verifier_out")
        c_admin_selenium.find_element_by_id("id_last_name").send_keys("last_name")
        c_admin_selenium.find_element_by_id("id_email").send_keys("verifier_out@test.test")

        verifier_out_create_button = c_admin_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        verifier_out_create_button.send_keys(Keys.RETURN)

        verifier_out = m.User.objects.get(email="verifier_out@test.test")
        verifier_out.set_password("password")
        verifier_out.username = "verifier_out"
        verifier_out.is_staff = True  # allows admin login without oauth
        verifier_out.save()

        ##### VERIFIER_OUT LOGIN #####

        v_no_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", v_no_selenium.title)
        current_url = v_no_selenium.current_url
        username = v_no_selenium.find_element_by_id("id_username")
        password = v_no_selenium.find_element_by_id("id_password")
        username.send_keys("verifier_out")
        password.send_keys("password")
        admin_login_submit = v_no_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", v_no_selenium.title)

        #############################################
        ##### CURATOR_ADMIN MANUSCRIPT CREATION #####
        #############################################

        c_admin_selenium.get(self.live_server_url + "/manuscript/create/")

        c_admin_selenium.find_element_by_id("id_pub_name").send_keys("pub_name")
        c_admin_selenium.find_element_by_id("id_pub_id").send_keys("pub_id")
        c_admin_selenium.find_element_by_id("id_description").send_keys("description")
        # c_admin_selenium.find_element_by_id('id_additional_info').send_keys('additional_info')
        c_admin_selenium.find_element_by_id("id_contact_first_name").send_keys("curatoradmin")
        c_admin_selenium.find_element_by_id("id_contact_last_name").send_keys("contact_last_name")
        c_admin_selenium.find_element_by_id("id_contact_email").send_keys("curatoradmin@test.test")
        Select(c_admin_selenium.find_element_by_id("id_compute_env")).select_by_visible_text(
            "Other"
        )  # select unneeded currently because its the only option
        c_admin_selenium.find_element_by_id("id_operating_system").send_keys("operating_system")
        c_admin_selenium.find_element_by_id("id_packages_info").send_keys("packages_info")
        c_admin_selenium.find_element_by_id("id_software_info").send_keys("software_info")
        # NOTE: The selenium test doesn't seem to do JS the same, so our janky formsets don't have a row displayed unless we click
        manuscript_create_add_author_link_button = c_admin_selenium.find_element_by_xpath('//*[@id="author_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_author_link_button.send_keys(Keys.RETURN)
        c_admin_selenium.find_element_by_id("id_author_formset-0-first_name").send_keys("author_0_first_name")
        c_admin_selenium.find_element_by_id("id_author_formset-0-last_name").send_keys("author_0_last_name")
        manuscript_create_add_data_source_link_button = c_admin_selenium.find_element_by_xpath('//*[@id="data_source_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_data_source_link_button.send_keys(Keys.RETURN)
        c_admin_selenium.find_element_by_id("id_data_source_formset-0-text").send_keys("data_source_0_text")
        manuscript_create_add_keyword_link_button = c_admin_selenium.find_element_by_xpath('//*[@id="keyword_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_keyword_link_button.send_keys(Keys.RETURN)
        c_admin_selenium.find_element_by_id("id_keyword_formset-0-text").send_keys("keyword_0_text")

        manuscript_create_submit_continue = c_admin_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ##### UPLOAD MANUSCRIPT FILES (skipping for now) #####

        ##### ADD VERIFIER AND CURATOR(ADMIN) TO MANUSCRIPT #####

        # NOTE: For some reason our verifiers don't show up as options for the assignverifier page
        #       This may be because of the javascript/ajax(?)
        #       So instead we'll assign via the backend, but this is a TODO for later
        #       - When we do this, we may want to move where it happens in the flow

        # c_admin_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/assignverifier/")

        manuscript = m.Manuscript.objects.latest("updated_at")
        group_manuscript_verifier = m.Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id))
        group_manuscript_verifier.user_set.add(verifier_in)
        group_manuscript_curator = m.Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id))
        group_manuscript_curator.user_set.add(curator_admin)

        ##### TEST GENERAL CORE2 ACCESS #####

        check_access(self, anon_selenium, assert_dict=g_dict_no_access_anon)
        check_access(self, v_no_selenium, assert_dict=g_dict_normal_access)
        check_access(self, v_yes_selenium, assert_dict=g_dict_normal_access)
        check_access(self, c_admin_selenium, assert_dict=g_dict_admin_access)

        ##### TEST ACCESS MANUSCRIPT : NEW #####

        self.assertEqual(manuscript._status, m.Manuscript.Status.NEW)

        check_access(self, anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)
        check_access(self, v_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_verifier_access)
        check_access(self, v_yes_selenium, manuscript=manuscript, assert_dict=m_dict_no_verifier_access)
        # time.sleep(999999)
        check_access(self, c_admin_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)

        ##### ASSIGN AUTHOR (SELF) TO MANUSCRIPT #####

        c_admin_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/addauthor/")
        # We don't fill out any fields for this form beacuse it is auto-populated with manuscript info
        manuscript_add_author_submit = c_admin_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        manuscript_add_author_submit.send_keys(Keys.RETURN)
        c_admin_selenium.switch_to.alert.accept()

        ##############################
        #####    SUBMISSION 1    #####
        ##############################

        ##### MANUSCRIPT LANDING #####

        manuscript_create_submit_continue = c_admin_selenium.find_element_by_id("createSubmissionButton")
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS MANUSCRIPT : AWAITING_INITIAL #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_INITIAL)

        check_access(self, anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)
        check_access(self, v_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_verifier_access)
        check_access(self, v_yes_selenium, manuscript=manuscript, assert_dict=m_dict_verifier_access__out_of_phase)
        check_access(self, c_admin_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)

        Select(c_admin_selenium.find_element_by_id("id_subject")).select_by_visible_text("Agricultural Sciences")
        manuscript_update_submit_continue = c_admin_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS SUBMISSION : NEW #####

        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.NEW)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        # time.sleep(999999)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### ADD SUBMISSION NOTES (none currently) #####

        c_admin_selenium.get(self.live_server_url + "/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
        submission_info_submit_continue = c_admin_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[5]')
        submission_info_submit_continue.send_keys(Keys.RETURN)
        c_admin_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_CURATION #####

        time.sleep(0.5)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_CURATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING REVIEW CURATION #####

        manuscript_review_submission = c_admin_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### CURATOR REVIEW - ISSUES #####

        Select(c_admin_selenium.find_element_by_id("id_curation_formset-0-_status")).select_by_visible_text("Major Issues")
        c_admin_selenium.find_element_by_id("id_curation_formset-0-report").send_keys("report")
        c_admin_selenium.find_element_by_id("id_curation_formset-0-needs_verification").click()
        Select(c_admin_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_month")).select_by_visible_text("January")
        Select(c_admin_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_day")).select_by_visible_text("1")
        Select(c_admin_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_year")).select_by_visible_text("2020")
        submission_info_submit_continue_curation = c_admin_selenium.find_element_by_id("submit_progress_curation_button")
        submission_info_submit_continue_curation.send_keys(Keys.RETURN)
        c_admin_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_VERIFICATION #####

        time.sleep(0.5)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_VERIFICATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING REVIEW VERIFICATION #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        v_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = v_yes_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### VERIFIER REVIEW - ISSUES #####

        Select(v_yes_selenium.find_element_by_id("id_verification_formset-0-_status")).select_by_visible_text("Major Issues")
        v_yes_selenium.find_element_by_id("id_verification_formset-0-code_executability").send_keys("report")
        v_yes_selenium.find_element_by_id("id_verification_formset-0-report").send_keys("report")
        submission_info_submit_continue_verification = v_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[12]')
        submission_info_submit_continue_verification.send_keys(Keys.RETURN)
        v_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : REVIEWED_AWAITING_REPORT #####

        time.sleep(0.5)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.REVIEWED_AWAITING_REPORT)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING SEND REPORT #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        c_admin_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_send_report = c_admin_selenium.find_element_by_id("sendReportButton")
        manuscript_send_report.send_keys(Keys.RETURN)
        time.sleep(2.5)  # wait for status to update in db, also our pdf code to generate

        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        #TODO: Test is blowing up here. I'm assuming its because something related to the report email fails when testing?...
        self.assertEqual(submission._status, m.Submission.Status.REVIEWED_REPORT_AWAITING_APPROVAL)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING RETURN SUBMISSION (editor step done by curator currently) #####

        # manuscript = m.Manuscript.objects.latest("updated_at")
        # c_admin_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_return_submission = c_admin_selenium.find_element_by_id("returnSubmissionButton")
        manuscript_return_submission.send_keys(Keys.RETURN)
        time.sleep(0.5)  # wait for status to update in db

        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_RESUBMISSION)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.RETURNED)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##############################
        #####    SUBMISSION 2    #####
        ##############################

        submission_previous = submission

        ##### MANUSCRIPT LANDING #####

        manuscript_create_submit_continue = c_admin_selenium.find_element_by_id("createSubmissionButton")
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS MANUSCRIPT : AWAITING_INITIAL #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_RESUBMISSION)

        check_access(self, anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)
        check_access(self, v_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_verifier_access)
        check_access(self, v_yes_selenium, manuscript=manuscript, assert_dict=m_dict_verifier_access__out_of_phase)
        check_access(self, c_admin_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)

        Select(c_admin_selenium.find_element_by_id("id_subject")).select_by_visible_text("Agricultural Sciences")
        manuscript_update_submit_continue = c_admin_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS SUBMISSION : NEW #####

        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.NEW)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        # time.sleep(999999)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### ADD SUBMISSION NOTES (none currently) #####

        c_admin_selenium.get(self.live_server_url + "/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
        submission_info_submit_continue = c_admin_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[5]')
        submission_info_submit_continue.send_keys(Keys.RETURN)
        c_admin_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_CURATION #####

        time.sleep(0.5)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_CURATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

        # Test previous submission access
        check_access(self, anon_selenium, submission=submission_previous, assert_dict=s_dict_anon_no_access__previous )
        check_access(self, v_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous)
        check_access(self, v_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous)
        check_access(self, c_admin_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)

        ##### MANUSCRIPT LANDING REVIEW CURATION #####

        manuscript_review_submission = c_admin_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### CURATOR REVIEW - NO ISSUES #####

        Select(c_admin_selenium.find_element_by_id("id_curation_formset-0-_status")).select_by_visible_text("No Issues")
        c_admin_selenium.find_element_by_id("id_curation_formset-0-report").send_keys("report")
        c_admin_selenium.find_element_by_id("id_curation_formset-0-needs_verification").click()
        Select(c_admin_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_month")).select_by_visible_text("January")
        Select(c_admin_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_day")).select_by_visible_text("1")
        Select(c_admin_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_year")).select_by_visible_text("2020")
        submission_info_submit_continue_curation = c_admin_selenium.find_element_by_id("submit_progress_curation_button")
        submission_info_submit_continue_curation.send_keys(Keys.RETURN)
        c_admin_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_VERIFICATION #####

        time.sleep(0.5)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_VERIFICATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

        # Test previous submission access
        check_access(self, anon_selenium, submission=submission_previous, assert_dict=s_dict_anon_no_access__previous )
        check_access(self, v_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous)
        check_access(self, v_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous)
        check_access(self, c_admin_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)

        ##### MANUSCRIPT LANDING REVIEW VERIFICATION #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        v_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = v_yes_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### VERIFIER REVIEW - NO ISSUES #####

        Select(v_yes_selenium.find_element_by_id("id_verification_formset-0-_status")).select_by_visible_text("Success")
        v_yes_selenium.find_element_by_id("id_verification_formset-0-code_executability").send_keys("report")
        v_yes_selenium.find_element_by_id("id_verification_formset-0-report").send_keys("report")
        submission_info_submit_continue_verification = v_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[12]')
        submission_info_submit_continue_verification.send_keys(Keys.RETURN)
        v_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : PENDING_DATAVERSE_PUBLISH #####

        time.sleep(0.5)  # wait for status to update in db
        
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PENDING_DATAVERSE_PUBLISH)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.REVIEWED_AWAITING_REPORT)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access__completed)

        # Test previous submission access
        check_access(self, anon_selenium, submission=submission_previous, assert_dict=s_dict_anon_no_access__previous )
        check_access(self, v_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous)
        check_access(self, v_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous)
        check_access(self, c_admin_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)

        ##### NOTE: Test ends here because we don't test the dataverse steps currently #####

        # ##### MANUSCRIPT GENERATE REPORT #####

        # c_admin_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id)) #Re-get the page to get the updated buttons
        # manuscript_send_report_button = c_admin_selenium.find_element_by_id('sendReportButton')
        # manuscript_send_report_button.send_keys(Keys.RETURN)

        # ##### TEST ACCESS SUBMISSION : REVIEWED_AWAITING_REPORT #####

        # time.sleep(.5) #wait for status to update in db
        # manuscript = m.Manuscript.objects.latest('updated_at')
        # self.assertEqual(manuscript._status, m.Manuscript.Status.COMPLETED)
        # submission = m.Submission.objects.latest('updated_at')
        # self.assertEqual(submission._status, m.Submission.Status.REVIEWED_REPORT_AWAITING_APPROVAL)

        # check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        # check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        # check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        # check_access(self, c_admin_selenium, submission=submission, assert_dict=s_dict_admin_access)

    # @unittest.skip("Disabled for test writing")
    @override_settings(SKIP_EDITION=False)
    @override_settings(DEBUG=True)
    def test_4_user_workflow_with_access_checks(self):
        
        # Thoughts:
        # - Should I be testing in/out for all roles? (at least 3... maybe skip curator?)
        #   - ... maybe I should go the OTHER way and test both types of curator

        ## If you use these settings, you have to skip our POST test currently because they seem to be contigent on headless...
        self.options_not_headless = Options()
        self.options_not_headless.add_argument("--disable-web-security")
        self.options_not_headless.add_argument("--user-data-dir=/tmp/chrome_dev_test")

        #Yes/No refers to their access to the manuscript
        admin_selenium = self.selenium
        anon_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        a_no_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        a_yes_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        e_no_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        e_yes_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        v_no_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        v_yes_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        c_no_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        c_yes_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)#_not_headless)
        c_admin_no_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        c_admin_yes_selenium = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)

        #Add our new instances to the dict for cleanup when closed via interrupt
        self.selenium_instances['anon'] = anon_selenium
        self.selenium_instances['a_no'] = a_no_selenium
        self.selenium_instances['a_yes'] = a_yes_selenium
        self.selenium_instances['e_no'] = e_no_selenium
        self.selenium_instances['e_yes'] = e_yes_selenium 
        self.selenium_instances['v_no'] = v_no_selenium
        self.selenium_instances['v_yes'] = v_yes_selenium
        self.selenium_instances['c_no'] = c_no_selenium
        self.selenium_instances['c_yes'] = c_yes_selenium
        self.selenium_instances['c_admin_yes'] = c_admin_yes_selenium
        self.selenium_instances['c_admin_no'] = c_admin_no_selenium
        
        ##### ADMIN LOGIN #####

        admin_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", admin_selenium.title)
        current_url = admin_selenium.current_url
        username = admin_selenium.find_element_by_id("id_username")
        password = admin_selenium.find_element_by_id("id_password")
        username.send_keys("admin")
        password.send_keys("password")
        admin_login_submit = admin_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", admin_selenium.title)

        ######################################
        ##### ACCOUNT CREATION AND LOGIN #####
        ######################################

        #NOTE: We create all users here we need via admin commands. These tests don't test new user creation via the standard flow

        ##### ADMIN CREATE CURATOR_ADMIN_YES #####

        curator_admin_yes = m.User.objects.create_superuser("curatoradminyes", "curatoradminyes@test.test", "password")
        role_c = m.Group.objects.get(name=c.GROUP_ROLE_CURATOR)
        role_a = m.Group.objects.get(name=c.GROUP_ROLE_AUTHOR)
        role_e = m.Group.objects.get(name=c.GROUP_ROLE_EDITOR)
        role_c.user_set.add(curator_admin_yes)
        role_a.user_set.add(curator_admin_yes)
        role_e.user_set.add(curator_admin_yes)

        ##### ADMIN CREATE CURATOR_ADMIN_NO #####

        curator_admin_no = m.User.objects.create_superuser("curatoradminno", "curatoradminno@test.test", "password")
        role_c = m.Group.objects.get(name=c.GROUP_ROLE_CURATOR)
        role_a = m.Group.objects.get(name=c.GROUP_ROLE_AUTHOR)
        role_e = m.Group.objects.get(name=c.GROUP_ROLE_EDITOR)
        role_c.user_set.add(curator_admin_no)
        role_a.user_set.add(curator_admin_no)
        role_e.user_set.add(curator_admin_no)

        ##### AUTHOR_NO CREATE #####

        author_no = m.User.objects.create_user("authorno", "author_no@test.test", "password")
        author_no.is_staff = True  # allows admin login without oauth
        author_no.save()
        role_a = m.Group.objects.get(name=c.GROUP_ROLE_AUTHOR)
        role_a.user_set.add(author_no)

        ##### AUTHOR_YES CREATE #####

        author_yes = m.User.objects.create_user("authoryes", "author_yes@test.test", "password")
        author_yes.is_staff = True  # allows admin login without oauth
        author_yes.save()
        role_a = m.Group.objects.get(name=c.GROUP_ROLE_AUTHOR)
        role_a.user_set.add(author_yes)

        ##### CURATOR_ADMIN_YES LOGIN #####

        c_admin_yes_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", c_admin_yes_selenium.title)
        current_url = c_admin_yes_selenium.current_url
        username = c_admin_yes_selenium.find_element_by_id("id_username")
        password = c_admin_yes_selenium.find_element_by_id("id_password")
        username.send_keys("curatoradminyes")
        password.send_keys("password")
        c_admin_yes_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']").send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", c_admin_yes_selenium.title)

        ##### CURATOR_ADMIN_NO LOGIN #####

        c_admin_no_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", c_admin_no_selenium.title)
        current_url = c_admin_no_selenium.current_url
        username = c_admin_no_selenium.find_element_by_id("id_username")
        password = c_admin_no_selenium.find_element_by_id("id_password")
        username.send_keys("curatoradminno")
        password.send_keys("password")
        c_admin_no_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']").send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", c_admin_no_selenium.title)

        ##### AUTHOR_NO LOGIN #####

        a_no_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", a_no_selenium.title)
        current_url = a_no_selenium.current_url
        username = a_no_selenium.find_element_by_id("id_username")
        password = a_no_selenium.find_element_by_id("id_password")
        username.send_keys("authorno")
        password.send_keys("password")
        a_no_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']").send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", a_no_selenium.title)

        ##### AUTHOR_YES LOGIN #####

        a_yes_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", a_yes_selenium.title)
        current_url = a_yes_selenium.current_url
        username = a_yes_selenium.find_element_by_id("id_username")
        password = a_yes_selenium.find_element_by_id("id_password")
        username.send_keys("authoryes")
        password.send_keys("password")
        a_yes_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']").send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", a_yes_selenium.title)


        ##### CURATOR_ADMIN_YES EDITOR_YES CREATION #####

        # This verifier will have verifier to the tested manuscript
        c_admin_yes_selenium.get(self.live_server_url + "/site_actions/inviteeditor/")
        c_admin_yes_selenium.find_element_by_id("id_first_name").send_keys("editor_yes")
        c_admin_yes_selenium.find_element_by_id("id_last_name").send_keys("last_name")
        c_admin_yes_selenium.find_element_by_id("id_email").send_keys("editor_yes@test.test")

        editor_yes_create_button = c_admin_yes_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        editor_yes_create_button.send_keys(Keys.RETURN)

        editor_yes = m.User.objects.get(email="editor_yes@test.test")
        editor_yes.set_password("password")
        editor_yes.username = "editor_yes"
        editor_yes.is_staff = True  # allows admin login without oauth
        editor_yes.save()

        ##### EDITOR_YES LOGIN #####

        e_yes_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", e_yes_selenium.title)
        current_url = e_yes_selenium.current_url
        username = e_yes_selenium.find_element_by_id("id_username")
        password = e_yes_selenium.find_element_by_id("id_password")
        username.send_keys("editor_yes")
        password.send_keys("password")
        e_yes_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']").send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", e_yes_selenium.title)

        ##### CURATOR_ADMIN_YES EDITOR_NO CREATION #####

        # This verifier will have verifier to the tested manuscript
        c_admin_yes_selenium.get(self.live_server_url + "/site_actions/inviteeditor/")
        c_admin_yes_selenium.find_element_by_id("id_first_name").send_keys("editor_no")
        c_admin_yes_selenium.find_element_by_id("id_last_name").send_keys("last_name")
        c_admin_yes_selenium.find_element_by_id("id_email").send_keys("editor_no@test.test")

        editor_no_create_button = c_admin_yes_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        editor_no_create_button.send_keys(Keys.RETURN)

        editor_no = m.User.objects.get(email="editor_no@test.test")
        editor_no.set_password("password")
        editor_no.username = "editor_no"
        editor_no.is_staff = True  # allows admin login without oauth
        editor_no.save()

        ##### EDITOR_NO LOGIN #####

        e_no_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", e_no_selenium.title)
        current_url = e_no_selenium.current_url
        username = e_no_selenium.find_element_by_id("id_username")
        password = e_no_selenium.find_element_by_id("id_password")
        username.send_keys("editor_no")
        password.send_keys("password")
        e_no_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']").send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", e_no_selenium.title)

        ##### CURATOR_ADMIN_YES CURATOR_YES CREATION #####

        # This verifier will have verifier to the tested manuscript
        c_admin_yes_selenium.get(self.live_server_url + "/site_actions/invitecurator/")
        c_admin_yes_selenium.find_element_by_id("id_first_name").send_keys("curator_yes")
        c_admin_yes_selenium.find_element_by_id("id_last_name").send_keys("last_name")
        c_admin_yes_selenium.find_element_by_id("id_email").send_keys("curator_yes@test.test")

        curator_yes_create_button = c_admin_yes_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        curator_yes_create_button.send_keys(Keys.RETURN)

        curator_yes = m.User.objects.get(email="curator_yes@test.test")
        curator_yes.set_password("password")
        curator_yes.username = "curator_yes"
        curator_yes.is_staff = True  # allows admin login without oauth
        curator_yes.save()

        ##### CURATOR_YES LOGIN #####

        c_yes_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", c_yes_selenium.title)
        current_url = c_yes_selenium.current_url
        username = c_yes_selenium.find_element_by_id("id_username")
        password = c_yes_selenium.find_element_by_id("id_password")
        username.send_keys("curator_yes")
        password.send_keys("password")
        c_yes_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']").send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", c_yes_selenium.title)

        ##### CURATOR_ADMIN_YES CURATOR_NO CREATION #####

        # This verifier will have verifier to the tested manuscript
        c_admin_yes_selenium.get(self.live_server_url + "/site_actions/invitecurator/")
        c_admin_yes_selenium.find_element_by_id("id_first_name").send_keys("curator_no")
        c_admin_yes_selenium.find_element_by_id("id_last_name").send_keys("last_name")
        c_admin_yes_selenium.find_element_by_id("id_email").send_keys("curator_no@test.test")

        curator_no_create_button = c_admin_yes_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        curator_no_create_button.send_keys(Keys.RETURN)

        curator_no = m.User.objects.get(email="curator_no@test.test")
        curator_no.set_password("password")
        curator_no.username = "curator_no"
        curator_no.is_staff = True  # allows admin login without oauth
        curator_no.save()

        ##### CURATOR_NO LOGIN #####

        c_no_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", c_no_selenium.title)
        current_url = c_no_selenium.current_url
        username = c_no_selenium.find_element_by_id("id_username")
        password = c_no_selenium.find_element_by_id("id_password")
        username.send_keys("curator_no")
        password.send_keys("password")
        c_no_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']").send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", c_no_selenium.title)

        ##### CURATOR_ADMIN_YES VERIFIER_YES CREATION #####

        # This verifier will have verifier to the tested manuscript
        c_admin_yes_selenium.get(self.live_server_url + "/site_actions/inviteverifier/")
        c_admin_yes_selenium.find_element_by_id("id_first_name").send_keys("verifier_yes")
        c_admin_yes_selenium.find_element_by_id("id_last_name").send_keys("last_name")
        c_admin_yes_selenium.find_element_by_id("id_email").send_keys("verifier_yes@test.test")

        verifier_yes_create_button = c_admin_yes_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        verifier_yes_create_button.send_keys(Keys.RETURN)

        verifier_yes = m.User.objects.get(email="verifier_yes@test.test")
        verifier_yes.set_password("password")
        verifier_yes.username = "verifier_yes"
        verifier_yes.is_staff = True  # allows admin login without oauth
        verifier_yes.save()

        ##### VERIFIER_YES LOGIN #####

        v_yes_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", v_yes_selenium.title)
        current_url = v_yes_selenium.current_url
        username = v_yes_selenium.find_element_by_id("id_username")
        password = v_yes_selenium.find_element_by_id("id_password")
        username.send_keys("verifier_yes")
        password.send_keys("password")
        admin_login_submit = v_yes_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", v_yes_selenium.title)

        ##### CURATOR_ADMIN_YES VERIFIER_NO CREATION #####

        # This verifier will have no access to the tested manuscript
        c_admin_yes_selenium.get(self.live_server_url + "/site_actions/inviteverifier/")
        c_admin_yes_selenium.find_element_by_id("id_first_name").send_keys("verifier_no")
        c_admin_yes_selenium.find_element_by_id("id_last_name").send_keys("last_name")
        c_admin_yes_selenium.find_element_by_id("id_email").send_keys("verifier_no@test.test")

        verifier_no_create_button = c_admin_yes_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        verifier_no_create_button.send_keys(Keys.RETURN)

        verifier_no = m.User.objects.get(email="verifier_no@test.test")
        verifier_no.set_password("password")
        verifier_no.username = "verifier_no"
        verifier_no.is_staff = True  # allows admin login without oauth
        verifier_no.save()

        ##### VERIFIER_NO LOGIN #####

        v_no_selenium.get(self.live_server_url + "/admin")
        self.assertIn("Log in", v_no_selenium.title)
        current_url = v_no_selenium.current_url
        username = v_no_selenium.find_element_by_id("id_username")
        password = v_no_selenium.find_element_by_id("id_password")
        username.send_keys("verifier_no")
        password.send_keys("password")
        admin_login_submit = v_no_selenium.find_element_by_xpath("//div[@class='submit-row']//input[@type='submit']")

        admin_login_submit.send_keys(Keys.RETURN)

        self.assertIn("| CORE2 Admin Site", v_no_selenium.title)

        #################################################
        ##### EDITOR_YES MANUSCRIPT CREATION #####
        #################################################

        e_yes_selenium.get(self.live_server_url + "/manuscript/create/")
        e_yes_selenium.find_element_by_id("id_pub_name").send_keys("pub_name")
        e_yes_selenium.find_element_by_id("id_pub_id").send_keys("pub_id")
        e_yes_selenium.find_element_by_id("id_contact_first_name").send_keys("author_yes")
        e_yes_selenium.find_element_by_id("id_contact_last_name").send_keys("contact_last_name")
        e_yes_selenium.find_element_by_id("id_contact_email").send_keys("author_yes@test.test")

        manuscript_create_submit_continue = e_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[4]')
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        manuscript = m.Manuscript.objects.latest("updated_at")

        ##### UPLOAD MANUSCRIPT FILES (skipping for now) #####

        ##### ADD VERIFIER AND CURATORS TO MANUSCRIPT #####

        # NOTE: For some reason our verifiers don't show up as options for the assignverifier page
        #       This may be because of the javascript/ajax(?)
        #       So instead we'll assign via the backend, but this is a TODO for later
        #       - When we do this, we may want to move where it happens in the flow

        group_manuscript_verifier = m.Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id))
        group_manuscript_verifier.user_set.add(verifier_yes)
        group_manuscript_curator_admin = m.Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id))
        group_manuscript_curator_admin.user_set.add(curator_admin_yes)
        group_manuscript_curator = m.Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id))
        group_manuscript_curator.user_set.add(curator_yes)

        ##### TEST GENERAL CORE2 ACCESS #####

        check_access(self, anon_selenium, assert_dict=g_dict_no_access_anon)
        check_access(self, a_no_selenium, assert_dict=g_dict_normal_access)
        check_access(self, a_yes_selenium, assert_dict=g_dict_normal_access)
        check_access(self, e_no_selenium, assert_dict=g_dict_editor_access)
        check_access(self, e_yes_selenium, assert_dict=g_dict_editor_access)
        check_access(self, v_no_selenium, assert_dict=g_dict_normal_access)
        check_access(self, v_yes_selenium, assert_dict=g_dict_normal_access)
        check_access(self, c_no_selenium, assert_dict=g_dict_normal_curator_access)
        check_access(self, c_yes_selenium, assert_dict=g_dict_normal_curator_access)
        check_access(self, c_admin_no_selenium, assert_dict=g_dict_admin_access)
        check_access(self, c_admin_yes_selenium, assert_dict=g_dict_admin_access)

        ##### TEST ACCESS MANUSCRIPT : NEW #####

        self.assertEqual(manuscript._status, m.Manuscript.Status.NEW)

        check_access(self, anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)
        check_access(self, a_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, a_yes_selenium, manuscript=manuscript, assert_dict=m_dict_no_access) #Does not have access yet
        check_access(self, e_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, e_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_editor_access)
        check_access(self, v_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, v_yes_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, c_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_curator_access__out_of_phase)
        check_access(self, c_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_curator_access)
        check_access(self, c_admin_no_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)
        check_access(self, c_admin_yes_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)

        # ##### ASSIGN AUTHOR TO MANUSCRIPT #####

        e_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/addauthor/")
        # We don't fill out any fields for this form beacuse it is auto-populated with manuscript info
        manuscript_add_author_submit = e_yes_selenium.find_element_by_xpath('//*[@id="content"]/form/input[4]')
        manuscript_add_author_submit.send_keys(Keys.RETURN)
        e_yes_selenium.switch_to.alert.accept()

        ##############################
        #####    SUBMISSION 1    #####
        ##############################

        ##### MANUSCRIPT LANDING #####

        time.sleep(3)  # wait for status to update in db
        a_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/")
        #Fields to fill: abstract, otherenvdetails, operating system, required packages, statistical software, authors, keywords
        #time.sleep(999999)
        manuscript_create_submit_continue = a_yes_selenium.find_element_by_id("createSubmissionButton")
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS MANUSCRIPT : AWAITING_INITIAL #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_INITIAL)

        check_access(self, anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)
        check_access(self, a_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, a_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_author_access)
        check_access(self, e_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, e_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_editor_access)
        check_access(self, v_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, v_yes_selenium, manuscript=manuscript, assert_dict=m_dict_verifier_access__out_of_phase)
        check_access(self, c_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_curator_access)
        check_access(self, c_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_curator_access)
        check_access(self, c_admin_no_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)
        check_access(self, c_admin_yes_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)

        Select(a_yes_selenium.find_element_by_id("id_subject")).select_by_visible_text("Agricultural Sciences")
        a_yes_selenium.find_element_by_id("id_description").send_keys("description")
        #a_yes_selenium.find_element_by_id('id_additional_info').send_keys('additional_info')

        # Select(e_yes_selenium.find_element_by_id("id_compute_env")).select_by_visible_text(
        #     "Other"
        # )  # select unneeded currently because its the only option
        a_yes_selenium.find_element_by_id("id_operating_system").send_keys("operating_system")
        a_yes_selenium.find_element_by_id("id_packages_info").send_keys("packages_info")
        a_yes_selenium.find_element_by_id("id_software_info").send_keys("software_info")
        # NOTE: The selenium test doesn't seem to do JS the same, so our janky formsets don't have a row displayed unless we click
        manuscript_create_add_author_link_button = a_yes_selenium.find_element_by_xpath('//*[@id="author_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_author_link_button.send_keys(Keys.RETURN)
        a_yes_selenium.find_element_by_id("id_author_formset-0-first_name").send_keys("author_0_first_name")
        a_yes_selenium.find_element_by_id("id_author_formset-0-last_name").send_keys("author_0_last_name")
        manuscript_create_add_data_source_link_button = a_yes_selenium.find_element_by_xpath('//*[@id="data_source_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_data_source_link_button.send_keys(Keys.RETURN)
        a_yes_selenium.find_element_by_id("id_data_source_formset-0-text").send_keys("data_source_0_text")
        manuscript_create_add_keyword_link_button = a_yes_selenium.find_element_by_xpath('//*[@id="keyword_table"]/tbody/tr[3]/td/a')
        manuscript_create_add_keyword_link_button.send_keys(Keys.RETURN)
        a_yes_selenium.find_element_by_id("id_keyword_formset-0-text").send_keys("keyword_0_text")

        manuscript_update_submit_continue = a_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')

        #time.sleep(999999) 
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS SUBMISSION : NEW #####

        time.sleep(2)  # wait for status to update in db
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.NEW)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__in_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_yes_access_curator__out_of_phase)        
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### ADD SUBMISSION NOTES (none currently) #####

        a_yes_selenium.get(self.live_server_url + "/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
        submission_info_submit_continue = a_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[2]')
        submission_info_submit_continue.send_keys(Keys.RETURN)
        a_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_EDITION #####

        time.sleep(1)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.REVIEWING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_EDITION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__in_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__out_of_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING REVIEW EDITION #####

        e_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = e_yes_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### EDITION REVIEW - ISSUES #####

        Select(e_yes_selenium.find_element_by_id("id_edition_formset-0-_status")).select_by_visible_text("Issues")
        e_yes_selenium.find_element_by_id("id_edition_formset-0-report").send_keys("report")
        submission_info_submit_continue_edition = e_yes_selenium.find_element_by_id("submit_progress_edition_button")
        submission_info_submit_continue_edition.send_keys(Keys.RETURN)
        e_yes_selenium.switch_to.alert.accept()

        ##### MANUSCRIPT LANDING #####

        time.sleep(1)  # wait for status to update in db
        a_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id) + "/")
        manuscript_create_submit_continue = a_yes_selenium.find_element_by_id("editSubmissionButton")
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        # ##### TEST ACCESS MANUSCRIPT : AWAITING_RESUBMISSION #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_RESUBMISSION)

        check_access(self, anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)
        check_access(self, a_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, a_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_author_access)
        check_access(self, e_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, e_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_editor_access)
        check_access(self, v_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, v_yes_selenium, manuscript=manuscript, assert_dict=m_dict_verifier_access__out_of_phase)
        check_access(self, c_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_curator_access)
        check_access(self, c_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_curator_access)
        check_access(self, c_admin_no_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)
        check_access(self, c_admin_yes_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)

        #Resubmit manuscript before updating submission
        manuscript_update_submit_continue = a_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS SUBMISSION : REJECTED_EDITOR #####

        time.sleep(.5)  # wait for status to update in db
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.REJECTED_EDITOR)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__in_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_yes_access_curator__out_of_phase)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### ADD SUBMISSION NOTES (none currently) #####

        a_yes_selenium.get(self.live_server_url + "/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
        submission_info_submit = a_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[2]')
        submission_info_submit.send_keys(Keys.RETURN)
        a_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_EDITION #####

        time.sleep(1)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.REVIEWING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_EDITION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__in_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__out_of_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING REVIEW EDITION #####

        e_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = e_yes_selenium.find_element_by_id("updateReviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### EDITION REVIEW - NO ISSUES #####

        Select(e_yes_selenium.find_element_by_id("id_edition_formset-0-_status")).select_by_visible_text("No Issues")
        e_yes_selenium.find_element_by_id("id_edition_formset-0-report").send_keys("report new")
        submission_info_submit_continue_edition = e_yes_selenium.find_element_by_id("submit_progress_edition_button")
        submission_info_submit_continue_edition.send_keys(Keys.RETURN)
        e_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_CURATION #####

        time.sleep(1)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_CURATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__out_of_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__out_of_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING REVIEW CURATION #####

        c_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = c_yes_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### CURATOR REVIEW - ISSUES #####

        Select(c_yes_selenium.find_element_by_id("id_curation_formset-0-_status")).select_by_visible_text("Major Issues")
        c_yes_selenium.find_element_by_id("id_curation_formset-0-report").send_keys("report")
        c_yes_selenium.find_element_by_id("id_curation_formset-0-needs_verification").click()
        # Select(c_yes_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_month")).select_by_visible_text("January")
        # Select(c_yes_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_day")).select_by_visible_text("1")
        # Select(c_yes_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_year")).select_by_visible_text("2020")
        submission_info_submit_continue_curation = c_yes_selenium.find_element_by_id("submit_progress_curation_button")
        submission_info_submit_continue_curation.send_keys(Keys.RETURN)
        c_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_VERIFICATION #####

        time.sleep(1)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_VERIFICATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__out_of_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING REVIEW VERIFICATION #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        v_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = v_yes_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### VERIFIER REVIEW - ISSUES #####

        Select(v_yes_selenium.find_element_by_id("id_verification_formset-0-_status")).select_by_visible_text("Major Issues")
        v_yes_selenium.find_element_by_id("id_verification_formset-0-code_executability").send_keys("report")
        v_yes_selenium.find_element_by_id("id_verification_formset-0-report").send_keys("report")
        submission_info_submit_continue_verification = v_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[3]')
        submission_info_submit_continue_verification.send_keys(Keys.RETURN)
        v_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : REVIEWED_AWAITING_REPORT #####

        time.sleep(0.5)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.REVIEWED_AWAITING_REPORT)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__out_of_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING SEND REPORT #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        c_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_send_report = c_yes_selenium.find_element_by_id("sendReportButton")
        manuscript_send_report.send_keys(Keys.RETURN)
        time.sleep(2.5)  # wait for status to update in db, also our pdf code to generate

        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        #TODO: Test is blowing up here. I'm assuming its because something related to the report email fails when testing?...
        self.assertEqual(submission._status, m.Submission.Status.REVIEWED_REPORT_AWAITING_APPROVAL)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__in_phase_finish)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING RETURN SUBMISSION #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        e_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_return_submission = e_yes_selenium.find_element_by_id("returnSubmissionButton")
        manuscript_return_submission.send_keys(Keys.RETURN)
        time.sleep(0.5)  # wait for status to update in db

        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_RESUBMISSION)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.RETURNED)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__out_of_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##############################
        #####    SUBMISSION 2    #####
        ##############################

        submission_previous = submission

        ##### MANUSCRIPT LANDING #####

        a_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_create_submit_continue = a_yes_selenium.find_element_by_id("createSubmissionButton")
        manuscript_create_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS MANUSCRIPT : AWAITING_INITIAL #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_RESUBMISSION)

        check_access(self, anon_selenium, manuscript=manuscript, assert_dict=m_dict_no_access_anon)
        check_access(self, a_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, a_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_author_access)
        check_access(self, e_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, e_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_editor_access)
        check_access(self, v_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_access)
        check_access(self, v_yes_selenium, manuscript=manuscript, assert_dict=m_dict_verifier_access__out_of_phase)
        check_access(self, c_no_selenium, manuscript=manuscript, assert_dict=m_dict_no_curator_access)
        check_access(self, c_yes_selenium, manuscript=manuscript, assert_dict=m_dict_yes_curator_access)
        check_access(self, c_admin_no_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)
        check_access(self, c_admin_yes_selenium, manuscript=manuscript, assert_dict=m_dict_admin_access)

        manuscript_update_submit_continue = a_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[7]')
        manuscript_update_submit_continue.send_keys(Keys.RETURN)

        ##### TEST ACCESS SUBMISSION : NEW #####

        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.NEW)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__in_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_exception)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_yes_access_curator__out_of_phase)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### ADD SUBMISSION NOTES (none currently) #####

        a_yes_selenium.get(self.live_server_url + "/submission/" + str(manuscript.get_latest_submission().id) + "/info/")
        submission_info_submit_continue = a_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[2]')
        submission_info_submit_continue.send_keys(Keys.RETURN)
        a_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_EDITION #####

        time.sleep(1)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.REVIEWING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_EDITION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__in_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__out_of_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        ##### MANUSCRIPT LANDING REVIEW EDITION #####

        e_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = e_yes_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### EDITION REVIEW - NO ISSUES #####

        Select(e_yes_selenium.find_element_by_id("id_edition_formset-0-_status")).select_by_visible_text("No Issues")
        e_yes_selenium.find_element_by_id("id_edition_formset-0-report").send_keys("report new")
        submission_info_submit_continue_edition = e_yes_selenium.find_element_by_id("submit_progress_edition_button")
        submission_info_submit_continue_edition.send_keys(Keys.RETURN)
        e_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_CURATION #####

        time.sleep(0.5)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_CURATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__out_of_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__out_of_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        # Test previous submission access
        check_access(self, anon_selenium, submission=submission_previous, assert_dict=s_dict_anon_no_access__previous )
        check_access(self, a_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous )
        check_access(self, a_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous )
        check_access(self, e_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous )
        check_access(self, e_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous )
        check_access(self, v_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous)
        check_access(self, v_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous)
        check_access(self, c_no_selenium, submission=submission_previous, assert_dict=s_dict_no_curator_access__previous)
        check_access(self, c_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)
        check_access(self, c_admin_no_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)
        check_access(self, c_admin_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)

        ##### MANUSCRIPT LANDING REVIEW CURATION #####
        c_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = c_yes_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### CURATOR REVIEW - NO ISSUES #####

        Select(c_yes_selenium.find_element_by_id("id_curation_formset-0-_status")).select_by_visible_text("No Issues")
        c_yes_selenium.find_element_by_id("id_curation_formset-0-report").send_keys("report")
        c_yes_selenium.find_element_by_id("id_curation_formset-0-needs_verification").click()
        # Select(c_yes_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_month")).select_by_visible_text("January")
        # Select(c_yes_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_day")).select_by_visible_text("1")
        # Select(c_yes_selenium.find_element_by_id("id_submission_editor_date_formset-0-editor_submit_date_year")).select_by_visible_text("2020")
        submission_info_submit_continue_curation = c_yes_selenium.find_element_by_id("submit_progress_curation_button")
        submission_info_submit_continue_curation.send_keys(Keys.RETURN)
        c_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : IN_PROGRESS_VERIFICATION #####

        time.sleep(0.5)  # wait for status to update in db
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_VERIFICATION)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__out_of_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access)

        # Test previous submission access
        check_access(self, anon_selenium, submission=submission_previous, assert_dict=s_dict_anon_no_access__previous )
        check_access(self, a_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous )
        check_access(self, a_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous )
        check_access(self, e_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous )
        check_access(self, e_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous )
        check_access(self, v_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous)
        check_access(self, v_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous)
        check_access(self, c_no_selenium, submission=submission_previous, assert_dict=s_dict_no_curator_access__previous)
        check_access(self, c_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)
        check_access(self, c_admin_no_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)
        check_access(self, c_admin_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)

        ##### MANUSCRIPT LANDING REVIEW VERIFICATION #####

        manuscript = m.Manuscript.objects.latest("updated_at")
        v_yes_selenium.get(self.live_server_url + "/manuscript/" + str(manuscript.id))
        manuscript_review_submission = v_yes_selenium.find_element_by_id("reviewSubmissionButtonMain")
        manuscript_review_submission.send_keys(Keys.RETURN)

        ##### VERIFIER REVIEW - NO ISSUES #####

        Select(v_yes_selenium.find_element_by_id("id_verification_formset-0-_status")).select_by_visible_text("Success")
        v_yes_selenium.find_element_by_id("id_verification_formset-0-code_executability").send_keys("report")
        v_yes_selenium.find_element_by_id("id_verification_formset-0-report").send_keys("report")
        submission_info_submit_continue_verification = v_yes_selenium.find_element_by_xpath('//*[@id="generic_object_form"]/input[3]')
        submission_info_submit_continue_verification.send_keys(Keys.RETURN)
        v_yes_selenium.switch_to.alert.accept()

        ##### TEST ACCESS SUBMISSION : PENDING_DATAVERSE_PUBLISH #####

        time.sleep(0.5)  # wait for status to update in db
        
        manuscript = m.Manuscript.objects.latest("updated_at")
        self.assertEqual(manuscript._status, m.Manuscript.Status.PENDING_DATAVERSE_PUBLISH)
        submission = m.Submission.objects.latest("updated_at")
        self.assertEqual(submission._status, m.Submission.Status.REVIEWED_AWAITING_REPORT)

        check_access(self, anon_selenium, submission=submission, assert_dict=s_dict_no_access_anon)
        check_access(self, a_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, a_yes_selenium, submission=submission, assert_dict=s_dict_author_access__out_of_phase)
        check_access(self, e_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, e_yes_selenium, submission=submission, assert_dict=s_dict_editor_access__out_of_phase)
        check_access(self, v_no_selenium, submission=submission, assert_dict=s_dict_no_access)
        check_access(self, v_yes_selenium, submission=submission, assert_dict=s_dict_verifier_access__in_phase)
        check_access(self, c_no_selenium, submission=submission, assert_dict=s_dict_no_access_curator__in_phase)
        check_access(self, c_yes_selenium, submission=submission, assert_dict=s_dict_admin_access__completed)
        check_access(self, c_admin_no_selenium, submission=submission, assert_dict=s_dict_admin_access__completed)
        check_access(self, c_admin_yes_selenium, submission=submission, assert_dict=s_dict_admin_access__completed)

        # Test previous submission access
        check_access(self, anon_selenium, submission=submission_previous, assert_dict=s_dict_anon_no_access__previous )
        check_access(self, a_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous )
        check_access(self, a_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous )
        check_access(self, e_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous )
        check_access(self, e_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous )
        check_access(self, v_no_selenium, submission=submission_previous, assert_dict=s_dict_no_access__previous)
        check_access(self, v_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_general_access__previous)
        check_access(self, c_no_selenium, submission=submission_previous, assert_dict=s_dict_no_curator_access__previous)
        check_access(self, c_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)
        check_access(self, c_admin_no_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)
        check_access(self, c_admin_yes_selenium, submission=submission_previous, assert_dict=s_dict_yes_full_access__previous)
