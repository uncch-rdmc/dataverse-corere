import logging, requests
from django.shortcuts import render, redirect, get_object_or_404
from guardian.decorators import permission_required_or_404
from guardian.shortcuts import get_objects_for_user, assign_perm, get_users_with_perms
from corere.main.models import Manuscript, User, CorereInvitation
from django.contrib.auth.decorators import login_required
from corere.main.forms import AuthorAddForm, UserByRoleAddFormHelper, UserDetailsFormHelper, AuthorInviteAddForm, EditorAddForm, CuratorAddForm, VerifierAddForm, EditUserForm, UserInviteForm, AuthorInviteAddFormHelper, StandardUserAddFormHelper
from django.contrib import messages
from django.utils.safestring import mark_safe
from invitations.utils import get_invitation_model
from django.utils.crypto import get_random_string
from django.contrib.auth.models import Permission, Group
from corere.main import constants as c
from corere.main import models as m
from corere.main import wholetale_corere as w
from django.contrib.auth import login, logout
from django.conf import settings
from notifications.signals import notify
from django.http import Http404, HttpResponse
from corere.main.templatetags.auth_extras import has_group
from corere.main.utils import fsm_check_transition_perm, generate_progress_bar_html
from django.utils.translation import gettext as _
from django.db import IntegrityError
from templated_email import send_templated_mail
from django.views.decorators.http import require_http_methods
logger = logging.getLogger(__name__)

# Editor/Superuser enters an email into a form and clicks submit
# Corere creates a user with no auth connected, and an email address, and the requested role(s).
# Corere emails the user telling them to sign-up. This has a one-time 

# TODO: We should probably make permissions part of our constants as well

@login_required
# @permission_required_or_404(c.perm_path(c.PERM_MANU_ADD_AUTHORS), (Manuscript, 'id', 'id'), accept_global_perms=True) #slightly hacky that you need add to access the remove function, but everyone with remove should be able to add
@permission_required_or_404(c.perm_path(c.PERM_MANU_CURATE), (Manuscript, 'id', 'id'), accept_global_perms=True)
@require_http_methods(["GET", "POST"])
def invite_assign_author(request, id=None):
    group_substring = c.GROUP_MANUSCRIPT_AUTHOR_PREFIX
    form = AuthorInviteAddForm(request.POST or None)
    manuscript = Manuscript.objects.get(pk=id)
    page_title = _("user_assignAuthor_pageTitle")
    page_help_text = _("user_assignAuthor_helpText")

    # if(manuscript._status == m.Manuscript.Status.COMPLETED_REPORT_SENT): #or not(request.user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists() or request.user.is_superuser)):
    #     raise Http404()

    manu_author_group = Group.objects.get(name__startswith=group_substring + " " + str(manuscript.id))
    can_remove_author = request.user.has_any_perm(c.PERM_MANU_REMOVE_AUTHORS, manuscript)
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            users = list(form.cleaned_data['users_to_add']) 
            new_user = ''
            if(email):
                author_role = Group.objects.get(name=c.GROUP_ROLE_AUTHOR) 
                try:
                    #def helper_create_user_and_invite(request, email, first_name, last_name, role):
                    new_user = helper_create_user_and_invite(request, email, first_name, last_name, author_role)
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
                msg = _("user_addAsRoleToManuscript_banner").format(role="author", email=u.email, manuscript_display_name=manuscript.get_display_name())
                logger.info(msg)
                messages.add_message(request, messages.INFO, msg)
                notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="author", email=request.user.email, manuscript_display_name=manuscript.get_display_name(), object_url=manuscript.get_landing_url(request))
                if(u != new_user):
                    notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
                    send_templated_mail( template_name='base', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={'subject':'CORE2 Update', 'notification_msg':notification_msg, 'user_email':u.email} )
                ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_AUTHOR, group_substring), 'manuscript_display_name': manuscript.get_display_name(),
        'group_substring': group_substring, 'role_name': 'Author', 'assigned_users': manu_author_group.user_set.all(), 'can_remove_author': can_remove_author, 'page_title': page_title, 'page_help_text': page_help_text,
        'helper': AuthorInviteAddFormHelper()})

#Called during initial manuscript creation
@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_ADD_AUTHORS), (Manuscript, 'id', 'id'), accept_global_perms=True) #slightly hacky that you need add to access the remove function, but everyone with remove should be able to add
@require_http_methods(["GET", "POST"])
def add_author(request, id=None):
    group_substring = c.GROUP_MANUSCRIPT_AUTHOR_PREFIX
    manuscript = Manuscript.objects.get(pk=id)
    page_title = _("user_assignAuthor_pageTitle")
    page_help_text = _("user_assignAuthor_helpText")
    helper = UserByRoleAddFormHelper()
    form_initial = {'first_name':manuscript.contact_first_name, 'last_name':manuscript.contact_last_name, 'email':manuscript.contact_email}
    form = AuthorAddForm(request.POST or None, initial=form_initial)

    if(manuscript._status == m.Manuscript.Status.COMPLETED_REPORT_SENT):
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
            msg = _("user_addAsRoleToManuscript_banner").format(role="author", email=user.email, manuscript_display_name=manuscript.get_display_name())
            logger.info(msg.format(user.email, manuscript.get_display_name()))
            messages.add_message(request, messages.INFO, msg)
            notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="author", email=request.user.email, manuscript_display_name=manuscript.get_display_name(), object_url=manuscript.get_landing_url(request))
            if(not new_user):
                notify.send(request.user, verb='assigned', recipient=user, target=manuscript, public=False, description=notification_msg)
                send_templated_mail( template_name='base', from_email=settings.EMAIL_HOST_USER, recipient_list=[user.email], context={'subject':'CORE2 Update', 'notification_msg':notification_msg, 'user_email':user.email} )

            msg = _("manuscript_submitted_banner").format(manuscript_display_name=manuscript.get_display_name(), manuscript_id=manuscript.id)
            messages.add_message(request, messages.INFO, msg)
            ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))

        else:
            logger.debug(form.errors) #TODO: DO MORE?

    progress_list = c.progress_list_manuscript
    progress_bar_html = generate_progress_bar_html(progress_list, 'Invite Author')

    return render(request, 'main/form_add_author.html', {'form': form, 'helper': helper,  'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_AUTHOR, group_substring), 
        'group_substring': group_substring, 'role_name': 'Author', 'manuscript_display_name': manuscript.get_display_name(), 'page_title': page_title, 'page_help_text': page_help_text, 'progress_bar_html': progress_bar_html})

@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_REMOVE_AUTHORS), (Manuscript, 'id', 'id'), accept_global_perms=True)
@require_http_methods(["GET", "POST"])
def unassign_author(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        if(manuscript._status == m.Manuscript.Status.COMPLETED_REPORT_SENT):
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
@require_http_methods(["GET", "POST"])
def assign_editor(request, id=None):
    form = EditorAddForm(request.POST or None)
    page_title = _("user_assignEditor_pageTitle")
    manuscript = Manuscript.objects.get(pk=id)
    if(manuscript._status == m.Manuscript.Status.COMPLETED_REPORT_SENT):
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
                msg = _("user_addAsRoleToManuscript_banner").format(role="editor", email=u.email, manuscript_display_name=manuscript.get_display_name())
                messages.add_message(request, messages.INFO, msg)
                logger.info(msg)
                notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="editor", email=request.user.email, manuscript_display_name=manuscript.get_display_name(), object_url=manuscript.get_landing_url(request))
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
                send_templated_mail( template_name='base', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={'subject':'CORE2 Update', 'notification_msg':notification_msg, 'user_email':u.email} )
                ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_EDITOR, group_substring), 
        'group_substring': group_substring, 'role_name': 'Editor', 'assigned_users': manu_editor_group.user_set.all(), 'manuscript_display_name': manuscript.get_display_name(), 'page_title': page_title,
        'helper': StandardUserAddFormHelper()})

@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_EDITORS), (Manuscript, 'id', 'id'), accept_global_perms=True)
@require_http_methods(["GET", "POST"])
def unassign_editor(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        if(manuscript._status == m.Manuscript.Status.COMPLETED_REPORT_SENT):
            raise Http404()
        group_substring = c.GROUP_MANUSCRIPT_EDITOR_PREFIX
        manu_editor_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
        try:
            user = manu_editor_group.user_set.get(id=user_id)
        except User.DoesNotExist:
            logger.warn("User {0} attempted to remove user id {1} from group {2} which is invalid".format(request.user.id, user_id, group_substring))
            raise Http404()
        manu_editor_group.user_set.remove(user)
        return redirect('/manuscript/'+str(id)+'/assigneditor')

@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_CURATORS), (Manuscript, 'id', 'id'), accept_global_perms=True)
@require_http_methods(["GET", "POST"])
def assign_curator(request, id=None):
    form = CuratorAddForm(request.POST or None)
    page_title = _("user_assignCurator_pageTitle")
    manuscript = Manuscript.objects.get(pk=id)
    if(manuscript._status == m.Manuscript.Status.COMPLETED_REPORT_SENT):
        raise Http404()
    group_substring = c.GROUP_MANUSCRIPT_CURATOR_PREFIX
    manu_curator_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
    # if manuscript.skip_edition:
    #     manu_author_group = Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX+ " " + str(manuscript.id))
    #     manu_editor_group = Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX+ " " + str(manuscript.id))
    if request.method == 'POST':
        if form.is_valid():
            users_to_add = list(form.cleaned_data['users_to_add'])
            
            for u in users_to_add:
                if(not u.groups.filter(name=c.GROUP_ROLE_CURATOR).exists()):
                    logger.warn("User {0} attempted to add user id {1} from group {2} when they don't have the base role (probably by hacking the form".format(request.user.id, u.id, group_substring))
                    raise Http404()
                manu_curator_group.user_set.add(u)
                # if manuscript.skip_edition:
                #     manu_author_group.user_set.add(u)
                #     manu_editor_group.user_set.add(u)

                ### Messaging ###
                msg = _("user_addAsRoleToManuscript_banner").format(role="curator", email=u.email, manuscript_display_name=manuscript.get_display_name())
                messages.add_message(request, messages.INFO, msg)
                logger.info(msg)
                notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="curator", email=request.user.email, manuscript_display_name=manuscript.get_display_name(), object_url=manuscript.get_landing_url(request))
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
                send_templated_mail( template_name='base', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={'subject':'CORE2 Update', 'notification_msg':notification_msg, 'user_email':u.email} )
                ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_CURATOR, group_substring),
        'group_substring': group_substring, 'role_name': 'Curator', 'assigned_users': manu_curator_group.user_set.all(), 'manuscript_display_name': manuscript.get_display_name(), 'page_title': page_title,
        'helper': StandardUserAddFormHelper()})

@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_CURATORS), (Manuscript, 'id', 'id'), accept_global_perms=True)
@require_http_methods(["GET", "POST"])
def unassign_curator(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        if(manuscript._status == m.Manuscript.Status.COMPLETED_REPORT_SENT):
            raise Http404()
        group_substring = c.GROUP_MANUSCRIPT_CURATOR_PREFIX
        manu_curator_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
        # if manuscript.skip_edition:
        #     manu_author_group = Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX+ " " + str(manuscript.id))
        #     manu_editor_group = Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX+ " " + str(manuscript.id))
        try:
            user = manu_curator_group.user_set.get(id=user_id)
        except User.DoesNotExist:
            logger.warn("User {0} attempted to remove user id {1} from group {2} which is invalid".format(request.user.id, user_id, group_substring))
            raise Http404()
        manu_curator_group.user_set.remove(user)
        # if manuscript.skip_edition:
        #     manu_author_group.user_set.remove(u)
        #     manu_editor_group.user_set.remove(u)

        return redirect('/manuscript/'+str(id)+'/assigncurator')

@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_VERIFIERS), (Manuscript, 'id', 'id'), accept_global_perms=True)
@require_http_methods(["GET", "POST"])
def assign_verifier(request, id=None):
    form = VerifierAddForm(request.POST or None)
    page_title = _("user_assignVerifier_pageTitle")
    manuscript = Manuscript.objects.get(pk=id)
    if(manuscript._status == m.Manuscript.Status.COMPLETED_REPORT_SENT):
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
                msg = _("user_addAsRoleToManuscript_banner").format(role="verifier", email=u.email, manuscript_display_name=manuscript.get_display_name())
                messages.add_message(request, messages.INFO, msg)
                logger.info(msg)
                notification_msg = _("user_addedYouAsRoleToManuscript_notify").format(role="verifier", email=request.user.email, manuscript_display_name=manuscript.get_display_name(), object_url=manuscript.get_landing_url(request))
                notify.send(request.user, verb='assigned', recipient=u, target=manuscript, public=False, description=notification_msg)
                send_templated_mail( template_name='base', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={'subject':'CORE2 Update', 'notification_msg':notification_msg, 'user_email':u.email} )
                ### End Messaging ###

            return redirect('/manuscript/'+str(manuscript.id))
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_assign_user.html', {'form': form, 'id': id, 'select_table_info': helper_generate_select_table_info(c.GROUP_ROLE_VERIFIER, group_substring),
        'group_substring': group_substring, 'role_name': 'Verifier', 'assigned_users': manu_verifier_group.user_set.all(), 'manuscript_display_name': manuscript.get_display_name(), 'page_title': page_title,
        'helper': StandardUserAddFormHelper()})

#MAD: Maybe error if id not in list (right now does nothing silently)
@login_required
@permission_required_or_404(c.perm_path(c.PERM_MANU_MANAGE_VERIFIERS), (Manuscript, 'id', 'id'), accept_global_perms=True)
@require_http_methods(["GET", "POST"])
def unassign_verifier(request, id=None, user_id=None):
    if request.method == 'POST':
        manuscript = Manuscript.objects.get(pk=id)
        if(manuscript._status == m.Manuscript.Status.COMPLETED_REPORT_SENT):
            raise Http404()
        group_substring = c.GROUP_MANUSCRIPT_VERIFIER_PREFIX
        manu_verifier_group = Group.objects.get(name=group_substring+ " " + str(manuscript.id))
        try:
            user = manu_verifier_group.user_set.get(id=user_id)
        except User.DoesNotExist:
            logger.warn("User {0} attempted to remove user id {1} from group {2} which is invalid".format(request.user.id, user_id, group_substring))
            raise Http404()
        manu_verifier_group.user_set.remove(user)
        return redirect('/manuscript/'+str(id)+'/assignverifier')

@require_http_methods(["GET"])
def account_associate_oauth(request, key=None):
    logout(request)
    user = get_object_or_404(User, invite__key=key)
    login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0]) # select a "fake" backend for our auth

    return render(request, 'main/new_user_oauth.html')

@require_http_methods(["GET"])
def account_associate_error(request, key=None):
    logout(request)
    return render(request, 'main/new_user_error.html')

#If Whole Tale is enabled, redirect user to the Whole Tale Globus authorization. Otherwise just continue to account_user_details
#TODO: Should we restrict at all when this page is accessed?
@login_required()
@require_http_methods(["GET"])
def account_complete_oauth(request):
    if settings.CONTAINER_DRIVER == "wholetale":
        if request.is_secure():
            protocol = "https"
        else:
            protocol = "http"
        
        r = requests.get(
            "https://girder."+settings.WHOLETALE_BASE_URL+"/api/v1/oauth/provider",
            params={"redirect": protocol + "://"+settings.SERVER_ADDRESS+"/account_user_details/?girderToken={girderToken}"} #This is not an f string. The {girderToken} indicates to girder to pass the token back
        )
        resp = HttpResponse(content="", status=303)
        resp["Location"] = r.json()["Globus"]
        return resp
    else:
        return redirect('/account_user_details/')

#This view is the first one the users are sent to after accepting an invite and registering
@login_required()
@require_http_methods(["GET", "POST"])
def account_user_details(request):
    helper = UserDetailsFormHelper()
    page_title = _("user_accountDetails_pageTitle")
           
    form = EditUserForm(request.POST or None, instance=request.user)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            msg = _("user_infoUpdated_banner")
            messages.add_message(request, messages.SUCCESS, msg)
            return redirect('/')
        else:
            logger.debug(form.errors) #TODO: DO MORE?
    
    response = render(request, 'main/form_user_details.html', {'form': form, 'page_title': page_title, 'helper': helper})

    if request.method == 'GET':
        try: #request.user.invite will error if there is no invite
            #we delete the invitation now that we can associate the user
            request.user.invite.delete() 
            
            #Since the new user now is part of Whole Tale, we invite them to all the groups they should be in    
            if settings.CONTAINER_DRIVER == 'wholetale':
                girderToken = request.GET.get("girderToken", None)
                if girderToken:
                    response.set_cookie(key="girderToken", value=girderToken)
                    #Here we also store the wt_id for the user, if there is a girderToken incoming it means they were just redirected from WT
                    wt_user = w.WholeTaleCorere(girderToken).get_logged_in_user()
                    request.user.wt_id = wt_user.get("_id")
                    request.user.save()

                wtc = w.WholeTaleCorere(admin=True)
                for group in request.user.groups.all():
                    if (group.name.startswith(c.GROUP_MANUSCRIPT_EDITOR_PREFIX) 
                    or group.name.startswith(c.GROUP_MANUSCRIPT_AUTHOR_PREFIX) 
                    or group.name.startswith(c.GROUP_MANUSCRIPT_CURATOR_PREFIX) 
                    or group.name.startswith(c.GROUP_MANUSCRIPT_VERIFIER_PREFIX)):
                        wtc.invite_user_to_group(request.user.wt_id, group.wholetale_group.wt_id)

                if(request.user.is_superuser):
                    wtc.invite_user_to_group(request.user.wt_id, wtm.objects.get(is_admins=True).wt_id)

                w.WholeTaleCorere(girderToken) #connecting as the user detects and accepts outstanding invitations
        except User.invite.RelatedObjectDoesNotExist:
            pass
    return response

@require_http_methods(["GET"])
def logout_view(request):
    logout(request)
    msg = _("user_loggedOut_banner") + ' <a href="https://auth.globus.org/v2/web/logout">click here</a>.'
    messages.add_message(request, messages.INFO,  mark_safe(msg))
    return redirect('/')

@login_required()
@require_http_methods(["GET"])
def notifications(request):
    return render(request, 'main/notifications.html', 
        {'page_title': _("notifications_pageTitle")})

@login_required()
@require_http_methods(["GET", "POST"])
def invite_editor(request):
    role = Group.objects.get(name=c.GROUP_ROLE_EDITOR) 
    return invite_user_not_author(request, role, "editor")

@login_required()
@require_http_methods(["GET", "POST"])
def invite_curator(request):
    role = Group.objects.get(name=c.GROUP_ROLE_CURATOR) 
    return invite_user_not_author(request, role, "curator")

@login_required()
@require_http_methods(["GET", "POST"])
def invite_verifier(request):
    role = Group.objects.get(name=c.GROUP_ROLE_VERIFIER) 
    return invite_user_not_author(request, role, "verifier")

@login_required()
@require_http_methods(["GET", "POST"])
def invite_user_not_author(request, role, role_text):
    if(has_group(request.user, c.GROUP_ROLE_CURATOR)):
        form = UserInviteForm(request.POST or None)
        helper = UserByRoleAddFormHelper()
        if request.method == 'POST':
            if form.is_valid():
                email = form.cleaned_data['email']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']
                
                if User.objects.filter(email=email):
                    messages.error(request, "Email provided already exists in CORE2")
                    return render(request, 'main/form_user_details.html', {'form': form, 'helper': helper, 'page_title': "Invite {0}".format(role_text.capitalize())})

                ### Messaging ###
                msg = _("user_inviteRole_banner").format(email=email, role=role_text)
                new_user = helper_create_user_and_invite(request, email, first_name, last_name, role)
                messages.add_message(request, messages.INFO, 'You have invited {0} to CORE2 as an {1}!'.format(email, role_text))
                ### End Messaging ###
            else:
                logger.debug(form.errors) #TODO: DO MORE?
        return render(request, 'main/form_user_details.html', {'form': form, 'helper': helper, 'page_title': "Invite {0}".format(role_text.capitalize())})

    else:
        raise Http404()

#TODO: Inviting with a bad email address errors but only AFTER the new user is created, creating an orphan
#TODO: Should most of this be added to the user save method?
def helper_create_user_and_invite(request, email, first_name, last_name, role):
    from django.contrib.sites.models import Site
    from django.contrib.sites.shortcuts import get_current_site

    #In here, we create a "starter" new_user that will later be modified and connected to auth after the invite
    new_user = User()
    new_user.email = email
    new_user.first_name = first_name
    new_user.last_name = last_name
    
    new_user.username = email #get_random_string(64).lower() #required field, we enter jibberish for now
    
    if request.user:
        new_user.invited_by=request.user
    new_user.set_unusable_password()
    new_user.full_clean() #runs email validator among other things. not perfect because if this fails we get a 500, but better than orphan users
    new_user.save()
    role.user_set.add(new_user)

    invite = CorereInvitation.create(email, new_user)#, inviter=request.user)

    ## TODO: This code was an attempt to alter the domain/port of the emails coming out of the invitations library. It didn't work
    ##       The goal in doing this was to make the invitation urls match the SERVER_ADDRESS. Which is nice when we are using an alternate SERVER_ADDRESS to make VM based testing flow
    ##       This wasn't high priority though so it was abandoned. We can just replace the urls during invite.
    ##       We may need to do this for other reasons in the future. See here for more info: https://github.com/bee-keeper/django-invitations/blob/9069002f1a0572ae37ffec21ea72f66345a8276f/invitations/models.py

    # request.META['SERVER_NAME'], request.META['SERVER_PORT'] = settings.SERVER_ADDRESS.split(":")
    # request.HTTP_HOST = settings.SERVER_ADDRESS
    invite.send_invitation(request)

    return new_user

#To make a select2 dropdown a table, we need to pass info to the template and then into JS
#Here we generate the info
#Its a string that is used to initialize a js map, fairly hacky stuff
#Output looks like: "[['key1', 'foo'], ['key2', 'test']]"
def helper_generate_select_table_info(role_name, group_substring):
    users = User.objects.filter(invite__isnull=True, groups__name=role_name)
    table_dict = "["
    for u in users:
        #{key1: "foo", key2: someObj}
        count = u.groups.filter(name__contains=group_substring).exclude(name__endswith=c.GROUP_COMPLETED_SUFFIX).count()
        table_dict += "['" + u.username +"','"+str(count)+"'],"
    table_dict += "]"
    return table_dict