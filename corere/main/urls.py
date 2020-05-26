from django.urls import path

from corere.main.views import datatables, main, users


urlpatterns = [ 
    path('', main.index),
    path('manuscript_table', datatables.ManuscriptJson.as_view(), name="manuscript_table"),
    path('manuscript/<int:manuscript_id>/submission_table', datatables.SubmissionJson.as_view(), name="submission_table"),
    path('manuscript/create', main.ManuscriptCreateView.as_view(), name="manuscript_create"),
    path('manuscript/<int:id>/edit', main.ManuscriptEditView.as_view(), name="manuscript_edit"),
    path('manuscript/<int:id>/editfiles', main.ManuscriptEditFilesView.as_view(), name="manuscript_editfiles"),
    path('manuscript/<int:id>/view', main.ManuscriptReadView.as_view(), name="manuscript_read"),
    path('manuscript/<int:id>/addauthor', users.add_author, name="manuscript_addauthor"),
    #TODO: Add deleteauthor and test
    path('manuscript/<int:id>/addcurator', users.add_curator, name="manuscript_addcurator"),
    path('manuscript/<int:id>/deletecurator/<int:user_id>', users.delete_curator, name="manuscript_deletecurator"),
    path('manuscript/<int:id>/addverifier', users.add_verifier, name="manuscript_addverifier"),
    path('manuscript/<int:id>/deleteverifier/<int:user_id>', users.delete_verifier, name="manuscript_deleteverifier"),
    path('manuscript/<int:manuscript_id>/createsubmission', main.SubmissionCreateView.as_view(), name="manuscript_createsubmission"),
    path('manuscript/<int:manuscript_id>/deletefile', main.delete_file, name="manuscript_deletefile"), #TODO: This currently works on GET with a query param for the file path. Should be changed to delete/post

    path('submission/<int:id>/edit', main.SubmissionEditView.as_view(), name="submission_edit"),
    path('submission/<int:id>/editfiles', main.SubmissionEditFilesView.as_view(), name="submission_editfiles"),
    path('submission/<int:id>/view', main.SubmissionReadView.as_view(), name="submission_read"),
    path('submission/<int:submission_id>/createcuration', main.CurationCreateView.as_view(), name="submission_createcuration"),
    path('submission/<int:submission_id>/createverification', main.VerificationCreateView.as_view(), name="submission_createverification"),
    path('submission/<int:submission_id>/createnote', main.edit_note, name="submission_createnote"),
    path('submission/<int:submission_id>/editnote/<int:id>', main.edit_note, name="submission_editnote"),
    path('submission/<int:submission_id>/deletenote/<int:id>', main.delete_note, name="submission_deletenote"),
    path('submission/<int:submission_id>/deletefile', main.delete_file, name="submission_deletefile"), #TODO: This currently works on GET with a query param for the file path. Should be changed to delete/post

    path('curation/<int:id>/edit', main.CurationEditView.as_view(), name="curation_edit"),
    path('curation/<int:id>/view', main.CurationReadView.as_view(), name="curation_read"),
    path('curation/<int:curation_id>/createnote', main.edit_note, name="curation_createnote"),
    path('curation/<int:curation_id>/editnote/<int:id>', main.edit_note, name="curation_editnote"),
    path('curation/<int:curation_id>/deletenote/<int:id>', main.delete_note, name="curation_deletenote"),

    path('verification/<int:id>/edit', main.VerificationEditView.as_view(), name="verification_edit"),
    path('verification/<int:id>/view', main.VerificationReadView.as_view(), name="verification_read"),
    path('verification/<int:verification_id>/createnote', main.edit_note, name="verification_createnote"),
    path('verification/<int:verification_id>/editnote/<int:id>', main.edit_note, name="verification_editnote"),
    path('verification/<int:verification_id>/deletenote/<int:id>', main.delete_note, name="verification_deletenote"),

    path('logout', users.logout_view),
    path('account_associate_oauth/<str:key>', users.account_associate_oauth),
    path('account_user_details', users.account_user_details),
]