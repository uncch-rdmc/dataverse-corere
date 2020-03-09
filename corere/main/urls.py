from django.urls import path

from corere.main.views import datatables, main, users

urlpatterns = [ 
    path('', main.index),
    path('manuscript_table', datatables.ManuscriptJson.as_view(), name="manuscript_table"),
    path('manuscript/<int:manuscript_id>/submission_table', datatables.SubmissionJson.as_view(), name="submission_table"),
    path('manuscript/create', main.edit_manuscript),
    path('manuscript/<int:id>/edit', main.edit_manuscript),
    path('manuscript/<int:id>/view', main.view_manuscript),
    path('manuscript/<int:id>/addauthor', users.add_author),
    path('manuscript/<int:id>/addcurator', users.add_curator),
    path('manuscript/<int:id>/deletecurator/<int:user_id>', users.delete_curator),
    path('manuscript/<int:id>/addverifier', users.add_verifier),
    path('manuscript/<int:id>/deleteverifier/<int:user_id>', users.delete_verifier),
    path('manuscript/<int:manuscript_id>/createsubmission', main.edit_submission),

    path('submission/<int:id>/edit', main.edit_submission),
    path('submission/<int:id>/view', main.view_submission),
    path('submission/<int:submission_id>/createcuration', main.edit_curation),
    path('submission/<int:submission_id>/createverification', main.edit_verification),
    path('submission/<int:submission_id>/createnote', main.edit_note),
    path('submission/<int:submission_id>/editnote/<int:id>', main.edit_note),
    path('submission/<int:submission_id>/deletenote/<int:id>', main.delete_note),

    path('curation/<int:id>/edit', main.edit_curation),
    path('curation/<int:id>/view', main.view_curation),
    path('curation/<int:curation_id>/createnote', main.edit_note),
    path('curation/<int:curation_id>/editnote/<int:id>', main.edit_note),
    path('curation/<int:curation_id>/deletenote/<int:id>', main.delete_note),

    path('verification/<int:id>/edit', main.edit_verification),
    path('verification/<int:id>/view', main.view_verification),
    path('verification/<int:verification_id>/createnote', main.edit_note),
    path('verification/<int:verification_id>/editnote/<int:id>', main.edit_note),
    path('verification/<int:verification_id>/deletenote/<int:id>', main.delete_note),

    path('logout', users.logout_view),
    path('account_associate_oauth/<str:key>', users.account_associate_oauth),
    path('account_user_details', users.account_user_details),

    path('test', main.CurationView.as_view()),
    path('testsub/<int:id>/edit',main.SubmissionEditView.as_view()),
    path('testsub/<int:id>/view',main.SubmissionReadView.as_view()),
    path('testsub/<int:manuscript_id>/createsubmission',main.SubmissionEditView.as_view()),
    path('testcur/<int:id>/edit',main.CurationEditView.as_view()),
    path('testcur/<int:id>/view',main.CurationReadView.as_view()),
    path('testcur/<int:submission_id>/createcuration',main.CurationEditView.as_view())
]