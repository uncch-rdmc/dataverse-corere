import json, unittest, mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from corere.main.middleware import local
from corere.main import constants as c
from corere.main import models as m
from django.contrib.auth.models import Permission, Group
from rest_framework import status
from http import HTTPStatus
from inspect import getframeinfo, stack


#will error on methods without id
def helper_check_statuses(testself, client, verb, endpoint, id_name, id_result_dict):
    lineno = getframeinfo(stack()[1][0]).lineno #gets the line number our helper was called from

    for mid in id_result_dict:
        resp = client.get(reverse(endpoint, kwargs={id_name:mid}))
        error_msg =  "(Line#:{0} | Endpoint:{1} | Object_id:{2})".format(lineno, endpoint, mid) #If this errors this is the message
        testself.assertEqual(resp.status_code, id_result_dict[mid], error_msg)

#will error on methods without id
# def helper_check_statuses(testself, client, endpoint, verb, id_name, manuscript_list, result_list):
#     lineno = getframeinfo(stack()[1][0]).lineno #gets the line number our helper was called from
#     if(len(manuscript_list) != len(result_list)):
#         raise Exception('List lengths must be the same!')
#     for i in range(len(manuscript_list)):
#         resp = client.get(reverse(endpoint, kwargs={id_name:manuscript_list[i]}))
#         error_msg =  "(Line#:{0} | Endpoint:{1} | Manuscript_id:{2})".format(lineno, endpoint, manuscript_list[i]) #If this errors this is the message
#         testself.assertEqual(resp.status_code, result_list[i], error_msg)

#@unittest.skip("Incomplete")
class TestUrlAccessFixture(TestCase):
    fixtures = ['manuscript_submission_states']

    M_NEW_NOUSER         = 1   # New manuscript no assigned users for any roles
    M_NEW_ALLUSER        = 2   # New manuscript users assigned for all 4 roles
    M_B4_SUB1_ALLUSER    = 3   # Manuscript awaiting initial submission, all 4 roles
    M_B4_SUB1_AUTHOR     = 4   # Manuscript awaiting initial submission, only author assigned
    M_DUR_SUB1_ALLUSER   = 8   # Manuscript initial submission created but not submit, all 4 roles
    M_B4_CUR1_ALLUSER    = 5   # Manuscript awaiting initial curation, all 4 roles
    M_DUR_CUR1_ALLUSER   = 9   # Manuscript initial curation created but not submit, all 4 roles
    M_B4_VER1_ALLUSER    = 6   # Manuscript awaiting initial verification, all 4 roles
    M_DUR_VER1_ALLUSER   = 10  # Manuscript initial verification created but not submit, all 4 roles
    M_B4_SUB2_ALLUSER    = 7   # Manuscript awaiting second submission, all 4 roles
    M_DUR_SUB1_NOUSER_F  = 11   # Manuscript initial submission created but not submit, no roles. Has notes/files
    M_DUR_SUB1_ALLUSER_F = 12   # Manuscript initial submission created but not submit, all roles. Has notes/files

    def testFixtureLoad(self):
        manuscript = m.Manuscript.objects.get(pk=1)
        self.assertEquals(manuscript.doi, 'test')

    #What do I need to add to my fixture to test access to "all" of our endpoints?:
    # - Notes for real (above is for view which we aren't testing):
    #   - Users should be able to edit/delete their own notes only. Though I think this is broken. 'change_note' isn't even used.
    #   - But really though we only need 4 notes, one for each role, just to be thorough
    #   - Could have one per sub/cur/ver, but honestly this'll need more work anyways so good enough for now
    # - GitlabFile
    #   - We really just to test deletefile
    #   - Any user who can edit can delete currently
    #   - Maybe 2 files, one that everyone can access and one that no one can access?
    #       - Means I need to create another manuscript with a submission that is all assigned to the admin

    # Fixture generation:
    # - python3 manage.py dumpdata --indent=4 > corere/main/fixtures/manuscript_submission_states.json
    
    # Fixture editing. You can load the fixture "normally" (and wipe out existing info by):
    # - drop and create database with postgres (manage.py flush does not work)
    # - python3 manage.py migrate
    # - python3 manage.py loaddata manuscript_submission_states.json -e contenttypes

    def testAssignedAuthorAccessManuscript(self):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)
        
        self.assertEqual(cl.get(reverse("index")).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_table")).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_NEW_NOUSER    })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_NEW_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_create")).status_code, 403)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_NEW_ALLUSER    })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_B4_SUB1_ALLUSER})).status_code, 404)

        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_NEW_NOUSER        })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_B4_SUB1_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_B4_CUR1_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_DUR_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_B4_SUB2_ALLUSER   })).status_code, 404)

        #You can edit files when a sub/cur/ver is not in progress

#TODO: Tomorrow fill this out for all roles, do notes and gitlabfiles. get it all done and move on


        resp = cl.get(reverse("manuscript_fileslist", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_read", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_readfiles", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_unassignauthor", kwargs={'id':5, 'user_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_assigneditor", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_unassigneditor", kwargs={'id':5, 'user_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_assigncurator", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_unassigncurator", kwargs={'id':5, 'user_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_assignverifier", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_unassignverifier", kwargs={'id':5, 'user_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_deletefile", kwargs={'manuscript_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_binder", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = cl.get(reverse("manuscript_progress", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)

        # resp = cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_NEW_NOUSER}))
        # self.assertEqual(resp.status_code, 200)

        # helper_check_statuses(self, cl, "submission_table", "get", 'manuscript_id', \
        #     [self.M_NEW_NOUSER,self.M_NEW_ALLUSER,self.M_BEFORE_SUB1_AUTHOR ], \
        #     [404,200,200])

        # helper_check_statuses(self, cl, "get", "submission_table", 'manuscript_id', \
        #     {self.M_NEW_NOUSER:404, self.M_NEW_ALLUSER:200, self.M_BEFORE_SUB1_AUTHOR:200})

    def testAssignedAuthorAccessSubCurVer(self):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        # resp = cl.get(reverse("submission_edit", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_editfiles", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_uploadfiles", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_fileslist", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_read", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_readfiles", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_createcuration", kwargs={'submission_id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_createverification", kwargs={'submission_id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_createnote", kwargs={'submission_id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_editnote", kwargs={'submission_id':5, 'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_deletenote", kwargs={'submission_id':5, 'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_deletefile", kwargs={'submission_id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_deleteallfiles", kwargs={'submission_id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("submission_progress", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)

        # resp = cl.get(reverse("curation_edit", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("curation_read", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("curation_createnote", kwargs={'curation_id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("curation_editnote", kwargs={'curation_id':5, 'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("curation_deletenote", kwargs={'curation_id':5, 'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("curation_progress", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        
        # resp = cl.get(reverse("verification_edit", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("verification_read", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("verification_createnote", kwargs={'verification_id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("verification_editnote", kwargs={'verification_id':5, 'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("verification_deletenote", kwargs={'verification_id':5, 'id':5}))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("verification_progress", kwargs={'id':5}))
        # self.assertEqual(resp.status_code, 200)
        
    def testAssignedAuthorAccessOther(self):
        pass
        # untested currently
        # resp = cl.get(reverse("account_associate_oauth", kwargs={'key':5}))
        # self.assertEqual(resp.status_code, 200)

        # resp = cl.get(reverse("account_user_details"))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("notifications"))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("site_actions"))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("site_actions/inviteeditor"))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("site_actions/invitecurator"))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("site_actions/inviteverifier"))
        # self.assertEqual(resp.status_code, 200)
        # resp = cl.get(reverse("logout"))
        # self.assertEqual(resp.status_code, 200)