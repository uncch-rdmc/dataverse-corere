import logging
from django.shortcuts import render, redirect, get_object_or_404
from guardian.decorators import permission_required_or_404
from guardian.shortcuts import get_objects_for_user, assign_perm, get_users_with_perms
from corere.main.models import Manuscript, User, CorereInvitation
from django.contrib.auth.decorators import login_required
from corere.main.forms import AuthorAddForm, UserByRoleAddFormHelper, AuthorInviteAddForm, EditorAddForm, CuratorAddForm, VerifierAddForm, EditUserForm, UserInviteForm
from django.contrib import messages
from invitations.utils import get_invitation_model
from django.utils.crypto import get_random_string
from django.contrib.auth.models import Permission, Group
from corere.main import constants as c
from django.contrib.auth import login, logout
from django.conf import settings
from notifications.signals import notify
from django.http import Http404
from corere.main.templatetags.auth_extras import has_group
from corere.main.utils import fsm_check_transition_perm, generate_progress_bar_html
from django.utils.translation import gettext as _
from django.db import IntegrityError
from templated_email import send_templated_mail
logger = logging.getLogger(__name__)

# Editor/Superuser enters an email into a form and clicks submit
# Corere creates a user with no auth connected, and an email address, and the requested role(s).
# Corere emails the user telling them to sign-up. This has a one-time 

# TODO: We should probably make permissions part of our constants as well


@login_required
# @permission_required_or_404(c.perm_path(c.PERM_MANU_ADD_AUTHORS), (Manuscript, 'id', 'id'), accept_global_perms=True) #slightly hacky that you need add to access the remove function, but everyone with remove should be able to add
@permission_required_or_404(c.perm_path(c.PERM_MANU_CURATE), (Manuscript, 'id', 'id'), accept_global_perms=True)
def invite_assign_author(request, id=None):
    group_substring = c.GROUP_MANUSCRIPT_AUTHOR_PREFIX
    form = AuthorInviteAddForm(request.POST or None)
    manuscript = Manuscript.objects.get(pk=id)
    page_title = _("user_assignAuthor_pageTitle")
    page_help_text = _("user_assignAuthor_helpText")

    # if(manuscript.is_complete()): #or not(request.user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists() or request.user.is_superuser)):
    #     raise Http404()

    manu_author_group = Group.objects.get(name__startswith=group_substring + " " + str(manuscript.id))
    can_remove_author = request.user.has_any_perm(c.PERM_MANU_REMOVE_AUTHORS, manuscript)
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            users = list(form.cleaned_data['users_to_add']) 
            new_user = ''
            if(email):
                author_role = Group.objects.get(name=c.GROUP_ROLE_AUTHOR) 
                try:
                    new_user = helper_create_user_and_invite(request, email, author_role)
                    # msg = _("user_inviteRole_banner").format(email=email, role="author")
                    # messages.add_message(request, messages.INFO, msg)
                    users.append(new_user) #add new new_user to the other users provided
                except IntegrityError: #If user entered in email field already exists
                    user = User.objects.get(email=email)
                    users.append(user)
            for u in users:
                if(not u.groups.filter(name=c.GROUP_ROLE_AUTHOR).exists()):
                    logger.warn("User {0} attempted to add user id {1} from group {2} when they don't have the base role (probably by hacking the form)".format(request.user.id, u.id, group_substring))
                    raise Http404()
                manu_author_group.user_set.add(u)
                
                ### Messaging ###
                msg = _("user_addAsRoleToManuscript_banner").format(role="author", email=u.email, manuscript_title=manuscript.title)
                logger.info(msg)
                messages.add_message(request, messages.INFO, msg)
                notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="author", email=request.user.email, manuscript_title=manuscript.title)
                if(u != new_user):
                    notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
                    send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_email':u.email} )
                ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_AUTHOR, group_substring), 'manuscript_title': manuscript.title,
        'group_substring': group_substring, 'role_name': 'Author', 'assigned_users': manu_author_group.user_set.all(), 'can_remove_author': can_remove_author, 'page_title': page_title, 'page_help_text': page_help_text})

#Called during initial manuscript creation
@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_ADD_AUTHORS), (Manuscript, 'id', 'id'), accept_global_perms=True) #slightly hacky that you need add to access the remove function, but everyone with remove should be able to add
def add_author(request, id=None):
    group_substring = c.GROUP_MANUSCRIPT_AUTHOR_PREFIX
    manuscript = Manuscript.objects.get(pk=id)
    page_title = _("user_assignAuthor_pageTitle")
    page_help_text = _("user_assignAuthor_helpText")
    helper = UserByRoleAddFormHelper()
    form_initial = {'first_name':manuscript.contact_first_name, 'last_name':manuscript.contact_last_name, 'email':manuscript.contact_email}
    form = AuthorAddForm(request.POST or None, initial=form_initial)

    if(manuscript.is_complete()):
        raise Http404()
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            author_role = Group.objects.get(name=c.GROUP_ROLE_AUTHOR) 
            try:
                user = User.objects.get(email=email)
                author_role.user_set.add(user)
                new_user = False
                #assign role
            except User.DoesNotExist:
                new_user = True
                user = helper_create_user_and_invite(request, email, first_name, last_name, author_role)

            manu_author_group = Group.objects.get(name=group_substring + " " + str(manuscript.id))
            manu_author_group.user_set.add(user)
  
            if not fsm_check_transition_perm(manuscript.begin, request.user): 
                logger.debug("PermissionDenied")
                raise Http404()
            manuscript.begin()
            manuscript.save()

            ### Messaging ###
            msg = _("user_addAsRoleToManuscript_banner").format(role="author", email=user.email, manuscript_title=manuscript.title)
            logger.info(msg.format(user.email, manuscript.title))
            messages.add_message(request, messages.INFO, msg)
            notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="author", email=request.user.email, manuscript_title=manuscript.title)
            if(not new_user):
                notify.send(request.user, verb='assigned', recipient=user, target=manuscript, public=False, description=notification_msg)
                send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[user.email], context={ 'notification_msg':notification_msg, 'user_email':user.email} )

            msg = _("manuscript_submitted_banner").format(manuscript_title=manuscript.title, manuscript_id=manuscript.id)
            messages.add_message(request, messages.INFO, msg)
            ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))

        else:
            logger.debug(form.errors) #TODO: DO MORE?

    progress_list = c.progress_list_manuscript
    progress_bar_html = generate_progress_bar_html(progress_list, 'Invite Author')

    return render(request, 'main/form_add_author.html', {'form': form, 'helper': helper,  'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_AUTHOR, group_substring), 
        'group_substring': group_substring, 'role_name': 'Author', 'manuscript_title': manuscript.title, 'page_title': page_title, 'page_help_text': page_help_text, 'progress_bar_html': progress_bar_html})


@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_REMOVE_AUTHORS), (Manuscript, 'id', 'id'), accept_global_perms=True)
def unassign_author(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        if(manuscript.is_complete()):
            raise Http404()
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
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_EDITORS), (Manuscript, 'id', 'id'), accept_global_perms=True)
def assign_editor(request, id=None):
    form = EditorAddForm(request.POST or None)
    page_title = _("user_assignEditor_pageTitle")
    manuscript = Manuscript.objects.get(pk=id)
    if(manuscript.is_complete()):
        raise Http404()
    group_substring = c.GROUP_MANUSCRIPT_EDITOR_PREFIX
    manu_editor_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
    if request.method == 'POST':
        if form.is_valid():
            users_to_add = list(form.cleaned_data['users_to_add'])
            
            for u in users_to_add:
                if(not u.groups.filter(name=c.GROUP_ROLE_EDITOR).exists()):
                    logger.warn("User {0} attempted to add user id {1} from group {2} when they don't have the base role (probably by hacking the form".format(request.user.id, u.id, group_substring))
                    raise Http404()
                manu_editor_group.user_set.add(u)

                ### Messaging ###
                msg = _("user_addAsRoleToManuscript_banner").format(role="editor", email=u.email, manuscript_title=manuscript.title)
                messages.add_message(request, messages.INFO, msg)
                logger.info(msg)
                notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="editor", email=request.user.email, manuscript_title=manuscript.title)
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
                send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_email':u.email} )
                ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_EDITOR, group_substring), 
        'group_substring': group_substring, 'role_name': 'Editor', 'assigned_users': manu_editor_group.user_set.all(), 'manuscript_title': manuscript.title, 'page_title': page_title})

@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_EDITORS), (Manuscript, 'id', 'id'), accept_global_perms=True)
def unassign_editor(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        if(manuscript.is_complete()):
            raise Http404()
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
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_CURATORS), (Manuscript, 'id', 'id'), accept_global_perms=True)
def assign_curator(request, id=None):
    form = CuratorAddForm(request.POST or None)
    page_title = _("user_assignCurator_pageTitle")
    manuscript = Manuscript.objects.get(pk=id)
    if(manuscript.is_complete()):
        raise Http404()
    group_substring = c.GROUP_MANUSCRIPT_CURATOR_PREFIX
    manu_curator_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
    if request.method == 'POST':
        if form.is_valid():
            users_to_add = list(form.cleaned_data['users_to_add'])
            
            for u in users_to_add:
                if(not u.groups.filter(name=c.GROUP_ROLE_CURATOR).exists()):
                    logger.warn("User {0} attempted to add user id {1} from group {2} when they don't have the base role (probably by hacking the form".format(request.user.id, u.id, group_substring))
                    raise Http404()
                manu_curator_group.user_set.add(u)

                ### Messaging ###
                msg = _("user_addAsRoleToManuscript_banner").format(role="curator", email=u.email, manuscript_title=manuscript.title)
                messages.add_message(request, messages.INFO, msg)
                logger.info(msg)
                notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="curator", email=request.user.email, manuscript_title=manuscript.title)
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
                send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_email':u.email} )
                ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_CURATOR, group_substring),
        'group_substring': group_substring, 'role_name': 'Curator', 'assigned_users': manu_curator_group.user_set.all(), 'manuscript_title': manuscript.title, 'page_title': page_title})

@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_CURATORS), (Manuscript, 'id', 'id'), accept_global_perms=True)
def unassign_curator(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        if(manuscript.is_complete()):
            raise Http404()
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
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_VERIFIERS), (Manuscript, 'id', 'id'), accept_global_perms=True)
def assign_verifier(request, id=None):
    form = VerifierAddForm(request.POST or None)
    page_title = _("user_assignVerifier_pageTitle")
    manuscript = Manuscript.objects.get(pk=id)
    if(manuscript.is_complete()):
        raise Http404()
    group_substring = c.GROUP_MANUSCRIPT_VERIFIER_PREFIX
    manu_verifier_group = Group.objects.get(name=group_substring + " " + str(manuscript.id))
    if request.method == 'POST':
        if form.is_valid():
            users = list(form.cleaned_data['users_to_add'])
            
            for u in users:
                if(not u.groups.filter(name=c.GROUP_ROLE_VERIFIER).exists()):
                    logger.warn("User {0} attempted to add user id {1} from group {2} when they don't have the base role (probably by hacking the form".format(request.user.id, u.id, group_substring))
                    raise Http404()
                manu_verifier_group.user_set.add(u)

                ### Messaging ###
                msg = _("user_addAsRoleToManuscript_banner").format(role="verifier", email=u.email, manuscript_title=manuscript.title)
                messages.add_message(request, messages.INFO, msg)
                logger.info(msg)
                notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="verifier", email=request.user.email, manuscript_title=manuscript.title)
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
                send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_email':u.email} )
                ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_VERIFIER, group_substring),
        'group_substring': group_substring, 'role_name': 'Verifier', 'assigned_users': manu_verifier_group.user_set.all(), 'manuscript_title': manuscript.title, 'page_title': page_title})

#MAD: Maybe error if id not in list (right now does nothing silently)
@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_VERIFIERS), (Manuscript, 'id', 'id'), accept_global_perms=True)
def unassign_verifier(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        if(manuscript.is_complete()):
            raise Http404()
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
    page_title = _("user_accountDetails_pageTitle")
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
            msg = _("user_infoUpdated_banner")
            messages.add_message(request, messages.SUCCESS, msg)
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_user_details.html', {'form': form, 'page_title': page_title})

def logout_view(request):
    logout(request)
    msg = _("user_loggedOut_banner")
    messages.add_message(request, messages.INFO, msg)
    return redirect('/')

@login_required()
def notifications(request):
    return render(request, 'main/notifications.html', 
        {'page_title': _("notifications_pageTitle")})

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
    if(has_group(request.user, c.GROUP_ROLE_CURATOR)):
        form = UserInviteForm(request.POST or None)
        helper = UserByRoleAddFormHelper()
        if request.method == 'POST':
            if form.is_valid():
                email = form.cleaned_data['email']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']
                
                ### Messaging ###
                msg = _("user_inviteRole_banner").format(email=email, role=role_text)
                new_user = helper_create_user_and_invite(request, email, first_name, last_name, role)
                messages.add_message(request, messages.INFO, 'You have invited {0} to CoReRe as an {1}!'.format(email, role_text))
                ### End Messaging ###
            else:
                logger.debug(form.errors) #TODO: DO MORE?
        return render(request, 'main/form_user_details.html', {'form': form, 'helper': helper, 'page_title': "Invite {0}".format(role_text.capitalize())})

    else:
        raise Http404()

#TODO: Should most of this be added to the user save method?
def helper_create_user_and_invite(request, email, first_name, last_name, role):
    #Invitation = get_invitation_model()
    #print(Invitation.__dict__)
    invite = CorereInvitation.create(email, first_name, last_name)#, inviter=request.user)
    #In here, we create a "starter" new_user that will later be modified and connected to auth after the invite
    new_user = User()
    new_user.email = email
    new_user.first_name = first_name
    new_user.last_name = last_name
    
    new_user.username = email #get_random_string(64).lower() #required field, we enter jibberish for now
    new_user.invite_key = invite.key #to later reconnect the new_user we've created to the invite
    new_user.invited_by=request.user
    new_user.set_unusable_password()
    new_user.save()

    role.user_set.add(new_user)

    #TODO: Think about doing this after everything else, incase something bombs
    invite.send_invitation(request)

    return new_user

#To make a select2 dropdown a table, we need to pass info to the template and then into JS
#Here we generate the info
#Its a string that is used to initialize a js map, fairly hacky stuff
#Output looks like: "[['key1', 'foo'], ['key2', 'test']]"
def helper_generate_select_table_info(role_name, group_substring):
    users = User.objects.filter(invite_key='', groups__name=role_name)
    table_dict = "["
    for u in users:
        #{key1: "foo", key2: someObj}
        count = u.groups.filter(name__contains=group_substring).exclude(name__endswith=c.GROUP_COMPLETED_SUFFIX).count()
        table_dict += "['" + u.username +"','"+str(count)+"'],"
    table_dict += "]"
    return table_dict