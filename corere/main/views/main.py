from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main.models import Manuscript, Submission, Curation, Verification, Note
from corere.main import constants as c
from corere.main.views.datatables import helper_manuscript_columns, helper_submission_columns
from corere.main.forms import * #bad practice but I use them all...
from django.contrib.auth.models import Permission, Group
from guardian.shortcuts import assign_perm, remove_perm#, get_objects_for_user
from django_fsm import can_proceed#, has_transition_perm
from django.core.exceptions import PermissionDenied, FieldDoesNotExist
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
    transition_button_title = None
    form = None
    model = None
    template = 'main/form_object_generic.html'
    redirect = '/'
    parent_reference_name = None
    parent_id_name = None
    parent_model = None
    object_friendly_name = None
    read_only = False
    http_method_names = ['get', 'post']

    def dispatch(self, request, *args, **kwargs): 
        if kwargs.get('id'):
            self.obj = get_object_or_404(self.model, id=kwargs.get('id'))
            self.message = 'Your '+self.object_friendly_name +' has been updated!'
        elif not self.read_only: #kwargs.get(self.parent_id_name) and 
            self.obj = self.model()
            if(self.parent_model is not None):
                setattr(self.obj, self.parent_reference_name, get_object_or_404(self.parent_model, id=kwargs.get(self.parent_id_name)))
            self.message = 'Your new '+self.object_friendly_name +' has been created!'
        else:
            print("ERROR")
        self.form = self.form(self.request.POST or None, self.request.FILES or None, instance=self.obj)
        self.notes = []
        try:
            self.model._meta.get_field('notes')
            for note in self.obj.notes.all():
                if request.user.has_perm('view_note', note):
                    self.notes.append(note)
                else:
                    print("user did not have permission for note: " + note.text)
        except FieldDoesNotExist: #To catch models without notes (Manuscript)
            pass
        return super(GenericCorereObjectView, self).dispatch(request,*args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only })

    def post(self, request, *args, **kwargs):
        if self.form.is_valid():
            self.form.save()
            if(self.transition_button_title and request.POST['submit'] == self.transition_button_title): #This checks to see which form button was used. There is probably a more precise way to check
                self.transition_if_allowed(request, *args, **kwargs)
            messages.add_message(request, messages.INFO, self.message)
            return redirect(self.redirect)
        else:
            print(form.errors) #Handle exception better
        return render(request, self.template, {'form': self.form, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only })


    ######## Custom class functions. You will want to override some of these. #########

    # To do a tranisition on save. Different transitions are used for each object
    def transition_if_allowed(self, request, *args, **kwargs):
        pass

class ReadOnlyCorereMixin(object):
    read_only = True
    http_method_names = ['get']


################################################################################################

class ManuscriptEditView(GenericCorereObjectView):
    transition_button_title = 'Save and Assign to Authors'
    form = ManuscriptForm
    object_friendly_name = 'manuscript'
    model = Manuscript

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


class SubmissionEditView(GenericCorereObjectView):
    transition_button_title = 'Submit for Review'
    form = SubmissionForm
    
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = Manuscript
    object_friendly_name = 'submission'
    model = Submission

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


class CurationEditView(GenericCorereObjectView):
    transition_button_title = 'Submit and Progress'
    form = CurationForm
    parent_reference_name = 'submission'
    parent_id_name = "submission_id"
    parent_model = Submission
    object_friendly_name = 'curation'
    model = Curation
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


class VerificationEditView(GenericCorereObjectView):
    transition_button_title = 'Submit and Progress'
    form = VerificationForm
    parent_reference_name = 'submission'
    parent_id_name = "submission_id"
    parent_model = Submission
    object_friendly_name = 'verification'
    model = Verification
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

################################################################################################


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