import logging
from django.shortcuts import render, redirect, get_object_or_404
from guardian.decorators import permission_required_or_404
from guardian.shortcuts import get_objects_for_user, assign_perm, get_users_with_perms
from corere.main.models import Manuscript, User
from django.contrib.auth.decorators import login_required
from corere.main.forms import AuthorInvitationForm, CuratorInvitationForm, VerifierInvitationForm, NewUserForm
from django.contrib import messages
from invitations.utils import get_invitation_model
from django.utils.crypto import get_random_string
from django.contrib.auth.models import Permission, Group
from corere.main import constants as c
from django.contrib.auth import login, logout
from django.conf import settings
from corere.main.gitlab import gitlab_create_user, gitlab_add_user_to_repo, gitlab_update_user
logger = logging.getLogger(__name__)

# Editor/Superuser enters an email into a form and clicks submit
# Corere creates a user with no auth connected, and an email address, and the requested role(s).
# Corere emails the user telling them to sign-up. This has a one-time 

# TODO: We should probably make permissions part of our constants as well
@login_required
@permission_required_or_404('main.manage_authors_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def add_author(request, id=None):
    form = AuthorInvitationForm(request.POST or None)
    group_substring = c.GROUP_MANUSCRIPT_AUTHOR_PREFIX
    manuscript = Manuscript.objects.get(pk=id)
    manu_author_group = Group.objects.get(name=group_substring + " " + str(manuscript.id))
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            users = list(form.cleaned_data['users_to_add'])

            if(email):
                Invitation = get_invitation_model()
                invite = Invitation.create(email)#, inviter=request.user)
                #In here, we create a "starter" new_user that will later be modified and connected to auth after the invite
                new_user = User()
                new_user.email = email
                new_user.username = get_random_string(64).lower() #required field, we enter jibberish for now
                new_user.is_author = True  #TODO: This need to be dynamic depending on roles selected.
                new_user.invite_key = invite.key #to later reconnect the new_user we've created to the invite
                new_user.invited_by=request.user
                new_user.set_unusable_password()
                new_user.save()
                author_role = Group.objects.get(name=c.GROUP_ROLE_AUTHOR) 
                author_role.user_set.add(new_user)
                users.append(new_user) #add new new_user to the other uses provided
                gitlab_create_user(new_user)
#TODO: Is this the right place to set these? Maybe better in a general save method???
                gitlab_add_user_to_repo(new_user, manuscript.gitlab_manuscript_id)
                #TODO: Think about doing this after everything else, incase something bombs
                invite.send_invitation(request)
                messages.add_message(request, messages.INFO, 'You have invited {0} to CoReRe!'.format(email))
            
            for u in users:
                manu_author_group.user_set.add(u)
                gitlab_add_user_to_repo(u, manuscript.gitlab_manuscript_id)
                messages.add_message(request, messages.INFO, 'You have given {0} author access to manuscript {1}!'.format(u.email, manuscript.title))
                logger.info('You have given {0} author access to manuscript {1}!'.format(u.email, manuscript.title))
                
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_initialize_user.html', {'form': form, 'id': id, 'group_substring': group_substring, 'role_name': 'Author', 'users': manu_author_group.user_set.all()})

@login_required
@permission_required_or_404('main.manage_curators_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def add_curator(request, id=None):
    form = CuratorInvitationForm(request.POST or None)
    #MAD: I moved these outside... is that bad?
    manuscript = Manuscript.objects.get(pk=id)
    group_substring = c.GROUP_MANUSCRIPT_CURATOR_PREFIX
    manu_curator_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
    if request.method == 'POST':
        if form.is_valid():
            users_to_add = list(form.cleaned_data['users_to_add'])
            
            for u in users_to_add:
                manu_curator_group.user_set.add(u)
                messages.add_message(request, messages.INFO, 'You have given {0} curator access to manuscript {1}!'.format(u.email, manuscript.title))
                logger.info('You have given {0} curator access to manuscript {1}!'.format(u.email, manuscript.title))
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_initialize_user.html', {'form': form, 'id': id, 'group_substring': group_substring, 'role_name': 'Curator', 'users': manu_curator_group.user_set.all()})

#MAD: Should this only work on post? Should it display confirmation?
#MAD: Maybe error if id not in list (right now does nothing silently)
@login_required
@permission_required_or_404('main.manage_curators_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def delete_curator(request, id=None, user_id=None):
    manuscript = Manuscript.objects.get(pk=id)
    group_substring = c.GROUP_MANUSCRIPT_CURATOR_PREFIX
    manu_curator_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
    user = User.objects.get(id=user_id)
    manu_curator_group.user_set.remove(user)
    # print("DELETE " + str(user_id))
    return redirect('/manuscript/'+str(id)+'/addcurator')
    #from django.http import HttpResponse
    #return HttpResponse("DELETE " + str(user_id))

@login_required
@permission_required_or_404('main.manage_verifiers_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def add_verifier(request, id=None):
    form = VerifierInvitationForm(request.POST or None)
    #MAD: I moved these outside... is that bad?
    manuscript = Manuscript.objects.get(pk=id)
    group_substring = c.GROUP_MANUSCRIPT_VERIFIER_PREFIX
    manu_verifier_group = Group.objects.get(name=group_substring + " " + str(manuscript.id))
    if request.method == 'POST':
        if form.is_valid():
            users = list(form.cleaned_data['users_to_add'])
            
            for u in users:
                manu_verifier_group.user_set.add(u)
                messages.add_message(request, messages.INFO, 'You have given {0} verifier access to manuscript {1}!'.format(u.email, manuscript.title))
                logger.info('You have given {0} verifier access to manuscript {1}!'.format(u.email, manuscript.title))
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_initialize_user.html', {'form': form, 'id': id, 'group_substring': group_substring, 'role_name': 'Verifier', 'users': manu_verifier_group.user_set.all()})

#MAD: Should this only work on post? Should it display confirmation?
#MAD: Maybe error if id not in list (right now does nothing silently)
@login_required
@permission_required_or_404('main.manage_verifiers_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def delete_verifier(request, id=None, user_id=None):
    manuscript = Manuscript.objects.get(pk=id)
    group_substring = c.GROUP_MANUSCRIPT_VERIFIER_PREFIX
    manu_verifier_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
    user = User.objects.get(id=user_id)
    manu_verifier_group.user_set.remove(user)
    # print("DELETE " + str(user_id))
    return redirect('/manuscript/'+str(id)+'/addverifier')

def account_associate_oauth(request, key=None):
    logout(request)
    user = get_object_or_404(User, invite_key=key)
    login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0]) # select a "fake" backend for our auth
    user.username = ""
    user.invite_key = ""

    return render(request, 'main/new_user_oauth.html')

@login_required()
def account_user_details(request):
    form = NewUserForm(request.POST or None, instance=request.user)
    if request.method == 'POST':
        if form.is_valid():
            if(request.user.invite_key):
                request.user.invite_key = "" #we clear out the invite_key now that we can associate the user
            user = form.save()
            gitlab_update_user(user)
            messages.add_message(request, messages.SUCCESS, "User info has been updated!")
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_user_details.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.add_message(request, messages.INFO, 'You have succesfully logged out!')
    return redirect('/')
