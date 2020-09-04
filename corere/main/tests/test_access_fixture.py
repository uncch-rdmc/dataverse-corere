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
from django.core.management import call_command

# Fixture generation:
# - python3 manage.py dumpdata --indent=4 > corere/main/fixtures/manuscript_submission_states.json
#
# Fixture editing. You can load the fixture "normally" (and wipe out existing info by):
# - drop and create database with postgres (manage.py flush does not work)
# - python3 manage.py migrate
# - python3 manage.py loaddata manuscript_submission_states.json -e contenttypes

### NOTE: With all these tests, I tested all the important cases and some of the "this really shouldn't happen" cases. It is a bit vague though
#@unittest.skip("Incomplete")
class BaseTestWithFixture(TestCase):
    #fixtures = ['manuscript_submission_states']

    #Our many contants to make referncing our various cases easier
    #(Technically most "nouser" manuscripts actually have admin as an author)
    #Also note that even though we have files, delete does not actually delete a GitlabFile, it calls GitLab. So its kinda pointless to have these cases
    #Loading the submission page checks gitlab every time and deletes files if needed.
    M_NEW_NOUSER         = 1   # New manuscript no assigned users for any roles
    M_NEW_ALLUSER        = 2   # New manuscript users assigned for all 4 roles
    M_NEW_AUTH_ED        = 22  # Manuscript initial submission created and submitted, author roles. Has files on sub
    M_NEW_AUTH           = 23  # Manuscript initial submission created and submitted, author roles. Has files on sub
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
    M_DUR_SUB1_NOUSER_F  = 11  # Manuscript initial submission created but not submit, no roles. Has files (and not great notes)
    M_DUR_SUB1_ALLUSER_F = 12  # Manuscript initial submission created but not submit, all roles. Has files (and not great notes)
    M_B4_SUB1_NOUSER     = 15  # Manuscript awaiting initial submission, no roles
    M_DUR_SUB1_NOUSER    = 16  # Manuscript initial submission created but not submit, no roles
    M_B4_CUR1_NOUSER     = 17  # Manuscript awaiting initial curation, no roles
    M_DUR_CUR1_NOUSER    = 18  # Manuscript initial curation created but not submit, no roles
    M_B4_VER1_NOUSER     = 19  # Manuscript awaiting initial verification, no roles
    M_DUR_VER1_NOUSER    = 20  # Manuscript initial verification created but not submit, no roles
    M_B4_CUR1_AUTHOR_F   = 21  # Manuscript initial submission created and submitted, author roles. Has files on sub

    S_DUR_SUB1_ALLUSER   = 4
    S_B4_CUR1_ALLUSER    = 1
    S_DUR_CUR1_ALLUSER   = 5
    S_B4_VER1_ALLUSER    = 2
    S_DUR_VER1_ALLUSER   = 6
    S_B4_SUB2_ALLUSER    = 3 
    S_DONE_ALLUSER       = 9 
    S_DONE_NOUSER        = 10
    S_DUR_SUB1_NOUSER_F  = 7
    S_DUR_SUB1_ALLUSER_F = 8
    S_DUR_SUB1_NOUSER    = 11  
    S_B4_CUR1_NOUSER     = 12 
    S_DUR_CUR1_NOUSER    = 13 
    S_B4_VER1_NOUSER     = 14 
    S_DUR_VER1_NOUSER    = 15  
    S_B4_CUR1_AUTHOR_F   = 16

    C_DUR_CUR1_ALLUSER   = 3 
    C_B4_VER1_ALLUSER    = 1
    C_DUR_VER1_ALLUSER   = 4  
    C_B4_SUB2_ALLUSER    = 2  
    C_DONE_ALLUSER       = 5  
    C_DONE_NOUSER        = 6  
    C_DUR_CUR1_NOUSER    = 7 
    C_B4_VER1_NOUSER     = 8 
    C_DUR_VER1_NOUSER    = 9  

    V_DUR_VER1_ALLUSER   = 2  
    V_B4_SUB2_ALLUSER    = 1   
    V_DONE_ALLUSER       = 3 
    V_DONE_NOUSER        = 4  
    V_DUR_VER1_NOUSER    = 5 

    #These notes are attached to various objects. 
    # The ones with _AD were created by the admin, otherwise they were created by the author/curator/verifier used in the tests
    N_DUR_SUB1_ALLUSER = 9  # Submission 4 / S_DUR_SUB1_ALLUSER
    N_DUR_SUB1_AUTHOR = 10  # Submission 4 / S_DUR_SUB1_ALLUSER
    N_DUR_SUB1_AUTHOR_AD = 21  # Submission 4 / S_DUR_SUB1_ALLUSER
    N_B4_CUR1_ALLUSER = 11  # Submission 1 / S_B4_CUR1_ALLUSER
    N_B4_CUR1_AUTHOR = 12   # Submission 1 / S_B4_CUR1_ALLUSER
    N_B4_CUR1_AUTHOR_AD = 22   # Submission 1 / S_B4_CUR1_ALLUSER
    N_DUR_CUR1_ALLUSER = 13 # Curation 3 / C_DUR_CUR1_ALLUSER
    N_DUR_CUR1_CURATOR = 14 # Curation 3 / C_DUR_CUR1_ALLUSER
    N_DUR_CUR1_CURATOR_AD = 23 # Curation 3 / C_DUR_CUR1_ALLUSER
    N_B4_VER1_ALLUSER = 15  # Curation 1 / C_B4_VER1_ALLUSER
    N_B4_VER1_CURATOR = 16  # Curation 1 / C_B4_VER1_ALLUSER
    N_B4_VER1_CURATOR_AD = 24  # Curation 1 / C_B4_VER1_ALLUSER
    N_DUR_VER1_ALLUSER = 17 # Verification 2 / V_DUR_VER1_ALLUSER 
    N_DUR_VER1_VERIF = 18   # Verification 2 / V_DUR_VER1_ALLUSER 
    N_DUR_VER1_VERIF_AD = 25   # Verification 2 / V_DUR_VER1_ALLUSER 
    N_B4_SUB2_ALLUSER = 19  # Verification 1 / V_B4_SUB2_ALLUSER
    N_B4_SUB2_VERIF = 20    # Verification 1 / V_B4_SUB2_ALLUSER
    N_B4_SUB2_VERIF_AD = 26    # Verification 1 / V_B4_SUB2_ALLUSER

    #Fixture is initialized here so we can call it once per class instead of method.
    #Downside is we could munge our test data. Seems worthwhile for now
    def setUpTestData():
        call_command(
            'loaddata', 
            'manuscript_submission_states.json',
            verbosity=0
        )

#####################################################################################################################################################
########## AUTHOR
#####################################################################################################################################################
class TestAuthorUrlAccess(BaseTestWithFixture):
    def test_AuthorAccess_IndexOther(self):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        #Authors can only view their own manuscripts and submissions
        self.assertEqual(cl.get(reverse("index")).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_table")).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_NEW_NOUSER    })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_NEW_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR})).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_DONE_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_DONE_NOUSER   })).status_code, 404)

        # pain to test # self.assertEqual(cl.get(reverse("account_associate_oauth")).status_code, 200)
        self.assertEqual(cl.get(reverse("account_user_details")).status_code, 200)
        self.assertEqual(cl.get(reverse("notifications")).status_code, 200)
        self.assertEqual(cl.get(reverse("site_actions")).status_code, 404)
        self.assertEqual(cl.get(reverse("inviteeditor")).status_code, 404)
        self.assertEqual(cl.get(reverse("invitecurator")).status_code, 404)
        self.assertEqual(cl.get(reverse("inviteverifier")).status_code, 404)
        self.assertEqual(cl.get(reverse("logout")).status_code, 302)

    @mock.patch('corere.main.views.main.gitlab_delete_file', mock.Mock())
    @mock.patch('corere.main.views.classes.gitlab_repo_get_file_folder_list', return_value=[])
    def test_AuthorAccess_ManuscriptCreateEdit(self, mock_gitlab_file_list):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)   

        ###We only test binders we can't access, because it redirects to an external service (and the functionality is not flushed out)
        self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_DONE_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_NEW_NOUSER   })).status_code, 404)

        #Only editor/curator can progress manuscript
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_NEW_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_NEW_NOUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_B4_SUB2_ALLUSER })).status_code, 404)

        ### Author can never create/edit manuscript. 
        self.assertEqual(cl.get(reverse("manuscript_create")).status_code, 403)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_NEW_ALLUSER    })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_NEW_ALLUSER    })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_B4_CUR1_ALLUSER})).status_code, 404)
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
        
        ### Author cannot delete from manuscript
        self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_DUR_SUB1_NOUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        # can't test with mock #self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_NEW_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitlabFiles actually on here, but delete just passes through to gitlab


    def test_AuthorAccess_ManuscriptAssign(self):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)   

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
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DONE_NOUSER      })).status_code, 404)

    @mock.patch('corere.main.views.classes.helper_populate_gitlab_files_submission', mock.Mock())
    @mock.patch('corere.main.views.main.gitlab_delete_file', mock.Mock())
    @mock.patch('corere.main.views.main.gitlab_submission_delete_all_files', mock.Mock())
    @mock.patch('corere.main.views.classes.gitlab_repo_get_file_folder_list', return_value=[])
    def test_AuthorAccess_Submission(self, mock_gitlab_file_list):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        ### Author can create submissions when one isn't already created. Post will probably break once we have any fields on the submission.
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_NOUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR   })).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_NOUSER   })).status_code, 404)

        ### All submission edit actions should only be doable when a submission is in progress
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DONE_NOUSER      })).status_code, 404)

        ### Read should be doable at any point there is a submission
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DONE_ALLUSER    })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DONE_NOUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_CUR1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_CUR1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_VER1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_VER1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DONE_ALLUSER    })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DONE_NOUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_CUR1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_CUR1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_VER1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_VER1_NOUSER })).status_code, 404)
        
        ### Author cannot create these
        # self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={'submission_id':self.S_B4_CUR1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createverification", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createverification", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createverification", kwargs={'submission_id':self.S_B4_VER1_NOUSER  })).status_code, 404)

        #We currently allow creating, editing, deleting notes they own at any point, even though the ui doesn't provide a path to the page when its not editing
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_ALLUSER    })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_NOUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_CUR1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_AUTHOR})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_AUTHOR_AD})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_AUTHOR})).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_AUTHOR_AD})).status_code, 404)

        ### Author can only delete from their own submission
        self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 302)
        self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        # can't test with mock #self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitlabFiles actually on here, but delete just passes through to gitlab
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER_F })).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER_F })).status_code, 404)

        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)



#Ok so... curator needs fixing for sure
#Right now it can view all manuscripts, but the perm check in a lot of places only looks for "object based", not global (I think)
#Also right not curator can't do any assignments which... it absolutely needs to do.
#...
#Maybe someday we'll need curators who can only see their assignments, but for now I should just design to not block that out


#####################################################################################################################################################
########## Curator
#####################################################################################################################################################
#NOTE: Curators have fairly verbose edit prividges, but they are not shown in the UI. There needs to be more discussions on what is needed.
class TestCuratorUrlAccess(BaseTestWithFixture):
    def test_CuratorAccess_IndexOther(self):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        #Curators can view all manuscripts and submissions
        self.assertEqual(cl.get(reverse("index")).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_table")).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_NEW_NOUSER    })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_NEW_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_DONE_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={'manuscript_id':self.M_DONE_NOUSER   })).status_code, 200)

        # pain to test # self.assertEqual(cl.get(reverse("account_associate_oauth")).status_code, 200)
        self.assertEqual(cl.get(reverse("account_user_details")).status_code, 200)
        self.assertEqual(cl.get(reverse("notifications")).status_code, 200)
        self.assertEqual(cl.get(reverse("site_actions")).status_code, 200)
        self.assertEqual(cl.get(reverse("inviteeditor")).status_code, 200)
        self.assertEqual(cl.get(reverse("invitecurator")).status_code, 200)
        self.assertEqual(cl.get(reverse("inviteverifier")).status_code, 200)
        self.assertEqual(cl.get(reverse("logout")).status_code, 302)

    @mock.patch('corere.main.views.main.gitlab_delete_file', mock.Mock())
    @mock.patch('corere.main.views.classes.gitlab_repo_get_file_folder_list', return_value=[])
    def test_CuratorAccess_ManuscriptCreateEdit(self, mock_gitlab_file_list):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)   

        ###We only test binders we can't access, because it redirects to an external service (and the functionality is not flushed out)
        # self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_DONE_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_NEW_NOUSER   })).status_code, 200)

        #Only curator/editor can progress manuscript, the ones they are assigned.
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_NEW_NOUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_NEW_ALLUSER })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_NEW_AUTH_ED })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_NEW_AUTH })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_NEW_NOUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_DONE_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={'id':self.M_DONE_NOUSER })).status_code, 404)

        ### Curator can only create/edit manuscripts they are assigned. Only after a round is completed.
        self.assertEqual(cl.get(reverse("manuscript_create")).status_code, 403)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_NEW_ALLUSER    })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_B4_CUR1_ALLUSER})).status_code, 404)
        #codebroken maybe #self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_NEW_ALLUSER    })).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_B4_CUR1_ALLUSER})).status_code, 404)
        #codebroken maybe #self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_NEW_NOUSER        })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_B4_SUB1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_B4_CUR1_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_DUR_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_B4_SUB2_ALLUSER   })).status_code, 200)
        #codebroken maybe #self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_NEW_NOUSER        })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_B4_SUB1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_B4_CUR1_ALLUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_DUR_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_B4_SUB2_ALLUSER   })).status_code, 200)
        #codebroken maybe #self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 404)
        
        ### Curator should always be able to read manuscript contents, even if not assigned
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_NEW_NOUSER        })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_B4_SUB1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_B4_CUR1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_DUR_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_B4_SUB2_ALLUSER   })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={'id':self.M_DONE_NOUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_NEW_NOUSER        })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_B4_SUB1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_B4_CUR1_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_DUR_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_B4_SUB2_ALLUSER   })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_DONE_ALLUSER   })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={'id':self.M_DONE_NOUSER   })).status_code, 200)
        
        ### Curator can delete from manuscript
        self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_DUR_CUR1_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_DUR_SUB1_NOUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        # can't test with mock #self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_NEW_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitlabFiles actually on here, but delete just passes through to gitlab


    def test_CuratorAccess_ManuscriptAssign(self):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)   

        ### Curator can invite all roles
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_NEW_NOUSER       })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_NEW_ALLUSER      })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_DUR_CUR1_ALLUSER })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_DONE_ALLUSER     })).status_code, 404)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={'id':self.M_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_NEW_NOUSER       })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_NEW_ALLUSER      })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_DUR_CUR1_ALLUSER })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_DONE_ALLUSER     })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={'id':self.M_DONE_NOUSER      })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_NEW_NOUSER       })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_NEW_ALLUSER      })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_DUR_CUR1_ALLUSER })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_DONE_ALLUSER     })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={'id':self.M_DONE_NOUSER      })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_NEW_NOUSER       })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_NEW_ALLUSER      })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_DUR_SUB1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_DUR_CUR1_ALLUSER })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_DONE_ALLUSER     })).status_code, 200)
        #codebroken #self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={'id':self.M_DONE_NOUSER      })).status_code, 200)
        
        ### Only curators can unassign
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_NEW_ALLUSER      })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={'user_id':5, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_DONE_ALLUSER     })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':5, 'id':self.M_DONE_NOUSER      })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_NEW_ALLUSER      })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DONE_ALLUSER     })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={'user_id':6, 'id':self.M_DONE_NOUSER      })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_NEW_ALLUSER      })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DONE_ALLUSER     })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={'user_id':7, 'id':self.M_DONE_NOUSER      })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_NEW_NOUSER       })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_NEW_ALLUSER      })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_B4_SUB1_ALLUSER  })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DUR_SUB1_ALLUSER })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_B4_CUR1_ALLUSER  })).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DUR_CUR1_ALLUSER })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DONE_ALLUSER     })).status_code, 302)
        #codebroken #self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={'user_id':8, 'id':self.M_DONE_NOUSER      })).status_code, 302)

    @mock.patch('corere.main.views.classes.helper_populate_gitlab_files_submission', mock.Mock())
    @mock.patch('corere.main.views.main.gitlab_delete_file', mock.Mock())
    @mock.patch('corere.main.views.main.gitlab_submission_delete_all_files', mock.Mock())
    @mock.patch('corere.main.views.classes.gitlab_repo_get_file_folder_list', return_value=[])
    def test_CuratorAccess_Submission(self, mock_gitlab_file_list):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        ### Curator cannot create submission.
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_NOUSER   })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_NEW_ALLUSER      })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR   })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_NOUSER   })).status_code, 404)


        ### Curator cannot edit submission
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_edit", kwargs={'id':self.S_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={'id':self.S_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={'id':self.S_DONE_NOUSER      })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={'id':self.S_DONE_NOUSER      })).status_code, 404)

        ### For curator, read should be doable at any point there is a submission completed
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DONE_ALLUSER    })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DONE_NOUSER     })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_CUR1_NOUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_CUR1_NOUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_B4_VER1_NOUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={'id':self.S_DUR_VER1_NOUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_SUB2_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DONE_ALLUSER    })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DONE_NOUSER     })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_CUR1_NOUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_CUR1_NOUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_B4_VER1_NOUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={'id':self.S_DUR_VER1_NOUSER })).status_code, 200)
 
        # Curator cannot add notes to submission
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_ALLUSER    })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_NOUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_CUR1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_AUTHOR_AD})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_AUTHOR_AD})).status_code, 404)

        ### Curator cannot delete submission files
        self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER_F })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404)
        # can't test with mock #self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitlabFiles actually on here, but delete just passes through to gitlab
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER_F })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER_F })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })).status_code, 404)

        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={'id':self.S_DUR_VER1_ALLUSER })).status_code, 404)

    @mock.patch('corere.main.views.classes.helper_populate_gitlab_files_submission', mock.Mock())
    @mock.patch('corere.main.views.main.gitlab_delete_file', mock.Mock())
    @mock.patch('corere.main.views.main.gitlab_submission_delete_all_files', mock.Mock())
    @mock.patch('corere.main.views.classes.gitlab_repo_get_file_folder_list', return_value=[])
    def test_CuratorAccess_Curation(self, mock_gitlab_file_list):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={'submission_id':self.S_B4_CUR1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)

        ### Curator can edit curations they are assigned at the right phase
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={'id':self.C_DUR_CUR1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={'id':self.C_DUR_CUR1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={'id':self.C_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={'id':self.C_B4_SUB2_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={'id':self.C_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={'id':self.C_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={'id':self.C_DONE_NOUSER      })).status_code, 404)

        ### For curator, read should be doable at any point there is a curation completed
        self.assertEqual(cl.get(reverse("curation_read", kwargs={'id':self.C_DUR_CUR1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={'id':self.C_B4_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={'id':self.C_DUR_VER1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={'id':self.C_B4_SUB2_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={'id':self.C_DONE_ALLUSER    })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={'id':self.C_DONE_NOUSER     })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={'id':self.C_DUR_CUR1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={'id':self.C_B4_VER1_NOUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={'id':self.C_DUR_VER1_NOUSER })).status_code, 200)
 
        ### We currently allow creating, editing, deleting notes they own at any point, even though the ui doesn't provide a path to the page when its not editing
        self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER  })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_SUB2_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_ALLUSER    })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_NOUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)
        self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 302)
        self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 302)
        self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("curation_progress", kwargs={'id':self.C_DUR_CUR1_ALLUSER })).status_code, 302)
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={'id':self.C_DUR_CUR1_ALLUSER })).status_code, 404) #can't call twice
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={'id':self.C_DUR_CUR1_NOUSER })).status_code, 404)
#TODO: This shouldn't work, I think you can call progress again before the new verification has been saved?? I think its progressing the verification
        #codebroken #self.assertEqual(cl.post(reverse("curation_progress", kwargs={'id':self.C_DUR_VER1_ALLUSER })).status_code, 404)  

    @mock.patch('corere.main.views.classes.helper_populate_gitlab_files_submission', mock.Mock())
    @mock.patch('corere.main.views.main.gitlab_delete_file', mock.Mock())
    @mock.patch('corere.main.views.main.gitlab_submission_delete_all_files', mock.Mock())
    @mock.patch('corere.main.views.classes.gitlab_repo_get_file_folder_list', return_value=[])
    def test_CuratorAccess_Verification(self, mock_gitlab_file_list):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={'submission_id':self.S_B4_CUR1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={'submission_id':self.S_B4_VER1_NOUSER  })).status_code, 404)

        ### Curator cannot edit verifications
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={'id':self.V_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={'id':self.V_DUR_VER1_NOUSER  })).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={'id':self.V_B4_SUB2_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={'id':self.V_DONE_ALLUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={'id':self.V_DONE_NOUSER      })).status_code, 404)

        ### For curator, read should be doable at any point there is a curation completed
        self.assertEqual(cl.get(reverse("verification_read", kwargs={'id':self.V_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={'id':self.V_B4_SUB2_ALLUSER })).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={'id':self.V_DONE_ALLUSER    })).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={'id':self.V_DONE_NOUSER     })).status_code, 200)
 
        ### Curator cannot add notes to verifications
        self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_ALLUSER    })).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_NOUSER     })).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_NOUSER })).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)

#TODO: This shouldn't work, I think you can call progress again before the new verification has been saved?? I think its progressing the verification
        #codebroken #self.assertEqual(cl.post(reverse("verification_progress", kwargs={'id':self.V_DUR_VER1_ALLUSER })).status_code, 404)
        #codebroken #self.assertEqual(cl.post(reverse("verification_progress", kwargs={'id':self.V_DUR_VER1_ALLUSER })).status_code, 404) #can't call twice
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={'id':self.V_DUR_VER1_NOUSER })).status_code, 404)

