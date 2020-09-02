import json, unittest, mock
#import urllib.parse
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from corere.main.middleware import local
from corere.main import constants as c
from corere.main import models as m
from django.contrib.auth.models import Permission, Group
from rest_framework import status
from http import HTTPStatus
#from inspect import getframeinfo, stack

#TODO: Delete these unused helper methods

# #will error on methods without id
# def helper_check_statuses(testself, client, verb, endpoint, id_name, id_result_dict):
#     lineno = getframeinfo(stack()[1][0]).lineno #gets the line number our helper was called from

#     for mid in id_result_dict:
#         resp = client.get(reverse(endpoint, kwargs={id_name:mid}))
#         error_msg =  "(Line#:{0} | Endpoint:{1} | Object_id:{2})".format(lineno, endpoint, mid) #If this errors this is the message
#         testself.assertEqual(resp.status_code, id_result_dict[mid], error_msg)

#will error on methods without id
# def helper_check_statuses(testself, client, endpoint, verb, id_name, manuscript_list, result_list):
#     lineno = getframeinfo(stack()[1][0]).lineno #gets the line number our helper was called from
#     if(len(manuscript_list) != len(result_list)):
#         raise Exception('List lengths must be the same!')
#     for i in range(len(manuscript_list)):
#         resp = client.get(reverse(endpoint, kwargs={id_name:manuscript_list[i]}))
#         error_msg =  "(Line#:{0} | Endpoint:{1} | Manuscript_id:{2})".format(lineno, endpoint, manuscript_list[i]) #If this errors this is the message
#         testself.assertEqual(resp.status_code, result_list[i], error_msg)



# Fixture generation:
# - python3 manage.py dumpdata --indent=4 > corere/main/fixtures/manuscript_submission_states.json
#
# Fixture editing. You can load the fixture "normally" (and wipe out existing info by):
# - drop and create database with postgres (manage.py flush does not work)
# - python3 manage.py migrate
# - python3 manage.py loaddata manuscript_submission_states.json -e contenttypes

### NOTE: With all these tests, I tested all the important cases and some of the "this really shouldn't happen" cases. It is a bit vague though
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
    M_DONE_ALLUSER       = 13  # Manuscript completed, all roles (well actually not, they get removed currently)
    M_DONE_NOUSER        = 14  # Manuscript completed, no roles
    M_DUR_SUB1_NOUSER_F  = 11  # Manuscript initial submission created but not submit, no roles. Has notes/files
    M_DUR_SUB1_ALLUSER_F = 12  # Manuscript initial submission created but not submit, all roles. Has notes/files

    def testFixtureLoad(self):
        manuscript = m.Manuscript.objects.get(pk=1)
        self.assertEquals(manuscript.doi, 'test')

    @mock.patch('corere.main.models.gitlab_create_manuscript_repo', mock.Mock())
    @mock.patch('corere.main.models.gitlab_create_submissions_repo', mock.Mock())
    def testAssignedAuthorAccessManuscript(self):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)
        
        self.assertEqual(cl.get(reverse("index")).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_table")).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_NEW_NOUSER    })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_NEW_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR})).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_DONE_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_DONE_NOUSER   })).status_code, 404)
        
        ### Author can never create/edit manuscript. 
        self.assertEqual(cl.get(reverse("manuscript_create")).status_code, 403)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_NEW_ALLUSER    })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_NEW_ALLUSER    })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_NEW_NOUSER        })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_B4_SUB1_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_B4_CUR1_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_DUR_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_B4_SUB2_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_NEW_NOUSER        })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_B4_SUB1_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_B4_CUR1_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_DUR_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_B4_SUB2_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        
        ### Author should always be able to read manuscript contents when assigned
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_NEW_NOUSER        })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_B4_SUB1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_B4_CUR1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_DUR_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_B4_SUB2_ALLUSER   })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_DONE_NOUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_NEW_NOUSER        })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_B4_SUB1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_B4_CUR1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_DUR_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_B4_SUB2_ALLUSER   })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_DONE_NOUSER   })).status_code, 404)
        
        ### Author should always be able to invite other authors, but no other roles
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_NEW_ALLUSER      })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_DUR_CUR1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_DONE_NOUSER      })).status_code, 404)
        
        ### Only curators can unassign
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':5, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':5, 'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':5, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':5, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':5, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':5, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':5, 'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':5, 'id':self.M_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':5, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':5, 'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':5, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':5, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':5, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':5, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':5, 'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':5, 'id':self.M_DONE_NOUSER      })).status_code, 404)

        ### Need to be able to get and post on create. Post will probably break once we have any fields on the submission.
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR   })).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DONE_ALLUSER     })).status_code, 404)

        ### Author cannot delete from manuscript
        self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_DUR_SUB1_NOUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 404)

        ###We only test binders we can't access, because it redirects to an external service (and the functionality is not flushed out)
        self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_DONE_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_NEW_NOUSER   })).status_code, 404)

        #Only editor can progress manuscript
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_NEW_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_NEW_NOUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_B4_SUB2_ALLUSER })).status_code, 404)

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

    def testAssignedCuratorAccessManuscript(self):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_NEW_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_NEW_ALLUSER   })).status_code, 404) #You can't unassign the same person twice
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_B4_SUB1_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_DUR_CUR1_ALLUSER   })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_DONE_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_NEW_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_NEW_ALLUSER   })).status_code, 404) #You can't unassign the same person twice
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_B4_SUB1_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DUR_CUR1_ALLUSER   })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DONE_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_NEW_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_NEW_ALLUSER   })).status_code, 404) #You can't unassign the same person twice
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_B4_SUB1_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DUR_CUR1_ALLUSER   })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DONE_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_NEW_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_NEW_ALLUSER   })).status_code, 404) #You have already unassigned yourself
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_B4_SUB1_ALLUSER   })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DUR_CUR1_ALLUSER   })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DONE_ALLUSER   })).status_code, 302)