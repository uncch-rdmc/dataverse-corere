from django.shortcuts import render, redirect, get_object_or_404
#from django.http import HttpResponse
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.utils.html import escape
from django.db.models import Q
from django.contrib.auth import logout
from django.contrib import messages
from .models import Manuscript, User
from .forms import ManuscriptForm, InvitationForm
from django_fsm import can_proceed, has_transition_perm
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from invitations.utils import get_invitation_model
from django.utils.crypto import get_random_string

def index(request):
    if request.user.is_authenticated:
        args = {'user':     request.user, 
                'columns':  helper_manuscript_columns(request.user)}
        return render(request, "main/index.html", args)
    else:
        return render(request, "main/login.html")

def logout_view(request):
    logout(request)
    messages.add_message(request, messages.INFO, 'You have succesfully logged out!')
    return redirect('/')

# MAD: How do we see this whole flow working?
# Editor/Superuser enters an email into a form and clicks submit
# Corere creates a user with no auth connected, and an email address, and the requested role(s).
# Corere emails the user telling them to sign-up. This has a one-time 
def add_user(request, id=None):
    form = InvitationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']

            Invitation = get_invitation_model()
            invite = Invitation.create(email)#, inviter=request.user)

            #In here, we create a "starter" user that will later be modified and connected to auth after the invite
            user = User()
            user.email = email
            user.username = get_random_string(64).lower() #required field, we enter jibberish for now
            user.is_author = True  #TODO: This need to be dynamic depending on roles selected.
            user.invite_key = invite.key #to later reconnect the user we've created to the invite
            user.save()
            manuscript = Manuscript.objects.get(pk=id)
            #TODO: We need to be able to set the Author as having access to the manuscript. But the permissions structure still needs to be nailed down

            invite.send_invitation(request)
            messages.add_message(request, messages.INFO, 'You have invited {0} to CoReRe!'.format(email))
            return redirect('/')
        else:
            print(form.errors) #MAD: DO MORE?
    return render(request, 'main/form_initialize_user.html', {'form': form})
    # Will need the invitation model to be aware of the roles
    # Also will need to be aware of the manuscript the author/editor/verifier is getting access to
    # (Would be nice to allow multiple selection, but for now lets just do one?)


#MAD: Turn these into class-based views?
#MAD: This does nothing to ensure someone is logged in and has the right permissions, etc
def edit_manuscript(request, id=None):
    # print(request.__dict__)
    print(request.FILES)
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
            print(form.errors) #MAD: DO MORE?
    return render(request, 'main/form_create_manuscript.html', {'form': form, 'id': id})

def helper_manuscript_columns(user):
    # This defines the columns a user can view for a table.
    # TODO: Controll in a more centralized manner for security
    # NOTE: If any of the columns defined here are just numbers, it opens a security issue with restricting datatable info. See the comment in extract_datatables_column_data
    columns = []
    if(user.is_curator):
        columns += ['id','pub_id','title','doi','open_data','note_text','status','created_at','updated_at','editors','submissions','verifications','curations']
    if(user.is_verifier):
        columns += ['id','pub_id','title','doi','open_data']
    if(user.is_author):
        columns += ['id','pub_id','title','doi','open_data']
    if(user.is_editor):
        columns += ['id','pub_id','title','doi','open_data']
    return list(dict.fromkeys(columns)) #remove duplicates, keeps order in python 3.7 and up

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