from django_datatables_view.base_datatable_view import BaseDatatableView
from corere.main.models import Manuscript, Submission, User
from corere.main import constants as c
from guardian.shortcuts import get_objects_for_user, get_perms
from django.utils.html import escape
from django.db.models import Q
from guardian.shortcuts import get_perms
from django_fsm import has_transition_perm# can_proceed,

#Shared across our various datatables
class CorereBaseDatatableView(BaseDatatableView):
    # pull from source mostly, except when noted. 
    # Needed to disallow users from requesting columns from the model we do not wish to provide
    def extract_datatables_column_data(self):
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

    def prepare_results(self, qs):
        data = []
        #TODO: Confirm this works right with pagination
        data.append(self.get_columns()) #add headers to grab in js for dynamic support
        for item in qs:
            if self.is_data_list:
                data.append([self.render_column(item, column) for column in self._columns])
            else:
                row = {col_data['data']: self.render_column(item, col_data['data']) for col_data in self.columns_data}
                data.append(row)

        return data


def helper_manuscript_columns(user):
    # This defines the columns a user can view for a table.
    # TODO: Controll in a more centralized manner for security
    # NOTE: If any of the columns defined here are just numbers, it opens a security issue with restricting datatable info. See the comment in extract_datatables_column_data
    
    # MAD: I'm weary of programatically limiting access to data on an attribute level, but I'm not sure of a good way to do this in django, especially with all the other permissions systems in play
    # also.. This should be using guardian?

    columns = []
    if(user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists()):
        columns += ['id','pub_id','title','doi','open_data','status','created_at','updated_at','authors','curators','verifiers','buttons']
    if(user.groups.filter(name=c.GROUP_ROLE_VERIFIER).exists()):
        columns += ['id','pub_id','title','doi','open_data','authors']
    if(user.groups.filter(name=c.GROUP_ROLE_AUTHOR).exists()):
        columns += ['id','pub_id','title','doi','open_data','authors']
    if(user.groups.filter(name=c.GROUP_ROLE_EDITOR).exists()):
        columns += ['id','pub_id','title','doi','open_data','authors']
    return list(dict.fromkeys(columns)) #remove duplicates, keeps order in python 3.7 and up

# Customizing django-datatables-view defaults
# See https://pypi.org/project/django-datatables-view/ for info on functions
class ManuscriptJson(CorereBaseDatatableView):
    model = Manuscript
    max_display_length = 500

    def get_columns(self):
        return helper_manuscript_columns(self.request.user)

    def render_column(self, obj, column):
        if column == 'authors':
            return '{0}'.format([escape(user.username) for user in User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(obj.id))])
        if column == 'curators':
            return '{0}'.format([escape(user.username) for user in User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(obj.id))])
        if column == 'verifiers':
            return '{0}'.format([escape(user.username) for user in User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(obj.id))])
        if column == 'buttons':
            user = self.request.user
            avail_buttons = []
            #fsm_check_transition_perm(manuscript.begin, request.user))
            print(get_perms(user, obj))
            from django.contrib.auth.models import Permission
            print(str(Permission.objects.filter(user=user)))
            #if(user.has_perm('change_manuscript', obj)):
            if(has_transition_perm(obj.edit_noop, user)):
                avail_buttons.append('editManuscript')
            # MAD: The way permissions work for this is confusing and will lead to bugs. It'd be good to create a wrapper that checks perms in all the places / can handle app label / etc
            if(user.has_perm('manage_authors_on_manuscript', obj) or user.has_perm('main.manage_authors_on_manuscript')):
                avail_buttons.append('addAuthor')
            if(user.has_perm('manage_curators_on_manuscript', obj) or user.has_perm('main.manage_curators_on_manuscript')):
                avail_buttons.append('addCurator')
            if(user.has_perm('manage_verifiers_on_manuscript', obj) or user.has_perm('main.manage_verifiers_on_manuscript')):
                avail_buttons.append('addVerifier')

            return avail_buttons#escape(get_perms(self.request.user, obj))
        else:
            return super(ManuscriptJson, self).render_column(obj, column)

    def get_initial_queryset(self):
        #view_perm = Permission.objects.get(codename="view_manuscript")
        return get_objects_for_user(self.request.user, "view_manuscript", klass=Manuscript) # Should use the model definition above?

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter (search) queryset

        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(title__icontains=search)|Q(pub_id__icontains=search)|Q(doi__icontains=search))
        return qs

def helper_submission_columns(user):
    # This defines the columns a user can view for a table.
    # TODO: Controll in a more centralized manner for security
    # NOTE: If any of the columns defined here are just numbers, it opens a security issue with restricting datatable info. See the comment in extract_datatables_column_data
    
    # MAD: I'm weary of programatically limiting access to data on an attribute level, but I'm not sure of a good way to do this in django, especially with all the other permissions systems in play
    # also.. This should be using guardian?

    columns = ['id','curation_status']
    # if(user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists()):
    #     columns += ['id','pub_id','title','doi','open_data','status','created_at','updated_at','authors','submissions','verifications','curations','buttons']
    # if(user.groups.filter(name=c.GROUP_ROLE_VERIFIER).exists()):
    #     columns += ['id','pub_id','title','doi','open_data','authors']
    # if(user.groups.filter(name=c.GROUP_ROLE_AUTHOR).exists()):
    #     columns += ['id','pub_id','title','doi','open_data','authors']
    # if(user.groups.filter(name=c.GROUP_ROLE_EDITOR).exists()):
    #     columns += ['id','pub_id','title','doi','open_data','authors']
    return list(dict.fromkeys(columns)) #remove duplicates, keeps order in python 3.7 and up

class SubmissionJson(CorereBaseDatatableView):
    model = Submission
    max_display_length = 500

    def get_columns(self):
        return helper_submission_columns(self.request.user)

    def render_column(self, obj, column):
        if column == 'curation_status':
            return '{0}'.format(obj.submission_curation.status)
        else:
            return super(SubmissionJson, self).render_column(obj, column)

    def get_initial_queryset(self):
        manuscript_id = self.kwargs['manuscript_id']
        #view_perm = Permission.objects.get(codename="view_manuscript")
        return get_objects_for_user(self.request.user, "view_submission", klass=Submission).filter(manuscript=manuscript_id) # Should use the model definition above?

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter (search) queryset

        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(title__icontains=search)|Q(pub_id__icontains=search)|Q(doi__icontains=search))
        return qs

