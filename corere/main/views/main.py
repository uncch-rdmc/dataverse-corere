from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main.models import Manuscript, Submission, Curation, Verification, Note
from corere.main import constants as c
from corere.main.views.datatables import helper_manuscript_columns, helper_submission_columns
from corere.main.forms import * #bad practice but I use them all...
from django.contrib.auth.models import Permission, Group
from guardian.shortcuts import assign_perm, remove_perm#, get_objects_for_user
from django_fsm import can_proceed#, has_transition_perm
from django.core.exceptions import PermissionDenied
from corere.main.utils import fsm_check_transition_perm

from django.http import HttpResponse
from django.views import View

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

def view_manuscript(request, id=None):
    if id:
        manuscript = get_object_or_404(Manuscript, id=id)
        message = 'Your manuscript has been updated!'
    form = ReadOnlyManuscriptForm(instance=manuscript)
    #TODO: Add Notes
    return render(request, 'main/form_view_manuscript.html', {'form': form, 'id': id})

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
                
            messages.add_message(request, messages.INFO, message)
            return redirect('/')
        else:
            print(form.errors) #Handle exception better
    return render(request, 'main/form_create_manuscript.html', {'form': form, 'id': id})

class GenericCorereObjectView(View):
    transition_form_button_title = None
    form = None
    obj_class = None #should probably rename to make clear its not an instantiation
    template = None
    redirect = '/'
    parent_reference_name = None
    parent_id_name = None
    parent_obj_class = None #should probably rename to make clear its not an instantiation
    object_friendly_name = None
    read_only = False
    http_method_names = ['get', 'post']

    def dispatch(self, *args, **kwargs): 
        if kwargs.get('id'):
            self.obj = get_object_or_404(self.obj_class, id=kwargs.get('id'))
            self.message = 'Your '+self.object_friendly_name +' has been updated!'
        elif not self.read_only: #kwargs.get(self.parent_id_name) and 
            self.obj = self.obj_class()
            if(self.parent_obj_class is not None):
                setattr(self.obj, self.parent_reference_name, get_object_or_404(self.parent_obj_class, id=kwargs.get(self.parent_id_name)))
            self.message = 'Your new '+self.object_friendly_name +' has been created!'
        else:
            print("ERROR")
        self.form = self.form(self.request.POST or None, self.request.FILES or None, instance=self.obj)
        return super(GenericCorereObjectView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form})#, 'id': self.id})#, 'notes': notes })

    def post(self, request, *args, **kwargs):
        if self.form.is_valid():
            self.form.save()
            if(self.transition_form_button_title and request.POST['submit'] == self.transition_form_button_title): #This checks to see which form button was used. There is probably a more precise way to check
                self.transition_if_allowed(request, *args, **kwargs)
            messages.add_message(request, messages.INFO, self.message)
            return redirect(self.redirect)
        else:
            print(form.errors) #Handle exception better
        return render(request, self.template, {'form': form})#, 'id': id})#, 'notes': notes })


    ######## Custom class functions. You will want to override some of these. #########

    # To do a tranisition on save. Different transitions are used for each object
    def transition_if_allowed(self, request, *args, **kwargs):
        pass

class ReadOnlyCorereMixin(object):
    read_only = True
    http_method_names = ['get']

################################################################################################

class ManuscriptEditView(GenericCorereObjectView):
    transition_form_button_title = 'Save and Assign to Authors'
    form = ManuscriptForm
    template = 'main/form_create_manuscript.html'
    object_friendly_name = 'manuscript'
    obj_class = Manuscript

    def transition_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.obj.begin, request.user): 
            print("PermissionDenied")
            raise PermissionDenied
        try: #TODO: only do this if the reviewer selects a certain form button
            self.obj.begin()
            self.obj.save()
        except TransactionNotAllowed:
            print("TransitionNotAllowed") #Handle exception better
            raise

class ManuscriptReadView(ReadOnlyCorereMixin, ManuscriptEditView):
    form = ReadOnlyManuscriptForm
    template = 'main/form_view_manuscript.html'

class SubmissionEditView(GenericCorereObjectView):
    transition_form_button_title = 'Submit for Review'
    form = SubmissionForm
    template = 'main/form_create_submission.html'
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_obj_class = Manuscript
    object_friendly_name = 'submission'
    obj_class = Submission

    def transition_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.obj.submit, request.user): 
            print("PermissionDenied")
            raise PermissionDenied
        try: #TODO: only do this if the reviewer selects a certain form button
            self.obj.submit()
            self.obj.save()
        except TransactionNotAllowed:
            print("TransitionNotAllowed") #Handle exception better
            raise

class SubmissionReadView(ReadOnlyCorereMixin, SubmissionEditView):
    form = ReadOnlySubmissionForm
    template = 'main/form_view_submission.html'


class CurationEditView(GenericCorereObjectView):
    transition_form_button_title = 'Submit and Progress'
    form = CurationForm
    template = 'main/form_create_curation.html'
    parent_reference_name = 'submission'
    parent_id_name = "submission_id"
    parent_obj_class = Submission
    object_friendly_name = 'curation'
    obj_class = Curation
    redirect = '/'

    def transition_if_allowed(self, request, *args, **kwargs):
        # if not fsm_check_transition_perm(self.obj.submission.review, request.user): #MAD: I left this in from submission even tho it wasn't in curation... maybe remove?
        #     print("PermissionDenied")
        #     raise PermissionDenied
        try:
            self.obj.submission.review()
            self.obj.submission.save()
        except TransactionNotAllowed:
            print("Transaction Not Allowed") #MAD: Prolly remove after testing
            pass #We do not do review if the statuses don't align

class CurationReadView(ReadOnlyCorereMixin, CurationEditView):
    form = ReadOnlyCurationForm
    template = 'main/form_view_curation.html'


class VerificationEditView(GenericCorereObjectView):
    transition_form_button_title = 'Submit and Progress'
    form = VerificationForm
    template = 'main/form_create_verification.html'
    parent_reference_name = 'submission'
    parent_id_name = "submission_id"
    parent_obj_class = Submission
    object_friendly_name = 'verification'
    obj_class = Verification
    redirect = '/'

    def transition_if_allowed(self, request, *args, **kwargs):
        # if not fsm_check_transition_perm(self.obj.submission.review, request.user): #MAD: I left this in from submission even tho it wasn't in curation... maybe remove?
        #     print("PermissionDenied")
        #     raise PermissionDenied
        try:
            self.obj.submission.review()
            self.obj.submission.save()
        except TransactionNotAllowed:
            print("Transaction Not Allowed") #MAD: Prolly remove after testing
            pass #We do not do review if the statuses don't align

class VerificationReadView(ReadOnlyCorereMixin, VerificationEditView):
    form = ReadOnlyVerificationForm
    template = 'main/form_view_verification.html'

################################################################################################

def view_submission(request, manuscript_id=None, id=None):
    submission = get_object_or_404(Submission, id=id)
    form = ReadOnlySubmissionForm(instance=submission)
    notes = []
    for note in submission.submission_notes.all():
        if request.user.has_perm('view_note', note):
            notes.append(note)
        else:
            print("user did not have permission for note: " + note.text)
    return render(request, 'main/form_view_submission.html', {'form': form, 'id': id, 'notes': notes })

def edit_submission(request, manuscript_id=None, id=None):
    if id:
        submission = get_object_or_404(Submission, id=id)
        message = 'Your submission has been updated!'
    else:
        submission = Submission()
        submission.manuscript = get_object_or_404(Manuscript, id=manuscript_id)
        message = 'Your new submission has been created!'
    form = SubmissionForm(request.POST or None, request.FILES or None, instance=submission)
    notes = []
    for note in submission.submission_notes.all():
        if request.user.has_perm('view_note', note):
            notes.append(note)
        else:
            print("user did not have permission for note: " + note.text)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            if(request.POST['submit'] == 'Submit for Review'): #This checks to see which form button was used. There is probably a more precise way to check
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
    return render(request, 'main/form_create_submission.html', {'form': form, 'id': id, 'notes': notes })



def view_curation(request, submission_id=None, id=None):
    curation = get_object_or_404(Curation, id=id)
    form = ReadOnlyCurationForm(instance=curation)
    notes = []
    for note in curation.curation_notes.all():
        if request.user.has_perm('view_note', note):
            notes.append(note)
        else:
            print("user did not have permission for note: " + note.text)
    return render(request, 'main/form_view_curation.html', {'form': form, 'id': id, 'notes': notes })

def edit_curation(request, submission_id=None, id=None):
    if id:
        curation = get_object_or_404(Curation, id=id)
        message = 'Your curation has been updated!'
    else:
        curation = Curation()
        curation.submission = get_object_or_404(Submission, id=submission_id)
        message = 'Your new curation has been created!'
    form = CurationForm(request.POST or None, request.FILES or None, instance=curation)
    notes = []
    for note in curation.curation_notes.all():
        if request.user.has_perm('view_note', note):
            notes.append(note)
        else:
            print("user did not have permission for note: " + note.text)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            if(request.POST['submit'] == 'Submit and Progress'): #This checks to see which form button was used. There is probably a more precise way to check
                try:
                    curation.submission.review()
                    curation.submission.save()
                except TransactionNotAllowed:
                    pass #We do not do review if the statuses don't align

            messages.add_message(request, messages.INFO, message)
            return redirect('/')
        else:
            print(form.errors) #Handle exception better
    return render(request, 'main/form_create_curation.html', {'form': form, 'id': id, 'notes': notes})

def view_verification(request, submission_id=None, id=None):
    verification = get_object_or_404(Verification, id=id)
    form = ReadOnlyVerificationForm(instance=verification)
    notes = []
    for note in verification.verification_notes.all():
        if request.user.has_perm('view_note', note):
            notes.append(note)
        else:
            print("user did not have permission for note: " + note.text)
    return render(request, 'main/form_view_verification.html', {'form': form, 'id': id, 'notes': notes })

def edit_verification(request, submission_id=None, id=None):
    if id:
        verification = get_object_or_404(Verification, id=id)
        message = 'Your verification has been updated!'
    else:
        verification = Verification()
        verification.submission = get_object_or_404(Submission, id=submission_id)
        message = 'Your new verification has been created!'
    form = VerificationForm(request.POST or None, request.FILES or None, instance=verification)
    notes = []
    for note in verification.verification_notes.all():
        if request.user.has_perm('view_note', note):
            notes.append(note)
        else:
            print("user did not have permission for note: " + note.text)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            if(request.POST['submit'] == 'Submit and Progress'): #This checks to see which form button was used. There is probably a more precise way to check
                try: 
                    verification.submission.review()
                    verification.submission.save()
                except TransactionNotAllowed:
                    pass #We do not do review if the statuses don't align

            messages.add_message(request, messages.INFO, message)
            return redirect('/')
        else:
            print(form.errors) #Handle exception better
    return render(request, 'main/form_create_verification.html', {'form': form, 'id': id, 'notes': notes})

def edit_note(request, id=None, submission_id=None, curation_id=None, verification_id=None):
    if id:
        note = get_object_or_404(Note, id=id)
        message = 'Your note has been updated!'
        re_url = '../edit'
    else:
        note = Note()
        if(submission_id):
            note.parent_submission = get_object_or_404(Submission, id=submission_id)
        elif(curation_id):
            note.parent_curation = get_object_or_404(Curation, id=curation_id)
        elif(verification_id):
            note.parent_verification = get_object_or_404(Verification, id=verification_id)
        message = 'Your new note has been created!'
        re_url = './edit'
    form = NoteForm(request.POST or None, request.FILES or None, instance=note)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            #We go through all available role-groups and add/remove their permissions depending on whether they were selected
            #TODO move to actual model save?
            for role in c.get_roles():
                group = Group.objects.get(name=role)
                if role in form.cleaned_data['scope']:
                    assign_perm('view_note', group, note) 
                else:
                    remove_perm('view_note', group, note)           
            #user always has full permissions to their own note
            assign_perm('view_note', request.user, note) 
            assign_perm('change_note', request.user, note) 
            assign_perm('delete_note', request.user, note) 
            return redirect(re_url)
        else:
            print(form.errors) #Handle exception better

    return render(request, 'main/form_create_note.html', {'form': form})

def delete_note(request, id=None, submission_id=None, curation_id=None, verification_id=None):
    note = get_object_or_404(Note, id=id)
    note.delete()
    return redirect('../edit')