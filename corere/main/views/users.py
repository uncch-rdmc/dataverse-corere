from django.shortcuts import render, redirect, get_object_or_404
from guardian.decorators import permission_required_or_403
from guardian.shortcuts import get_objects_for_user, assign_perm
from corere.main.models import Manuscript, User
from django.contrib.auth.decorators import login_required
from corere.main.forms import InvitationForm, NewUserForm
from django.contrib import messages
from invitations.utils import get_invitation_model
from django.utils.crypto import get_random_string
from django.contrib.auth.models import Permission, Group
from corere.main import constants as c
from django.contrib.auth import login, logout
from django.conf import settings

# Editor/Superuser enters an email into a form and clicks submit
# Corere creates a user with no auth connected, and an email address, and the requested role(s).
# Corere emails the user telling them to sign-up. This has a one-time 

# TODO: We should probably make permissions part of our constants as well
@permission_required_or_403('main.manage_authors_on_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
def add_user(request, id=None):
    form = InvitationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            users = list(form.cleaned_data['existing_users'])

            if(email):
                Invitation = get_invitation_model()
                invite = Invitation.create(email)#, inviter=request.user)
                #In here, we create a "starter" user that will later be modified and connected to auth after the invite
                user = User()
                user.email = email
                user.username = get_random_string(64).lower() #required field, we enter jibberish for now
                user.is_author = True  #TODO: This need to be dynamic depending on roles selected.
                user.invite_key = invite.key #to later reconnect the user we've created to the invite
                user.invited_by=request.user
                user.set_unusable_password()
                user.save()
                author_group = Group.objects.get(name=c.GROUP_ROLE_AUTHOR) 
                author_group.user_set.add(user)
                users.append(user) #add new user to the other uses provided

                #TODO: Think about doing this after everything else, incase something bombs
                invite.send_invitation(request)
                messages.add_message(request, messages.INFO, 'You have invited {0} to CoReRe!'.format(email))
            
            manuscript = Manuscript.objects.get(pk=id)
            for u in users:
                assign_perm('main.manage_authors_on_manuscript', u, manuscript)
                assign_perm('main.view_manuscript', u, manuscript)
                messages.add_message(request, messages.INFO, 'You have given {0} access to manuscript {1}!'.format(u.email, manuscript.title))

            return redirect('/')
        else:
            print(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_initialize_user.html', {'form': form})

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
            form.save()
            return redirect('/')
        else:
            print(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_user_details.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.add_message(request, messages.INFO, 'You have succesfully logged out!')
    return redirect('/')