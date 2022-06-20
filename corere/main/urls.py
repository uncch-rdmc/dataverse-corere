from django.urls import path

from corere.main.views import datatables, main, users, classes

urlpatterns = [ 
    path('', main.index, name="index"),
    path('manuscript_table/', datatables.ManuscriptJson.as_view(), name="manuscript_table"),
    path('manuscript/create/', classes.ManuscriptCreateView.as_view(), name="manuscript_create"),

    path('manuscript/<int:id>/', main.manuscript_landing, name="manuscript_landing"),
    path('manuscript/<int:manuscript_id>/submission_table/', datatables.SubmissionJson.as_view(), name="submission_table"),
    path('manuscript/<int:id>/edit/', classes.ManuscriptEditView.as_view(), name="manuscript_edit"),
    path('manuscript/<int:id>/update/', classes.ManuscriptUpdateView.as_view(), name="manuscript_update"), #almost same as edit but part of create submission flow
    path('manuscript/<int:id>/uploadfiles/', classes.ManuscriptUploadFilesView.as_view(), name="manuscript_uploadfiles"),
    path('manuscript/<int:id>/uploader/', classes.ManuscriptUploaderView.as_view(), name="manuscript_uploader"),
    path('manuscript/<int:id>/fileslist/', classes.ManuscriptFilesListAjaxView.as_view(),name="manuscript_fileslist"),
    path('manuscript/<int:id>/view/', classes.ManuscriptReadView.as_view(), name="manuscript_read"),
    path('manuscript/<int:id>/viewfiles/', classes.ManuscriptReadFilesView.as_view(), name="manuscript_readfiles"),
    path('manuscript/<int:id>/inviteassignauthor/', users.invite_assign_author, name="manuscript_inviteassignauthor"),
    path('manuscript/<int:id>/addauthor/', users.add_author, name="manuscript_addauthor"),
    path('manuscript/<int:id>/unassignauthor/<int:user_id>/', users.unassign_author, name="manuscript_unassignauthor"),
    path('manuscript/<int:id>/assigneditor/', users.assign_editor, name="manuscript_assigneditor"),
    path('manuscript/<int:id>/unassigneditor/<int:user_id>/', users.unassign_editor, name="manuscript_unassigneditor"),
    path('manuscript/<int:id>/assigncurator/', users.assign_curator, name="manuscript_assigncurator"),
    path('manuscript/<int:id>/unassigncurator/<int:user_id>/', users.unassign_curator, name="manuscript_unassigncurator"),
    path('manuscript/<int:id>/assignverifier/', users.assign_verifier, name="manuscript_assignverifier"),
    path('manuscript/<int:id>/unassignverifier/<int:user_id>/', users.unassign_verifier, name="manuscript_unassignverifier"),
    # path('manuscript/<int:manuscript_id>/createsubmission/', classes.SubmissionCreateView.as_view(), name="manuscript_createsubmission"),
    path('manuscript/<int:id>/deletefile/', classes.ManuscriptDeleteFileView.as_view(), name="manuscript_deletefile"),
    path('manuscript/<int:id>/downloadfile/', classes.ManuscriptDownloadFileView.as_view(), name="manuscript_downloadfile"),
    path('manuscript/<int:id>/downloadall/', classes.ManuscriptDownloadAllFilesView.as_view(), name="manuscript_downloadall"),
    #path('manuscript/<int:id>/notebook/', main.open_notebook, name="manuscript_notebook"), #This is disabled, but we used it for internal container mode so we should look at it again when needed
    #path('manuscript/<int:id>/progress/', classes.ManuscriptProgressView.as_view(), name="manuscript_progress"),
    # path('manuscript/<int:id>/report/', classes.ManuscriptReportView.as_view(), name="manuscript_report"),
    path('manuscript/<int:id>/reportdownload/', classes.ManuscriptReportDownloadView.as_view(), name="manuscript_reportdownload"),
    #path('manuscript/<int:id>/deletenotebook/', main.delete_notebook_stack, name="manuscript_delete_notebook"),
    path('manuscript/<int:id>/file_table/', datatables.ManuscriptFileJson.as_view(), name="manuscript_file_table"),
    path('manuscript/<int:id>/confirm/', classes.ManuscriptEditConfirmBeforeDataverseUploadView.as_view(), name="manuscript_confirmbeforedataverseupload"),
    path('manuscript/<int:id>/pullcitation/', classes.ManuscriptPullCitationFromDataverseView.as_view(), name="manuscript_pullcitationfromdataverse"),

    #TODO: Maybe switch all submission endpoints to be manuscript/<mid>/submission/<version_id>/...
    path('submission/<int:id>/info/', classes.SubmissionEditView.as_view(), name="submission_info"),
    #path('submission/<int:id>/editfiles/', classes.SubmissionEditFilesView.as_view(), name="submission_editfiles"),
    path('submission/<int:id>/uploadfiles/', classes.SubmissionUploadFilesView.as_view(), name="submission_uploadfiles"),
    path('submission/<int:id>/confirmfiles/', classes.SubmissionCompleteFilesBeforeDataverseUploadView.as_view(), name="submission_confirmfilesbeforedataverseupload"),
    path('submission/<int:id>/uploader/', classes.SubmissionUploaderView.as_view(), name="submission_uploader"),
    path('submission/<int:id>/fileslist/', classes.SubmissionFilesListAjaxView.as_view(),name="submission_fileslist"),
    path('submission/<int:id>/view/', classes.SubmissionReadView.as_view(), name="submission_read"),
    path('submission/<int:id>/viewfiles/', classes.SubmissionReadFilesView.as_view(), name="submission_readfiles"),
    path('submission/<int:id>/deletefile/', classes.SubmissionDeleteFileView.as_view(), name="submission_deletefile"),
    path('submission/<int:id>/deleteallfiles/', classes.SubmissionDeleteAllFilesView.as_view(), name="submission_deleteallfiles"),
    path('submission/<int:id>/downloadfile/', classes.SubmissionDownloadFileView.as_view(), name="submission_downloadfile"),
    path('submission/<int:id>/downloadall/', classes.SubmissionDownloadAllFilesView.as_view(), name="submission_downloadall"),
    #path('submission/<int:id>/progress/', classes.SubmissionProgressView.as_view(), name="submission_progress"),
    path('submission/<int:id>/sendreport/', classes.SubmissionSendReportView.as_view(), name="submission_sendreport"),
    path('submission/<int:id>/finish/', classes.SubmissionFinishView.as_view(), name="submission_finish"),
    path('submission/<int:id>/notebook/', classes.SubmissionNotebookView.as_view(), name="submission_notebook"),
    path('submission/<int:id>/notebooklogin/', classes.SubmissionNotebookRedirectView.as_view(), name="submission_notebooklogin"), #Technically this page is more than login, but login is a good user facing name
    path('submission/<int:id>/newfilecheck/', classes.SubmissionFilesCheckNewness.as_view(), name="submission_checkfilenewness"),
    path('submission/<int:id>/wtstream/', classes.SubmissionWholeTaleEventStreamView.as_view(), name="submission_wholetalestream"),
    path('submission/<int:id>/wtdownloadall/', classes.SubmissionDownloadWholeTaleNotebookView.as_view(), name="submission_wholetalestream"),
    path('submission/<int:id>/deleteinstance/', classes.SubmissionDeleteInstanceView.as_view(), name="submission_deleteinstance"),
    path('submission/<int:id>/file_table/', datatables.SubmissionFileJson.as_view(), name="submission_file_table"),

    path('logout/', users.logout_view, name="logout"),
    path('account_associate_oauth/<str:key>/', users.account_associate_oauth, name="account_associate_oauth"),
    path('account_associate_error/', users.account_associate_error, name="account_associate_error"),
    path('account_user_details/', users.account_user_details, name="account_user_details"),
    path('account_complete_oauth/', users.account_complete_oauth, name="account_complete_oauth"),
    path('notifications/', users.notifications, name="notifications"),
    path('wholetale_connection/', main.check_wholetale_connection, name="wholetale_connection"),
    path('site_actions/', main.site_actions, name="site_actions"),
    path('site_actions/inviteeditor/', users.invite_editor, name="inviteeditor"),
    path('site_actions/invitecurator/', users.invite_curator, name="invitecurator"),
    path('site_actions/inviteverifier/', users.invite_verifier, name="inviteverifier"),
    #path('switch_role/', main.switch_role, name="switch_role"),

    #TODO: We need to think better about how we handle this table. It exposes all users usernames (which are emails) and roles. There should probably be a different endpoint for just authors
    path('user_table/', datatables.UserJson.as_view(), name="user_table"),
    
]