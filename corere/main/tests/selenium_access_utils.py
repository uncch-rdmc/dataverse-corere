# TODO Implement a different way to do non-get requests in selenium
# - https://stackoverflow.com/questions/5660956/is-there-any-way-to-start-with-a-post-request-using-selenium
#   - It looks like you can eval javascript to do other request types...

#Tests the state of our accesss dictionaries
def check_access(test, browser, manuscript=None, submission=None, assert_dict=None):
    if assert_dict == None:
        raise Exception('assert_dict must be set for check_access')            
    if manuscript != None and submission != None:
        raise Exception('both manuscript and submission cannot be set at the same time for check_access')

    current_url = browser.current_url #We get the url before testing to return the browser to at the end

    if manuscript != None:
        url_pre = '/manuscript/' + str(manuscript.id) + '/'
    elif submission != None:
        url_pre = '/submission/' + str(submission.id) + '/'
    else:
        url_pre = '/'

    del browser.requests #clear previous built up requests

    for url_post, status_dict in assert_dict.items():
        full_url = test.live_server_url + url_pre + url_post
        for method, status_code in status_dict.items():
            print("")
            print(full_url)
            print("...")
            
            if method == 'GET':
                browser.get(full_url)
                
                for request in browser.requests:
                    if(request.response):
                        print("{} - {}".format(request.url, request.response.status_code))
                for request in browser.requests:
                    if request.url == full_url and request.response:
                        test.assertEqual(request.response.status_code, status_code, msg=full_url)
                        del browser.requests
            else:
                raise Exception("NO OTHER METHODS SUPPORTED")

    browser.get(current_url)

            # try:
            #     response = browser.request(method, full_url)
            # except Exception as e:
            #     print("Error in check_access request. URL: {}, Method: {}".format(full_url, method))
            #     raise e
            # if status_code == 302:
            #     #If we expect a 302, we look for it in the history
            #     if response.history:
            #         test.assertEqual(response.history[0].status_code, status_code, msg="Checking 302 status in history. URL: {}, Method: {}".format(full_url, method))
            #         test.assertEqual(response.status_code, 200, msg="Checking 200 status on current page. URL: {}, Method: {}".format(full_url, method))
            #     else: 
            #         print(full_url)
            #         #time.sleep(500000)
            #         test.fail("Checking 302 status, there was no history. This means that there was no 302. Status: {}, URL: {}, Method: {}".format(response.status_code, full_url, method))
            # else:
            #     # print(response.__dict__)
            #     # print(response.history[0].status_code)
            #     test.assertEqual(response.status_code, status_code, msg=method + ": " + full_url)

###############################
###############################
##### ACCESS DICTIONARIES #####
###############################
###############################

# These dictionaries are used with check_access to test endpoints throughout the workflow.
# We use "inheritance" to define some of the dictionaries as slight alterations of other ones.
# These dictionaries don't check everything, as some endpoints progress code when called.

##########################
##### General Access #####
##########################

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
    'manuscript/create/': {'GET': 403}, 
    'site_actions/': {'GET': 404}, 
    'site_actions/inviteeditor/': {'GET': 404}, 
    'site_actions/invitecurator/': {'GET': 404}, 
    'site_actions/inviteverifier/': {'GET': 404}, 
})

g_dict_normal_editor_access = g_dict_normal_access.copy()
g_dict_normal_editor_access.update({
    'manuscript/create/': {'GET': 200}, 
})

#############################
##### Manuscript Access #####
#############################

#TODO: Most todos in this are stale
m_dict_no_access = {
    '': {'GET': 404},
    'submission_table/': {'GET': 404}, #TODO: No access verifier gets a 200. Should this instead error? I need to check the content returned.
    'edit/': {'GET': 404}, #TODO: No access anon gets 500?
    'update/': {'GET': 404},
    'uploadfiles/': {'GET': 404},
    'uploader/': {'GET': 404}, #TODO: This is correct but right now we wipe it out with our admin access setting, so I've disabled it
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
    'deletefile/': {'GET': 404}, #TODO: This is correct but right now we wipe it out with our admin access setting, so I've disabled it
    'downloadfile/': {'GET': 404}, #TODO: This is probably correct (I think without passing a file name we should 404), but right now we wipe it out with our admin access setting, so I've disabled it
    'downloadall/': {'GET': 404},
    'reportdownload/': {'GET': 404},
    #'deletenotebook/': {'GET': 404}, #TODO: This errors asking for a cookie (WT). Should this work on a get? I may have done that out of laziness.
    'file_table/': {'GET': 404},  #TODO: No access verifier gets a 200. Should this instead error? I need to check the content returned.
    'confirm/': {'GET': 404}, #TODO: This is correct but right now we wipe it out with our admin access setting, so I've disabled it
    'pullcitation/': {'GET': 404} #TODO: This is correct but right now we wipe it out with our admin access setting, so I've disabled it
}

m_dict_no_access_anon = dict.fromkeys(m_dict_no_access, {'GET': 302})

#TODO: Add editor/curator/verifier when we test all roles

m_dict_verifier_access__out_of_phase = m_dict_no_access.copy()
m_dict_verifier_access__out_of_phase.update({
    '': {'GET': 200},
    'submission_table/': {'GET': 200}, 
    'view/': {'GET': 200}, 
    'fileslist/': {'GET': 200},
    'viewfiles/': {'GET': 200},
    'downloadall/': {'GET': 200},
    'reportdownload/': {'GET': 200},
    'file_table/': {'GET': 200},
})

m_dict_admin_access = {
    '': {'GET': 200},
    'submission_table/': {'GET': 200},
    'edit/': {'GET': 200},
    'update/': {'GET': 200},
    'uploadfiles/': {'GET': 200},
    'uploader/': {'GET': 405},
    'fileslist/': {'GET': 200},
    'view/': {'GET': 200},
    'viewfiles/': {'GET': 200},
    'inviteassignauthor/': {'GET': 200},
    'addauthor/': {'GET': 200},
    #'unassignauthor/': {'GET': 200}, #this needs a user id
    'assigneditor/': {'GET': 200},
    #'unassigneditor/': {'GET': 200}, #this needs a user id
    'assigncurator/': {'GET': 200},
    #'unassigncurator/': {'GET': 200}, #this needs a user id
    'assignverifier/': {'GET': 200},
    #'unassignverifier/': {'GET': 200}, #this needs a user id
    'deletefile/': {'GET': 405}, 
    'downloadfile/': {'GET': 404}, #TODO: Test with files to get actual 200
    'downloadall/': {'GET': 200},
    'reportdownload/': {'GET': 200},
    #'deletenotebook/': {'GET': 200}, #TODO: This errors asking for a cookie (WT). Should this work on a get? I may have done that out of laziness.
    'file_table/': {'GET': 200},
    'confirm/': {'GET': 404}, #TODO: This is conditionally available, and maybe requires post
    'pullcitation/': {'GET': 404} #TODO: This is conditionally available, and maybe requires post
}

#############################
##### Submission Access #####
#############################

#TODO: access on some of these change with phase
s_dict_admin_access = {
    'info/': {'GET': 200},
    'uploadfiles/': {'GET': 200},
    'confirmfiles/': {'GET': 404}, 
    'uploader/': {'GET': 405},
    'fileslist/': {'GET': 200},
    'view/': {'GET': 200},
    'viewfiles/': {'GET': 200},
    'deletefile/': {'GET': 405},
    'deleteallfiles/': {'GET': 405},
    'downloadfile/': {'GET': 404}, #Needs a query string to not 404
    'downloadall/': {'GET': 200},
    'sendreport/': {'GET': 405},
    'finish/': {'GET': 405},
#    'notebook/': {'GET': 200},
#    'notebooklogin/': {'GET': 200},
    'newfilecheck/': {'GET': 404}, #Need a query string to not 404
#    'wtstream/': {'GET': 200},
#    'wtdownloadall/': {'GET': 200},
    'file_table/': {'GET': 200} 
}

s_dict_admin_access__completed = s_dict_admin_access.copy()
s_dict_admin_access__completed.update({
    'confirmfiles/': {'GET': 200}  
 })

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
    'sendreport/': {'GET': 405},
    'finish/': {'GET': 405},
#    'notebook/': {'GET': 404},
#    'notebooklogin/': {'GET': 404},
    'newfilecheck/': {'GET': 404},
#    'wtstream/': {'GET': 404},
#    'wtdownloadall/': {'GET': 404},
    'file_table/': {'GET': 404} 
}

s_dict_no_access_anon = dict.fromkeys(s_dict_no_access, {'GET': 302})

s_dict_verifier_access__out_of_phase = s_dict_no_access.copy()
s_dict_verifier_access__out_of_phase.update({
    'file_table/': {'GET': 200}  #TODO: This should probably 404
 })

s_dict_verifier_access__in_phase = s_dict_no_access.copy()
s_dict_verifier_access__in_phase.update({
    'info/': {'GET': 200},
    'view/': {'GET': 200},
    'viewfiles/': {'GET': 200},
    'downloadall/': {'GET': 200},
    'file_table/': {'GET': 200} 
 })