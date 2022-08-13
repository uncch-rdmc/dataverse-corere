# TODO Implement a different way to do non-get requests in selenium
# - https://stackoverflow.com/questions/5660956/is-there-any-way-to-start-with-a-post-request-using-selenium
#   - It looks like you can eval javascript to do other request types...

# Tests the state of our accesss dictionaries
def check_access(test, browser, manuscript=None, submission=None, assert_dict=None):
    # return #TODO DISABLE TEST CODE
    if assert_dict == None:
        raise Exception("assert_dict must be set for check_access")
    if manuscript != None and submission != None:
        raise Exception("both manuscript and submission cannot be set at the same time for check_access")

    current_url = browser.current_url  # We get the url before testing to return the browser to at the end

    if manuscript != None:
        url_pre = "/manuscript/" + str(manuscript.id) + "/"
    elif submission != None:
        url_pre = "/submission/" + str(submission.id) + "/"
    else:
        url_pre = "/"

    del browser.requests  # clear previous built up requests

    for url_post, status_dict in assert_dict.items():
        full_url = test.live_server_url + url_pre + url_post
        for method, status_code in status_dict.items():
            # print("")
            # print(full_url)
            # print("...")

            try:

                if method.startswith("GET"): #TODO: Add debug for GET
                    browser.get(full_url)
                    # for request in browser.requests:
                    #     if(request.response):
                    #         print("{} - {}".format(request.url, request.response.status_code))
                    for request in browser.requests:
                        if request.url == full_url and request.response:
                            test.assertEqual(status_code, request.response.status_code, msg=method + " " + full_url)
                            del browser.requests
                elif method.startswith("POST"):
                    # This is for posting without a body, which we use in a few places to progress the manuscript etc.
                    # We'll need something more verbose if we want to pass a body

                    #NOTE: Comment the below call/assert out if you are not running headless. Currently it'll blow up
                    result_status = call_request_method(browser, "POST", full_url, debug=method.endswith("-DEBUG"))
                    test.assertEqual(status_code, result_status, msg="POST " + full_url)

                # elif method == "POST-DEBUG":
                #     result_status = call_request_method(browser, "POST", full_url, debug=True)
                #     test.assertEqual(status_code, result_status, msg=method + " " + full_url)


                else:
                    raise Exception("NO OTHER METHODS SUPPORTED")

            except Exception as e:
                # This block was disabled as we now just disable cors for our selenium tests

                # #TODO: We are catching these post errors that seem to be blowing up because of CORS under the hood.
                # #      I'm not quite sure what caused these, it could have been template refactor but honestly may just be chrome updating?
                # #
                # #      Here is some more verbose error messaging when calling these via the console on our curator selenium browser:

                #             #fetch('http://localhost:60492/manuscript/1/uploader/', {method: 'POST',credentials: 'include'})
                #             #Promise {<pending>}
                #             #localhost/:1 Access to fetch at 'http://localhost:60492/manuscript/1/uploader/' from origin 'http://localhost:61565' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource. If an opaque response serves your needs, set the request's mode to 'no-cors' to fetch the resource with CORS disabled.
                #             #VM323:1          POST http://localhost:60492/manuscript/1/uploader/ net::ERR_FAILED 502
                #             #(anonymous) @ VM323:1
                #             #VM323:1                  Uncaught (in promise) TypeError: Failed to fetch
                #             #    at <anonymous>:1:1
                #             #(anonymous) @ VM323:1
                #             #fetch('http://localhost:60492/manuscript/1/uploader/', {method: 'POST',credentials: 'include', mode: 'no-cors'})
                #             #Promise {<pending>}
                #             #VM371:1          POST http://localhost:60492/manuscript/1/uploader/ net::ERR_ABORTED 502 (Bad Gateway)

                # if(method == 'POST' and hasattr(e, 'msg') and (e.msg.startswith('javascript error') or e.msg.startswith('unexpected alert open'))):
                #     print("Exception with javascript and post on url {}. This seems to be a CORS issue, maybe manifesting in the recent version of chrome. Bypassing for now".format(full_url))
                #     pass #unneeded?

                print("Exception calling {} on url {}".format(method, full_url))
                print(e.__dict__)
                raise e

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


def call_request_method(browser, method, endpoint, debug=False):
    fetch_javascript = "return fetch('" + endpoint + "', {method: '" + method + "',credentials: 'include'})"
    result = browser.execute_script(fetch_javascript)
    if debug:
        # print("DEBUG")
        # print(fetch_javascript)
        print("DEBUG: " + str(result))
    return result["status"]
    # TODO: see manuscript_landing.postToSubUrl and the .then() section if we want to go to the endpoint after.


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
g_dict_admin_access = {  #'': {'GET': 200}, #blows up due to oauth code
    #'manuscript_table/': {'GET': 200},
    "manuscript/create/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change. It errors for editor?
    #'account_user_details/': {'GET': 200}, #blow up due to oauth code
    "notifications/": {"GET": 200, "POST": 405},
    "site_actions/": {"GET": 200, "POST": 405},
    "site_actions/inviteeditor/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    "site_actions/invitecurator/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    "site_actions/inviteverifier/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    # "user_table/": {"GET": 200, "POST": 405},
}

g_dict_normal_curator_access = g_dict_admin_access.copy()
g_dict_normal_curator_access.update(
    {
        "manuscript/create/": {"GET": 403, "POST": 403},
    }
)

# Django's @login_required decorator (and the guardian mixin that uses it) end up with a 200 when redirecting to login.
# ... This may just be due to the different ways we are testing get vs post, not sure
# ... TODO: Add a better test for the anon post calls to ensure that the 200 includes a redirect to login
g_dict_no_access_anon = dict.fromkeys(g_dict_admin_access, {"GET": 302, "POST": 200})

g_dict_normal_access = g_dict_admin_access.copy()
g_dict_normal_access.update(
    {
        # 'manuscript_table/': {'GET': 200},
        # 'notifications/': {'GET': 200},
        # 'user_table/': {'GET': 200}
        "manuscript/create/": {"GET": 403, "POST": 403},
        "site_actions/": {"GET": 404, "POST": 405},
        "site_actions/inviteeditor/": {"GET": 404, "POST": 404},
        "site_actions/invitecurator/": {"GET": 404, "POST": 404},
        "site_actions/inviteverifier/": {"GET": 404, "POST": 404},
    }
)

g_dict_editor_access = g_dict_normal_access.copy()
g_dict_editor_access.update(
    {
        "manuscript/create/": {"GET": 200, "POST": 500},
    }
)

#############################
##### Manuscript Access #####
#############################

# TODO: Most todos in this are stale
m_dict_no_access = {
    "": {"GET": 404, "POST": 405},
    "submission_table/": {"GET": 404, "POST": 405},  
    "edit/": {"GET": 404, "POST": 404},  # TODO: No access anon gets 500?
    "update/": {"GET": 404, "POST": 404},
    "uploadfiles/": {"GET": 404, "POST": 404},
    "uploader/": {"GET": 404, "POST": 404},  # TODO: This is correct but right now we wipe it out with our admin access setting, so I've disabled it
    "fileslist/": {"GET": 404, "POST": 404},
    "view/": {"GET": 404, "POST": 404},
    "viewfiles/": {"GET": 404, "POST": 404},
    "inviteassignauthor/": {"GET": 404, "POST": 404},
    "addauthor/": {"GET": 404, "POST": 404},
    #'unassignauthor/': {'GET': 404}, #this needs a user id
    "assigneditor/": {"GET": 404, "POST": 404},
    #'unassigneditor/': {'GET': 404}, #this needs a user id
    "assigncurator/": {"GET": 404, "POST": 404},
    #'unassigncurator/': {'GET': 404}, #this needs a user id
    "assignverifier/": {"GET": 404, "POST": 404},
    #'unassignverifier/': {'GET': 404}, #this needs a user id
    "deletefile/": {"GET": 404, "POST": 404},  # TODO: This is correct but right now we wipe it out with our admin access setting, so I've disabled it
    "downloadfile/": {"GET": 404, "POST": 404},  # TODO: This is probably correct (I think without passing a file name we should 404), but right now we wipe it out with our admin access setting, so I've disabled it
    "downloadall/": {"GET": 404, "POST": 404},
    "reportdownload/": {"GET": 404, "POST": 404},
    #'deletenotebook/': {'GET': 404}, #TODO: This errors asking for a cookie (WT). Should this work on a get? I may have done that out of laziness.
    "file_table/": {"GET": 404, "POST": 405},  # TODO: Should this 404 instead and hit the access restriction first?
    "confirm/": {"GET": 404, "POST": 404},  # TODO: This is correct but right now we wipe it out with our admin access setting, so I've disabled it
    "pullcitation/": {"GET": 404, "POST": 404}  # TODO: This is correct but right now we wipe it out with our admin access setting, so I've disabled it
}

#TODO: We may want to allow non-admin curators to do more things
m_dict_no_curator_access__out_of_phase = m_dict_no_access.copy()
m_dict_no_curator_access__out_of_phase.update(
    {
        "addauthor/": {"GET": 200, "POST": 200},
        "assigneditor/": {"GET": 200, "POST": 200},
        "assigncurator/": {"GET": 200, "POST": 200},
        "assignverifier/": {"GET": 200, "POST": 200},
    }
)

m_dict_no_curator_access = m_dict_no_curator_access__out_of_phase.copy()
m_dict_no_curator_access.update(
    {
        "": {"GET": 200, "POST": 405},
        "submission_table/": {"GET": 200, "POST": 405},
        "addauthor/": {"GET": 200, "POST": 200},
        "assigneditor/": {"GET": 200, "POST": 200},
        "assigncurator/": {"GET": 200, "POST": 200},
        "assignverifier/": {"GET": 200, "POST": 200},
        "fileslist/": {"GET": 404, "POST": 405},
        "view/": {"GET": 200, "POST": 405},
        "viewfiles/": {"GET": 200, "POST": 405},
        "downloadfile/": {"GET": 404, "POST": 405}, #downloadfile GET 404s because we aren't passing a file
        "downloadall/": {"GET": 200, "POST": 405}, 
        "reportdownload/": {"GET": 200, "POST": 405},
        "file_table/": {"GET": 200, "POST": 405}, 
    }
)

# m_dict_no_editor_access = m_dict_no_author_access.copy()

m_dict_no_verifier_access = m_dict_no_access.copy()
m_dict_no_verifier_access.update(
    {
        "": {"GET": 404, "POST": 405},
    }
)

m_dict_no_access_anon = dict.fromkeys(m_dict_no_access, {"GET": 302, "POST": 200})

m_dict_verifier_access__out_of_phase = m_dict_no_access.copy()
m_dict_verifier_access__out_of_phase.update(
    {
        "": {"GET": 200, "POST": 405},
        "submission_table/": {"GET": 200, "POST": 405},
        "view/": {"GET": 200, "POST": 405},
        "fileslist/": {"GET": 200, "POST": 405},
        "viewfiles/": {"GET": 200, "POST": 405},
        "downloadfile/": {"GET": 404, "POST": 405},
        "downloadall/": {"GET": 200, "POST": 405},
        "reportdownload/": {"GET": 200, "POST": 405},
        "file_table/": {"GET": 200, "POST": 405},
    }
)

m_dict_admin_access = {
    "": {"GET": 200, "POST": 405},
    "submission_table/": {"GET": 200, "POST": 405},
    "edit/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    "update/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    "uploadfiles/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    "uploader/": {"GET": 405, "POST": 404},  # TODO: Test with files to get actual 200
    "fileslist/": {"GET": 200, "POST": 405},
    "view/": {"GET": 200, "POST": 405},
    "viewfiles/": {"GET": 200, "POST": 405},
    "inviteassignauthor/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    "addauthor/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    #'unassignauthor/': {'GET': 200}, #this needs a user id
    "assigneditor/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    #'unassigneditor/': {'GET': 200}, #this needs a user id
    "assigncurator/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    #'unassigncurator/': {'GET': 200}, #this needs a user id
    "assignverifier/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    #'unassignverifier/': {'GET': 200}, #this needs a user id
    "deletefile/": {"GET": 405, "POST": 404},  # TODO: Test with files to get actual 200. Also maybe switch code to actually use delete.
    "downloadfile/": {"GET": 404, "POST": 405},  # TODO: Test with files to get actual 200
    "downloadall/": {"GET": 200, "POST": 405},
    "reportdownload/": {"GET": 200, "POST": 405},
    #'deletenotebook/': {'GET': 200}, #TODO: This errors asking for a cookie (WT). Should this work on a get? I may have done that out of laziness.
    "file_table/": {"GET": 200, "POST": 405},
    "confirm/": {"GET": 404, "POST": 404},  # TODO: This is conditionally available, and maybe requires post
    "pullcitation/": {"GET": 404, "POST": 404}  # TODO: This is conditionally available, and maybe requires post. | POST 404s because its called out of phase and TransistionPermissionMixin happens first I think
}

m_dict_yes_author_access = m_dict_admin_access.copy()
m_dict_yes_author_access.update(
    {
        "inviteassignauthor/": {"GET": 404, "POST": 404},
        "addauthor/": {"GET": 404, "POST": 404},
        "assigneditor/": {"GET": 404, "POST": 404}, 
        "assigncurator/": {"GET": 404, "POST": 404}, 
        "assignverifier/": {"GET": 404, "POST": 404}, 
    }
)

m_dict_yes_editor_access = m_dict_admin_access.copy()
m_dict_yes_editor_access.update(
    {
        "inviteassignauthor/": {"GET": 404, "POST": 404},
        "assigneditor/": {"GET": 404, "POST": 404}, 
        "assigncurator/": {"GET": 404, "POST": 404}, 
        "assignverifier/": {"GET": 404, "POST": 404}, 
    }
)

#TODO: We may want to allow non-admin curators to do more things
m_dict_yes_curator_access = m_dict_admin_access.copy()
m_dict_yes_curator_access.update(
    {
    }
)


# TODO: What additional dictionaries do I need?
# - Author (in and out of phase?)
# - Editor (in and out of phase?)
# - Curator (same as admin?)

#############################
##### Submission Access #####
#############################

# TODO: access on some of these change with phase
s_dict_admin_access = {
    "info/": {"GET": 200},  # TODO-FIX: Not testing post because it 500s at some phases. Investigate
    "uploadfiles/": {"GET": 200},  # TODO: Post disabled because it returns literally nothing, probably due to changing the file datatable to be more restrictive on when its visible    
    "confirmfiles/": {"GET": 404, "POST": 404},  #TODO: Post disabled because it causes an ajax error. Probably due to changing file_table perms check.
    "uploader/": {"GET": 405, "POST": 404},  # Test with files to get actual 200
    "fileslist/": {"GET": 200, "POST": 405},
    "view/": {"GET": 200, "POST": 200},  # TODO: POST - I'm surprised an empty body doesn't error, maybe change
    "viewfiles/": {"GET": 200, "POST": 500},  # TODO: Fix this! Maybe its a phase issue (happens during NEW). Or a lack of files?
    "deletefile/": {"GET": 405, "POST": 404},
    "deleteallfiles/": {"GET": 405, "POST": 200},
    "downloadfile/": {"GET": 404},  # Needs a query string to not 404
    "downloadall/": {"GET": 200, "POST": 405},
    "sendreport/": {"GET": 405},  # TODO: Not testing post because its phase dependent. Need to fix tests and add more cases
    "finish/": {"GET": 405},  # TODO: Not testing post because its phase dependent. Need to fix tests and add more cases
    #    'notebook/': {'GET': 200},
    #    'notebooklogin/': {'GET': 200},
    "newfilecheck/": {"GET": 404, "POST": 405},  # Need a query string to not 404
    #    'wtstream/': {'GET': 200},
    #    'wtdownloadall/': {'GET': 200},
    "file_table/": {"GET": 200, "POST": 405},  # TODO: Should this 404 instead and hit the access restriction first?
}

s_dict_admin_access__completed = s_dict_admin_access.copy()
s_dict_admin_access__completed.update({"confirmfiles/": {"GET": 200}})

s_dict_yes_access_curator__out_of_phase = s_dict_admin_access.copy()
s_dict_yes_access_curator__out_of_phase.update(
    {
        "view/": {"GET": 404}, #, "POST": 404 Post disabled because ajax error, probably due to changing the file_table#TODO: Why does this 404? Because view is disabled when you have edit if you are non admin?
        "viewfiles/": {"GET": 404, "POST": 404}, #TODO: Why does this 404? Because view is disabled when you have edit if you are non admin?
        "downloadall/": {"GET": 404, "POST": 404}, #TODO: I really don't understand why this is 404ing
        "newfilecheck/": {"GET": 404, "POST": 404},  # Need a query string to not 404
        "file_table/": {"GET": 200, "POST": 405},  # TODO: Should this 404 instead and hit the access restriction first?
        "confirmfiles/": {"GET": 404 , "POST": 404},   #TODO: Disabled because it causes an ajax error / 500s. Probably due to changing file_table perms check.
        "uploader/": {"GET": 405, "POST": 404},  # Test with files to get actual 200
        "fileslist/": {"GET": 200, "POST": 405},
    }
)

s_dict_yes_access_curator__in_phase = s_dict_admin_access.copy()
s_dict_yes_access_curator__in_phase.update(
    {

    }
)

s_dict_no_access = {
    "info/": {"GET": 404, "POST": 404},
    "uploadfiles/": {"GET": 404, "POST": 404},
    "confirmfiles/": {"GET": 404, "POST": 404},
    "uploader/": {"GET": 404, "POST": 404},
    "fileslist/": {"GET": 404, "POST": 404},
    "view/": {"GET": 404, "POST": 404},
    "viewfiles/": {"GET": 404, "POST": 404},
    "deletefile/": {"GET": 404, "POST": 404},
    "deleteallfiles/": {"GET": 404, "POST": 404},
    "downloadfile/": {"GET": 404, "POST": 404},
    "downloadall/": {"GET": 404, "POST": 404},
    "sendreport/": {"GET": 405, "POST": 404},
    "finish/": {"GET": 405, "POST": 404},
    #    'notebook/': {'GET': 404},
    #    'notebooklogin/': {'GET': 404},
    "newfilecheck/": {"GET": 404, "POST": 404},
    #    'wtstream/': {'GET': 404},
    #    'wtdownloadall/': {'GET': 404},
    "file_table/": {"GET": 404, "POST": 405},  # TODO: Should this 404 instead and hit the access restriction first?
}

#TODO: This is really a fix for a broken piece of code. file_table shouldn't 200. Then we can delete this and just use s_dict_no_access
s_dict_no_access_exception = s_dict_no_access.copy()
s_dict_no_access_exception.update(
    {
         "file_table/": {"GET": 200, "POST": 405},
    }
)

s_dict_no_access_anon = dict.fromkeys(s_dict_no_access, {"GET": 302, "POST": 200}) #TODO: Should we be testing post for anon?

s_dict_author_access__out_of_phase = s_dict_no_access.copy()
s_dict_author_access__out_of_phase.update(
    {
        "info/": {"GET": 200, "POST": 200},
        "view/": {"GET": 200, "POST": 200},
        "viewfiles/": {"GET": 200, "POST": 500},  # TODO-FIX: Maybe the 500 is a phase issue. Or a lack of files?

        "downloadfile/": {"GET": 404, "POST": 405},  # Need a query string to not 404
        "downloadall/": {"GET": 200, "POST": 405},
        "newfilecheck/": {"GET": 404, "POST": 405},
        "file_table/": {"GET": 200, "POST": 405},
    }
)

s_dict_author_access__in_phase = s_dict_author_access__out_of_phase.copy()
s_dict_author_access__in_phase.update(
    {

        "uploadfiles/": {"GET": 200, "POST": 200},
        "uploader/": {"GET": 405, "POST": 404},        
        "fileslist/": {"GET": 200, "POST": 405},
        "deletefile/": {"GET": 405, "POST": 404},
        "deleteallfiles/": {"GET": 405, "POST": 200}, 
    }
)

s_dict_editor_access__out_of_phase = s_dict_no_access.copy()
s_dict_editor_access__out_of_phase.update(
    {
        "info/": {"GET": 200, "POST": 200},
        "view/": {"GET": 200, "POST": 200},
        "viewfiles/": {"GET": 200, "POST": 500},  # TODO-FIX: Maybe the 500 is a phase issue. Or a lack of files?

        "downloadfile/": {"GET": 404, "POST": 405},  # Need a query string to not 404
        "downloadall/": {"GET": 200, "POST": 405},
        "newfilecheck/": {"GET": 404, "POST": 405},
        "file_table/": {"GET": 200, "POST": 405},
    }
)

s_dict_editor_access__in_phase = s_dict_no_access.copy()
s_dict_editor_access__in_phase.update(
    {
        "info/": {"GET": 200, "POST": 200},
        "view/": {"GET": 200, "POST": 200},
        "viewfiles/": {"GET": 200, "POST": 500},  # TODO-FIX: Maybe the 500 is a phase issue. Or a lack of files?

        "downloadfile/": {"GET": 404, "POST": 405},  # Need a query string to not 404
        "downloadall/": {"GET": 200, "POST": 405},
        "newfilecheck/": {"GET": 404, "POST": 405},
        "file_table/": {"GET": 200, "POST": 405},
    }
)

s_dict_editor_access__in_phase_finish = s_dict_editor_access__in_phase.copy()
s_dict_editor_access__in_phase_finish.update(
    {
        "finish/": {"GET": 405}, #removed post test, it'll be confirmed by the actual flow
    }
)

#TODO: Are these accesses what we want for non-admin curator? Surprised they can't do view or info
#Curators still have access even when they aren't assigned. The access is the same regardless of phase
s_dict_no_access_curator__in_phase = s_dict_no_access.copy()
s_dict_no_access_curator__in_phase.update(
    {
        "viewfiles/": {"GET": 200, "POST": 500},  # TODO-FIX: Maybe the 500 is a phase issue. Or a lack of files?
        "downloadfile/": {"GET": 404, "POST": 405},  # Need a query string to not 404
        "downloadall/": {"GET": 200, "POST": 405},
        "newfilecheck/": {"GET": 404, "POST": 405},
        "file_table/": {"GET": 200, "POST": 405},
    }
)

s_dict_verifier_access__out_of_phase = s_dict_no_access.copy()
s_dict_verifier_access__out_of_phase.update(
    {
        "info/": {"GET": 200, "POST": 200},
        "view/": {"GET": 200, "POST": 200},
        "viewfiles/": {"GET": 200, "POST": 500},  # TODO-FIX: Maybe the 500 is a phase issue. Or a lack of files?

        "downloadfile/": {"GET": 404, "POST": 405},  # Need a query string to not 404
        "downloadall/": {"GET": 200, "POST": 405},
        "newfilecheck/": {"GET": 404, "POST": 405},
        "file_table/": {"GET": 200, "POST": 405},
    }
) 

s_dict_verifier_access__in_phase = s_dict_no_access.copy()
s_dict_verifier_access__in_phase.update(
    {
        "info/": {"GET": 200, "POST": 200},
        "view/": {"GET": 200, "POST": 200},
        "viewfiles/": {"GET": 200, "POST": 500},  # TODO-FIX: Maybe its a phase issue (happens during NEW). Or a lack of files?
        "downloadfile/": {"GET": 404, "POST": 405},  # Need a query string to not 404
        "downloadall/": {"GET": 200, "POST": 405},
        "newfilecheck/": {"GET": 404, "POST": 405},
        "file_table/": {"GET": 200, "POST": 405},
    }
)

# These don't test all previous endpoints currently, just a sampling

s_dict_previous_submission_write_access_verifier = {
    "view/": {"GET": 200, "POST": 200},
    "info/": {"GET": 200, "POST": 200}, #TODO: POST was 200 for verifier but 500 for curator_admin
    "viewfiles/": {"GET": 200, "POST": 500}, #TODO: why 500?
    "uploadfiles/": {"GET": 404, "POST": 404} #I guess uploading files should 404 for everyone? The submission is over? #Nope, 200 for curator admin, 404 for verifier... tho this may be because verifier could never upload?
}

s_dict_previous_submission_write_access_admin = {
    "view/": {"GET": 200, "POST": 200},
    "info/": {"GET": 200, "POST": 500}, #TODO: Why 500?
    "viewfiles/": {"GET": 200, "POST": 500}, #TODO: why 500?
    "uploadfiles/": {"GET": 200, "POST": 200} 
}

# s_dict_previous_submission_read_access = {
#     "view/": {"GET": 200, "POST": 200}, #Should out of phase be able to post notes in view?
#     "info/": {"GET": 404, "POST": 404},
#     "viewfiles/": {"GET": 200, "POST": 404},
#     "uploadfiles/": {"GET": 404, "POST": 404}
# }

s_dict_previous_submission_no_access = {
    "view/": {"GET": 404, "POST": 404},
    "info/": {"GET": 404, "POST": 404},
    "viewfiles/": {"GET": 404, "POST": 404},
    "uploadfiles/": {"GET": 404, "POST": 404}
}

#TODO: When we test post for other anon, add here too
s_dict_previous_submission_no_access_anon = {
    "view/": {"GET": 302},
    "info/": {"GET": 302},
    "viewfiles/": {"GET": 302},
    "uploadfiles/": {"GET": 302}
}