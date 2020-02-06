from django.shortcuts import render, redirect, get_object_or_404
#from django.http import HttpResponse
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.utils.html import escape
from django.db.models import Q
from django.contrib.auth import logout
from django.contrib import messages
from .models import Manuscript, User
from .forms import ManuscriptForm, InvitationForm, NewUserForm
from django_fsm import can_proceed, has_transition_perm
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from invitations.utils import get_invitation_model
from django.utils.crypto import get_random_string
from guardian.decorators import permission_required_or_403
from guardian.shortcuts import get_objects_for_user, assign_perm
from django.contrib.auth.models import Permission, Group
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from . import constants as c

def index(request):
    if request.user.is_authenticated:
        if(request.user.invite_key): #user hasn't finished signing up if we are still holding their key
            return redirect("/account_user_details")
        else:
            #TODO: write own context processor to pass repeatedly-used constants, etc
            #https://stackoverflow.com/questions/433162/can-i-access-constants-in-settings-py-from-templates-in-django
            args = {'user':     request.user, 
                    'columns':  helper_manuscript_columns(request.user),
                    'GROUP_EDITOR': c.GROUP_EDITOR,
                    'GROUP_AUTHOR': c.GROUP_AUTHOR,
                    'GROUP_VERIFIER': c.GROUP_VERIFIER,
                    'GROUP_CURATOR': c.GROUP_CURATOR,
                    }
            return render(request, "main/index.html", args)
    else:
        return render(request, "main/login.html")

def logout_view(request):
    logout(request)
    messages.add_message(request, messages.INFO, 'You have succesfully logged out!')
    return redirect('/')

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
            users = form.cleaned_data['existing_users']

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
                user.save()
                author_group = Group.objects.get(name=c.GROUP_AUTHOR) 
                author_group.user_set.add(user)
                users.add(user) #add new user to the other uses provided

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

#TODO: Turn these into class-based views?
@permission_required_or_403('main.change_manuscript', (Manuscript, 'id', 'id'), accept_global_perms=True)
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
            if('submit_and_update_status' in request.POST): #MAD: This checks to see which form button was used. There is probably a more precise way to check
                if (not can_proceed(manuscript.begin)) or (not has_transition_perm(manuscript.begin, request.user)): 
                    raise PermissionDenied
                manuscript.begin()
                manuscript.save()
            messages.add_message(request, messages.INFO, message)
            return redirect('/')
        else:
            print(form.errors) #TODO: DO MORE?
    return render(request, 'main/form_create_manuscript.html', {'form': form, 'id': id})

def helper_manuscript_columns(user):
    # This defines the columns a user can view for a table.
    # TODO: Controll in a more centralized manner for security
    # NOTE: If any of the columns defined here are just numbers, it opens a security issue with restricting datatable info. See the comment in extract_datatables_column_data
    
    # MAD: I'm weary of programatically limiting access to data on an attribute level, but I'm not sure of a good way to do this in django, especially with all the other permissions systems in play
    # also.. This should be using guardian?

    columns = []
    if(user.groups.filter(name=c.GROUP_CURATOR).exists()):
        columns += ['id','pub_id','title','doi','open_data','note_text','status','created_at','updated_at','editors','submissions','verifications','curations']
    if(user.groups.filter(name=c.GROUP_VERIFIER).exists()):
        columns += ['id','pub_id','title','doi','open_data']
    if(user.groups.filter(name=c.GROUP_AUTHOR).exists()):
        columns += ['id','pub_id','title','doi','open_data']
    if(user.groups.filter(name=c.GROUP_EDITOR).exists()):
        columns += ['id','pub_id','title','doi','open_data']
    return list(dict.fromkeys(columns)) #remove duplicates, keeps order in python 3.7 and up

# Customizing django-datatables-view defaults
# See https://pypi.org/project/django-datatables-view/ for info on functions
class ManuscriptJson(BaseDatatableView):
    model = Manuscript

    max_display_length = 500

    def get_columns(self):
        return helper_manuscript_columns(self.request.user)

    # pull from source mostly, except when noted. 
    # Needed to disallow users from requesting columns from the model we do not wish to provide
    def extract_datatables_column_data(self):
        """ Helper method to extract columns data from request as passed by Datatables 1.10+
        """
        request_dict = self._querydict
        col_data = []
        if not self.pre_camel_case_notation:
            counter = 0
            data_name_key = 'columns[{0}][name]'.format(counter)

            while data_name_key in request_dict:
                #begin custom 
                allowed_cols = self.get_columns()
                name_data = request_dict.get('columns[{0}][data]'.format(counter)) #Yes, this is actually the name
                #TODO: This prevention of unspecified fields fails if the model field name is just numbers. Can we find a better fix?
                if(not name_data.isdigit() and (name_data not in allowed_cols)):
                    raise SuspiciousOperation("Requested column not available: {0}".format(name_data))
                #end custom

                searchable = True if request_dict.get('columns[{0}][searchable]'.format(counter)) == 'true' else False
                orderable = True if request_dict.get('columns[{0}][orderable]'.format(counter)) == 'true' else False

                col_data.append({'name': request_dict.get(data_name_key),
                                 'data': name_data,
                                 'searchable': searchable,
                                 'orderable': orderable,
                                 'search.value': request_dict.get('columns[{0}][search][value]'.format(counter)),
                                 'search.regex': request_dict.get('columns[{0}][search][regex]'.format(counter)),
                                 })
                counter += 1
                data_name_key = 'columns[{0}][name]'.format(counter)
        return col_data

    def render_column(self, row, column):
        if column == 'editors':
            # escape HTML for security reasons
            if(row.editors.count() > 0):
                return escape('{0}'.format([editor.username for editor in row.editors.all()]))
            else:
                return ""
        else:
            return super(ManuscriptJson, self).render_column(row, column)

    def get_initial_queryset(self):
        #view_perm = Permission.objects.get(codename="view_manuscript")
        return get_objects_for_user(self.request.user, "view_manuscript", klass=Manuscript) # Should use the model definition above?

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter (search) queryset

        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(title__icontains=search)|Q(pub_id__icontains=search)|Q(note_text__icontains=search)|Q(doi__icontains=search))
        return qs
    
    def prepare_results(self, qs):
        data = []
        for item in qs:
            if self.is_data_list:
                data.append([self.render_column(item, column) for column in self._columns])
            else:
                row = {col_data['data']: self.render_column(item, col_data['data']) for col_data in self.columns_data}
                data.append(row)

        return data