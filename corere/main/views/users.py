import logging
from django.shortcuts import render, redirect, get_object_or_404
from guardian.decorators import permission_required_or_404
from guardian.shortcuts import get_objects_for_user, assign_perm, get_users_with_perms
from corere.main.models import Manuscript, User
from django.contrib.auth.decorators import login_required
from corere.main.forms import AuthorInviteAddForm, EditorAddForm, CuratorAddForm, VerifierAddForm, EditUserForm, UserInviteForm
from django.contrib import messages
from invitations.utils import get_invitation_model
from django.utils.crypto import get_random_string
from django.contrib.auth.models import Permission, Group
from corere.main import constants as c
from django.contrib.auth import login, logout
from django.conf import settings
from corere.main.gitlab import gitlab_create_user, gitlab_add_user_to_repo, gitlab_update_user
from notifications.signals import notify
from django.http import Http404
logger = logging.getLogger(__name__)

# Editor/Superuser enters an email into a form and clicks submit
# Corere creates a user with no auth connected, and an email address, and the requested role(s).
# Corere emails the user telling them to sign-up. This has a one-time 

# TODO: We should probably make permissions part of our constants as well
@login_required
@permission_required_or_404('main.add_authors_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True) #slightly hacky that you need add to access the remove function, but everyone with remove should be able to add
def invite_assign_author(request, id=None):
    form = AuthorInviteAddForm(request.POST or None)
    group_substring = c.GROUP_MANUSCRIPT_AUTHOR_PREFIX
    manuscript = Manuscript.objects.get(pk=id)
    manu_author_group = Group.objects.get(name=group_substring + " " + str(manuscript.id))
    can_remove_author = request.user.has_perm('remove_authors_on_manuscript')
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            users = list(form.cleaned_data['users_to_add'])

            if(email):
                author_role = Group.objects.get(name=c.GROUP_ROLE_AUTHOR) 
                new_user = helper_create_user_and_invite(request, email, author_role)
                messages.add_message(request, messages.INFO, 'You have invited {0} to CoReRe as an Author!'.format(email))
                # gitlab_add_user_to_repo(new_user, manuscript.gitlab_manuscript_id) #done below
                users.append(new_user) #add new new_user to the other users provided
            for u in users:
                manu_author_group.user_set.add(u)
                gitlab_add_user_to_repo(u, manuscript.gitlab_manuscript_id)
                messages.add_message(request, messages.INFO, 'You have given {0} author access to manuscript {1}!'.format(u.email, manuscript.title))
                logger.info('You have given {0} author access to manuscript {1}!'.format(u.email, manuscript.title))
                #Admin gave Author access to Matthew for manuscript bug5
                notification_msg = '{0} has given you author access to manuscript {1}!'.format(request.user.email, manuscript.title)
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'group_substring': group_substring, 'role_name': 'Author', 'assigned_users': manu_author_group.user_set.all(), 'can_remove_author': can_remove_author})

@login_required
@permission_required_or_404('main.remove_authors_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def unassign_author(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        group_substring = c.GROUP_MANUSCRIPT_AUTHOR_PREFIX
        manu_author_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
        try:
            user = manu_author_group.user_set.get(id=user_id)
        except User.DoesNotExist:
            logger.warn("User {0} attempted to remove user id {1} from group {2} which is invalid".format(request.user.id, user_id, group_substring))
            raise Http404()
        manu_author_group.user_set.remove(user)
        return redirect('/manuscript/'+str(id)+'/inviteassignauthor')

@login_required
@permission_required_or_404('main.manage_editors_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def assign_editor(request, id=None):
    form = EditorAddForm(request.POST or None)
    #MAD: I moved these outside... is that bad?
    manuscript = Manuscript.objects.get(pk=id)
    group_substring = c.GROUP_MANUSCRIPT_EDITOR_PREFIX
    manu_editor_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
    if request.method == 'POST':
        if form.is_valid():
            users_to_add = list(form.cleaned_data['users_to_add'])
            
            for u in users_to_add:
                manu_editor_group.user_set.add(u)
                messages.add_message(request, messages.INFO, 'You have given {0} editor access to manuscript {1}!'.format(u.email, manuscript.title))
                logger.info('You have given {0} editor access to manuscript {1}!'.format(u.email, manuscript.title))
                notification_msg = '{0} has given you editor access to manuscript {1}!'.format(request.user.email, manuscript.title)
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'group_substring': group_substring, 'role_name': 'Editor', 'assigned_users': manu_editor_group.user_set.all()})

@login_required
@permission_required_or_404('main.manage_editors_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def unassign_editor(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        group_substring = c.GROUP_MANUSCRIPT_EDITOR_PREFIX
        manu_editor_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
        try:
            user = manu_editor_group.user_set.get(id=user_id)
        except User.DoesNotExist:
            logger.warn("User {0} attempted to remove user id {1} from group {2} which is invalid".format(request.user.id, user_id, group_substring))
            raise Http404()
        manu_editor_group.user_set.remove(user)
        # print("DELETE " + str(user_id))
        return redirect('/manuscript/'+str(id)+'/assigneditor')

@login_required
@permission_required_or_404('main.manage_curators_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def assign_curator(request, id=None):
    form = CuratorAddForm(request.POST or None)
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
                notification_msg = '{0} has given you curator access to manuscript {1}!'.format(request.user.email, manuscript.title)
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'group_substring': group_substring, 'role_name': 'Curator', 'assigned_users': manu_curator_group.user_set.all()})

@login_required
@permission_required_or_404('main.manage_curators_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def unassign_curator(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        group_substring = c.GROUP_MANUSCRIPT_CURATOR_PREFIX
        manu_curator_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
        try:
            user = manu_curator_group.user_set.get(id=user_id)
        except User.DoesNotExist:
            logger.warn("User {0} attempted to remove user id {1} from group {2} which is invalid".format(request.user.id, user_id, group_substring))
            raise Http404()
        manu_curator_group.user_set.remove(user)
        return redirect('/manuscript/'+str(id)+'/assigncurator')

@login_required
@permission_required_or_404('main.manage_verifiers_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def assign_verifier(request, id=None):
    form = VerifierAddForm(request.POST or None)
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
                notification_msg = '{0} has given you verifier access to manuscript {1}!'.format(request.user.email, manuscript.title)
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'group_substring': group_substring, 'role_name': 'Verifier', 'assigned_users': manu_verifier_group.user_set.all()})

#MAD: Maybe error if id not in list (right now does nothing silently)
@login_required
@permission_required_or_404('main.manage_verifiers_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def unassign_verifier(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        group_substring = c.GROUP_MANUSCRIPT_VERIFIER_PREFIX
        manu_verifier_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
        try:
            user = manu_verifier_group.user_set.get(id=user_id)
        except User.DoesNotExist:
            logger.warn("User {0} attempted to remove user id {1} from group {2} which is invalid".format(request.user.id, user_id, group_substring))
            raise Http404()
        manu_verifier_group.user_set.remove(user)
        # print("DELETE " + str(user_id))
        return redirect('/manuscript/'+str(id)+'/assignverifier')

def account_associate_oauth(request, key=None):
    logout(request)
    user = get_object_or_404(User, invite_key=key)
    login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0]) # select a "fake" backend for our auth
    #user.username = ""
    #user.invite_key = ""

    return render(request, 'main/new_user_oauth.html')

@login_required()
def account_user_details(request):
    if(request.user.invite_key):
        #we clear out the invite_key now that we can associate the user
        #we do it regardless incase a new user clicks out of the page.
        #This is somewhat a hack to get around having to serve this page with and without header content
        request.user.invite_key = "" 
        request.user.save()
    form = EditUserForm(request.POST or None, instance=request.user)
    if request.method == 'POST':
        if form.is_valid():
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

@login_required()
def notifications(request):
    return render(request, 'main/notifications.html')

@login_required()
def invite_editor(request):
    role = Group.objects.get(name=c.GROUP_ROLE_EDITOR) 
    return invite_user_not_author(request, role, "editor")

@login_required()
def invite_curator(request):
    role = Group.objects.get(name=c.GROUP_ROLE_CURATOR) 
    return invite_user_not_author(request, role, "curator")

@login_required()
def invite_verifier(request):
    role = Group.objects.get(name=c.GROUP_ROLE_VERIFIER) 
    return invite_user_not_author(request, role, "verifier")

@login_required()
def invite_user_not_author(request, role, role_text):
    if(request.user.is_superuser):
        form = UserInviteForm(request.POST or None)
        if request.method == 'POST':
            if form.is_valid():
                email = form.cleaned_data['email']
                if(email):
                    new_user = helper_create_user_and_invite(request, email, role)
                    messages.add_message(request, messages.INFO, 'You have invited {0} to CoReRe as an {1}!'.format(email, role_text))
            else:
                logger.debug(form.errors) #TODO: DO MORE?
        return render(request, 'main/form_user_details.html', {'form': form})

    else:
        raise Http404()


def helper_create_user_and_invite(request, email, role):
    Invitation = get_invitation_model()
    invite = Invitation.create(email)#, inviter=request.user)
    #In here, we create a "starter" new_user that will later be modified and connected to auth after the invite
    new_user = User()
    new_user.email = email
    
    #Username can't be set to email as gitlab does not support those characters.
    new_user.username = get_random_string(64).lower() #required field, we enter jibberish for now
    new_user.invite_key = invite.key #to later reconnect the new_user we've created to the invite
    new_user.invited_by=request.user
    new_user.set_unusable_password()
    new_user.save()

    role.user_set.add(new_user)
    gitlab_create_user(new_user)

    #TODO: Think about doing this after everything else, incase something bombs
    invite.send_invitation(request)

    return new_user