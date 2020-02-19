from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main.models import Manuscript
from corere.main import constants as c
from corere.main.views.datatables import helper_manuscript_columns, helper_submission_columns
from corere.main.forms import ManuscriptForm
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
            #TODO: write own context processor to pass repeatedly-used constants, etc
            #https://stackoverflow.com/questions/433162/can-i-access-constants-in-settings-py-from-templates-in-django
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

#TODO: Turn these into class-based views?
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
            if('submit_and_update_status' in request.POST): #This checks to see which form button was used. There is probably a more precise way to check
                #print(request.user.groups.filter(name='c.GROUP_ROLE_VERIFIER').exists())
                print("main has_transition_perm")
                print(fsm_check_transition_perm(manuscript.begin, request.user))
                if not fsm_check_transition_perm(manuscript.begin, request.user): 
                    print("PermissionDenied")
                    raise PermissionDenied
                try:
                    manuscript.begin()
                except TransactionNotAllowed:
                    #TODO: Do something better
                    print("TransitionNotAllowed")
                    raise
                manuscript.save()
            if not id:
                # TODO: MAke this concatenation standardized
                group_manuscript_editor, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(manuscript.id))
                assign_perm('add_manuscript', group_manuscript_editor, manuscript) #does add even do anything on an object level?
                assign_perm('change_manuscript', group_manuscript_editor, manuscript) 
                assign_perm('delete_manuscript', group_manuscript_editor, manuscript) 
                assign_perm('view_manuscript', group_manuscript_editor, manuscript) 
                assign_perm('manage_authors_on_manuscript', group_manuscript_editor, manuscript) 
                group_manuscript_author, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(manuscript.id))
                assign_perm('change_manuscript', group_manuscript_author, manuscript) # TODO: Remove?
                assign_perm('view_manuscript', group_manuscript_author, manuscript) 
                assign_perm('manage_authors_on_manuscript', group_manuscript_author, manuscript) 
                group_manuscript_verifier, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id))
                assign_perm('change_manuscript', group_manuscript_verifier, manuscript) 
                assign_perm('view_manuscript', group_manuscript_verifier, manuscript) 
                group_manuscript_curator, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id))
                # TODO: Should curators always get all this, or is this a superuser thing?
                assign_perm('add_manuscript', group_manuscript_curator, manuscript) #does add even do anything on an object level?
                assign_perm('change_manuscript', group_manuscript_curator, manuscript) 
                assign_perm('delete_manuscript', group_manuscript_curator, manuscript) 
                assign_perm('view_manuscript', group_manuscript_curator, manuscript) 
                assign_perm('manage_authors_on_manuscript', group_manuscript_curator, manuscript) 

                group_manuscript_editor.user_set.add(request.user) #TODO: Make this dynamic based upon the ROLE_GROUPs the user has
                
            messages.add_message(request, messages.INFO, message)
            return redirect('/')
        else:
            print(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_create_manuscript.html', {'form': form, 'id': id})