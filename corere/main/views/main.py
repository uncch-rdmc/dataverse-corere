from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main.models import Manuscript, Submission, Curation, Verification
from corere.main import constants as c
from corere.main.views.datatables import helper_manuscript_columns, helper_submission_columns
from corere.main.forms import ManuscriptForm, SubmissionForm, CurationForm, VerificationForm
from django.contrib.auth.models import Permission, Group
from guardian.shortcuts import assign_perm#, get_objects_for_user
from django_fsm import can_proceed#, has_transition_perm
from django.core.exceptions import PermissionDenied
from corere.main.utils import fsm_check_transition_perm

def index(request):
    if request.user.is_authenticated:
        if(request.user.invite_key): #user hasn't finished signing up if we are still holding their key
            return redirect("/account_user_details")
        else:
            args = {'user':     request.user, 
                    'manuscript_columns':  helper_manuscript_columns(request.user),
                    'submission_columns':  helper_submission_columns(request.user),
                    'GROUP_ROLE_EDITOR': c.GROUP_ROLE_EDITOR,
                    'GROUP_ROLE_AUTHOR': c.GROUP_ROLE_AUTHOR,
                    'GROUP_ROLE_VERIFIER': c.GROUP_ROLE_VERIFIER,
                    'GROUP_ROLE_CURATOR': c.GROUP_ROLE_CURATOR,
                    }
            return render(request, "main/index.html", args)
    else:
        return render(request, "main/login.html")

#Maybe someday we should used class-based views
#MAD: This decorator gets in the way of creation. We need to do it inside
#@permission_required_or_403('main.change_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def edit_manuscript(request, id=None):
    if id:
        manuscript = get_object_or_404(Manuscript, id=id)
        message = 'Your manuscript has been updated!'
    else:
        manuscript = Manuscript()
        message = 'Your new manuscript has been created!'
    form = ManuscriptForm(request.POST or None, request.FILES or None, instance=manuscript)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            if(request.POST['submit'] == 'Save and Assign to Authors'): #This checks to see which form button was used. There is probably a more precise way to check
                #print(request.user.groups.filter(name='c.GROUP_ROLE_VERIFIER').exists())
                print("main has_transition_perm")
                print(fsm_check_transition_perm(manuscript.begin, request.user))
                if not fsm_check_transition_perm(manuscript.begin, request.user): 
                    print("PermissionDenied")
                    raise PermissionDenied
                try:
                    manuscript.begin()
                    manuscript.save()
                except TransactionNotAllowed:
                    print("TransitionNotAllowed") #Handle exception better
                    raise
            if not id: # if create
                # Note these works alongside global permissions defined in signals.py
                # TODO: Make this concatenation standardized
                group_manuscript_editor, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(manuscript.id))
                assign_perm('change_manuscript', group_manuscript_editor, manuscript) 
                assign_perm('delete_manuscript', group_manuscript_editor, manuscript) 
                assign_perm('view_manuscript', group_manuscript_editor, manuscript) 
                assign_perm('manage_authors_on_manuscript', group_manuscript_editor, manuscript) 

                group_manuscript_author, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(manuscript.id))
                assign_perm('change_manuscript', group_manuscript_author, manuscript)
                assign_perm('view_manuscript', group_manuscript_author, manuscript) 
                assign_perm('manage_authors_on_manuscript', group_manuscript_author, manuscript) 
                assign_perm('add_submission_to_manuscript', group_manuscript_author, manuscript) 

                group_manuscript_verifier, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id))
                assign_perm('change_manuscript', group_manuscript_verifier, manuscript) 
                assign_perm('view_manuscript', group_manuscript_verifier, manuscript) 
                assign_perm('curate_manuscript', group_manuscript_verifier, manuscript) 

                group_manuscript_curator, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id))
                assign_perm('change_manuscript', group_manuscript_curator, manuscript) 
                assign_perm('view_manuscript', group_manuscript_curator, manuscript) 
                assign_perm('verify_manuscript', group_manuscript_verifier, manuscript) 

                group_manuscript_editor.user_set.add(request.user) #TODO: Should be dynamic on role, but right now only editors create manuscripts
                
            messages.add_message(request, messages.INFO, message)
            return redirect('/')
        else:
            print(form.errors) #Handle exception better
    return render(request, 'main/form_create_manuscript.html', {'form': form, 'id': id})

def edit_submission(request, manuscript_id=None, id=None):
    if id:
        submission = get_object_or_404(Submission, id=id)
        message = 'Your submission has been updated!'
    else:
        submission = Submission()
        submission.manuscript = get_object_or_404(Manuscript, id=manuscript_id)
        message = 'Your new submission has been created!'
    form = SubmissionForm(request.POST or None, request.FILES or None, instance=submission)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            
            if not fsm_check_transition_perm(submission.submit, request.user): 
                print("PermissionDenied")
                raise PermissionDenied
            try: #TODO: only do this if the reviewer selects a certain form button
                submission.submit()
                submission.save()
            except TransactionNotAllowed:
                print("TransitionNotAllowed") #Handle exception better
                raise

            messages.add_message(request, messages.INFO, message)
            return redirect('/')
        else:
            print(form.errors) #Handle exception better
    return render(request, 'main/form_create_submission.html', {'form': form, 'id': id})

def edit_curation(request, submission_id=None, id=None):
    if id:
        curation = get_object_or_404(Curation, id=id)
        message = 'Your curation has been updated!'
    else:
        curation = Curation()
        curation.submission = get_object_or_404(Submission, id=submission_id)
        message = 'Your new curation has been created!'
    form = CurationForm(request.POST or None, request.FILES or None, instance=curation)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            try:
                curation.submission.review()
                curation.submission.save()
            except TransactionNotAllowed:
                pass #We do not do review if the statuses don't align

            messages.add_message(request, messages.INFO, message)
            return redirect('/')
        else:
            print(form.errors) #Handle exception better
    return render(request, 'main/form_create_curation.html', {'form': form, 'id': id})

def edit_verification(request, submission_id=None, id=None):
    if id:
        verification = get_object_or_404(Verification, id=id)
        message = 'Your verification has been updated!'
    else:
        verification = Verification()
        verification.submission = get_object_or_404(Submission, id=submission_id)
        message = 'Your new verification has been created!'
    form = VerificationForm(request.POST or None, request.FILES or None, instance=verification)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            try: #TODO: only do this if the reviewer selects a certain form button
                verification.submission.review()
                verification.submission.save()
            except TransactionNotAllowed:
                pass #We do not do review if the statuses don't align

            messages.add_message(request, messages.INFO, message)
            return redirect('/')
        else:
            print(form.errors) #Handle exception better
    return render(request, 'main/form_create_verification.html', {'form': form, 'id': id})