import logging
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.conf import settings
from corere.main import constants as c
from corere.main import models as m
from corere.apps.file_datatable import views as fdtv
from corere.main.utils import fsm_check_transition_perm
from guardian.shortcuts import get_objects_for_user, get_perms
from django.utils.html import escape
from django.db.models import Q
from guardian.shortcuts import get_perms
from django_fsm import has_transition_perm
from django.utils.decorators import classonlymethod
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
logger = logging.getLogger(__name__)

#Shared across our various (non-file) datatables
class CorereBaseDatatableView(LoginRequiredMixin, BaseDatatableView):
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
        data.append(self.get_columns()) #adds headers to grab in js for dynamic support
        for item in qs:
            if self.is_data_list:
                data.append([self.render_column(item, column) for column in self._columns])
            else:
                row = {col_data['data']: self.render_column(item, col_data['data']) for col_data in self.columns_data}
                data.append(row)

        
        return data

    # pull from source, paging commented out for now
    #TODO: Understand why the paging isn't pulling correctly from datatables. We will probably want this when the number of manuscripts gets large
    def paging(self, qs):
        """ Paging
        """

        return qs

        # if self.pre_camel_case_notation:
        #     limit = min(int(self._querydict.get('iDisplayLength', 10)), self.max_display_length)
        #     start = int(self._querydict.get('iDisplayStart', 0))
        # else:
        #     limit = min(int(self._querydict.get('length', 10)), self.max_display_length)
        #     start = int(self._querydict.get('start', 0))

        # # if pagination is disabled ("paging": false)
        # if limit == -1:
        #     return qs

        # offset = start + limit

        # return qs[start:offset]


def helper_manuscript_columns(user):
    columns = [['selected',''],['id','ID'],['pub_id','Pub ID'],['pub_name','Pub Name'],['_status','Status']]
    if(user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists()):
        columns.append(['users', "Users"])
    if(user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists() or user.groups.filter(name=c.GROUP_ROLE_VERIFIER).exists()):
        #columns.append(['created_at','Create Date']) #Right now we don't show it so why provide it?
        columns.append(['updated_at','Last Update Date'])
    return columns
    #return list(dict.fromkeys(columns)) #remove duplicates, keeps order in python 3.7 and up

# Customizing django-datatables-view defaults
# See https://pypi.org/project/django-datatables-view/ for info on functions
class ManuscriptJson(CorereBaseDatatableView):
    max_display_length = 500

    def get_columns(self):
        return helper_manuscript_columns(self.request.user)

    # If you need the old render_column code, look at commit aa36e9b87b8d8504728ff2365219beb917210eae or earlier
    def render_column(self, manuscript, column):
        if column[0] == 'users':
            return ", ".join(list(set(m.User.objects.filter(groups__name__contains="Manuscript " + str(manuscript.id)).values_list('username', flat=True))))
        elif column[0] == 'created_at':
            return '{0}'.format(manuscript.created_at.strftime("%b %d %Y %H:%M")) #%H:%M:%S"
        elif column[0] == 'updated_at':
            return '{0}'.format(manuscript.updated_at.strftime("%b %d %Y %H:%M"))
        else:
            return super(ManuscriptJson, self).render_column(manuscript, column[0])

    def get_initial_queryset(self):
        return get_objects_for_user(self.request.user, c.PERM_MANU_VIEW_M, klass=m.Manuscript).order_by('-id')

    #Note: this isn't tied to the search bar in the datatable, that happens solely browserside
    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter (search) queryset
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(pub_name__icontains=search)|Q(pub_id__icontains=search)|Q(doi__icontains=search))
        return qs

def helper_submission_columns(user):
    columns = [['selected',''],['id','ID'],['version_id', 'Submission'],['submission_status','Submission Status'],['submission_timestamp','Submission Updated At'],['buttons','Buttons']]
    if(user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists() or user.groups.filter(name=c.GROUP_ROLE_VERIFIER).exists()):
        columns.append(['edition_status', 'Editor Review'])
        columns.append(['edition_timestamp', 'Edition Updated At'])        
        columns.append(['curation_status','Curator Review'])
        columns.append(['curation_timestamp', 'Curation Updated At'])
        columns.append(['verification_status','Verifier Review'])
        columns.append(['verification_timestamp', 'Verification Updated At'])

    #return list(dict.fromkeys(columns)) #remove duplicates, keeps order in python 3.7 and up
    return columns

class SubmissionJson(CorereBaseDatatableView):
    model = m.Submission
    max_display_length = 500

    def get_columns(self):
        return helper_submission_columns(self.request.user)

    def render_column(self, submission, column):
        user = self.request.user

        if column[0] == 'submission_status':
            if(has_transition_perm(submission.view_noop, user)):
                return submission.get__status_display()
            else:
                return ''
        elif column[0] == 'submission_timestamp':
            if(has_transition_perm(submission.view_noop, user)):
                return submission.updated_at.strftime("%b %d %Y %H:%M")
            else:
                return ''

        elif column[0] == 'edition_status':
            try:
                if(has_transition_perm(submission.submission_edition.view_noop, user)):
                    return '{0}'.format(submission.submission_edition.get__status_display())
            except m.Submission.submission_edition.RelatedObjectDoesNotExist:
                pass
            return ''
        elif column[0] == 'edition_timestamp':
            try:
                if(has_transition_perm(submission.submission_edition.view_noop, user)):
                    return submission.submission_edition.updated_at.strftime("%b %d %Y %H:%M")
            except m.Submission.submission_edition.RelatedObjectDoesNotExist:
                pass
            return ''

        elif column[0] == 'curation_status':
            try:
                if(has_transition_perm(submission.submission_curation.view_noop, user)):
                    return '{0}'.format(submission.submission_curation.get__status_display())
            except m.Submission.submission_curation.RelatedObjectDoesNotExist:
                pass
            return ''
        elif column[0] == 'curation_timestamp':
            try:
                if(has_transition_perm(submission.submission_curation.view_noop, user)):
                    return '{0}'.format(submission.submission_curation.updated_at.strftime("%b %d %Y %H:%M"))
            except m.Submission.submission_curation.RelatedObjectDoesNotExist:
                pass
            return ''

        elif column[0] == 'verification_status':
            try:
                if(has_transition_perm(submission.submission_verification.view_noop, user)):
                    return '{0}'.format(submission.submission_verification.get__status_display())
            except m.Submission.submission_verification.RelatedObjectDoesNotExist:
                pass
            return ''
        elif column[0] == 'verification_timestamp':
            try:
                if(has_transition_perm(submission.submission_verification.view_noop, user)):
                    return '{0}'.format(submission.submission_verification.updated_at.strftime("%b %d %Y %H:%M"))
            except m.Submission.submission_verification.RelatedObjectDoesNotExist:
                pass
            return ''

        elif column[0] == 'buttons': 
            avail_buttons = []

            #Here we allow edit submission to be done at multiple phases
            if(has_transition_perm(submission.edit_noop, user)
               or has_transition_perm(submission.add_edition_noop, user)
               or has_transition_perm(submission.add_curation_noop, user)
               or has_transition_perm(submission.add_verification_noop, user) ):
                avail_buttons.append('editSubmission')
                #avail_buttons.append('editSubmissionFiles')
            else:
                try:
                    if(has_transition_perm(submission.submission_edition.edit_noop, user)):
                        avail_buttons.append('editSubmission')
                        #avail_buttons.append('editSubmissionFiles')
                except m.Submission.submission_edition.RelatedObjectDoesNotExist:
                    pass

                try:
                    if(has_transition_perm(submission.submission_curation.edit_noop, user)):
                        avail_buttons.append('editSubmission')
                        #avail_buttons.append('editSubmissionFiles')
                except m.Submission.submission_curation.RelatedObjectDoesNotExist:
                    pass

                try:
                    if(has_transition_perm(submission.submission_verification.edit_noop, user)):
                        avail_buttons.append('editSubmission')
                        #avail_buttons.append('editSubmissionFiles')
                except m.Submission.submission_verification.RelatedObjectDoesNotExist:
                    pass

            if(has_transition_perm(submission.view_noop, user)):
                if('editSubmission' not in avail_buttons):
                    avail_buttons.append('viewSubmission')
                if('editSubmissionFiles' not in avail_buttons):
                    avail_buttons.append('viewSubmissionFiles')

            # if(has_transition_perm(submission.submit, user)):
            #     avail_buttons.append('progressSubmission')
            if(has_transition_perm(submission.send_report, user)):
                avail_buttons.append('generateReportForSubmission')
            if(has_transition_perm(submission.finish_submission, user)):
                avail_buttons.append('returnSubmission')

            # Similar logic repeated in main page view for showing the sub button for the manuscript level
            if submission.manuscript.compute_env != 'Other' and settings.CONTAINER_DRIVER == 'wholetale':
                dominant_corere_group = w.get_dominant_group_connector(user, submission).corere_group
                if dominant_corere_group:
                    if(dominant_corere_group.name.startswith("Author")):
                        if(has_transition_perm(submission.edit_noop, user) and 'launchSubmissionContainer' not in avail_buttons):
                            avail_buttons.append('launchSubmissionContainer')
                    else: 
                        if(has_transition_perm(submission.view_noop, user) and 'launchSubmissionContainer' not in avail_buttons):
                            avail_buttons.append('launchSubmissionContainer')

            return avail_buttons

        elif column[0] == 'version_id': 
            latest_submission_version = submission.manuscript.get_max_submission_version_id() #Probably inefficient here
            if(submission.version_id == latest_submission_version):
                return '#{0} (Current)'.format(submission.version_id)
            else:
                return '#{0}'.format(submission.version_id)
        else:
            return super(SubmissionJson, self).render_column(submission, column[0])

    def get_initial_queryset(self):
        manuscript_id = self.kwargs['manuscript_id']
        try:
            manuscript = m.Manuscript.objects.get(id=manuscript_id)
        except ObjectDoesNotExist:
            raise Http404()
        if(self.request.user.has_any_perm(c.PERM_MANU_VIEW_M, manuscript)):
            return(m.Submission.objects.filter(manuscript=manuscript_id).order_by('-version_id'))
        else:
            raise Http404()

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter (search) queryset
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(pub_name__icontains=search)|Q(pub_id__icontains=search))
        return qs

def helper_user_columns(user):
    columns = [['selected',''],['id','ID'],['username','username'],['roles','Roles'],['assigned_manuscripts','Assigned Manuscripts']]
    # if(user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists()):
    #     columns.append(['curators', "Curators"])
    # if(user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists() or user.groups.filter(name=c.GROUP_ROLE_VERIFIER).exists()):
    #     #columns.append(['created_at','Create Date']) #Right now we don't show it so why provide it?
    #     columns.append(['updated_at','Last Update Date'])
    return columns
    #return list(dict.fromkeys(columns)) #remove duplicates, keeps order in python 3.7 and up

# Customizing django-datatables-view defaults
# See https://pypi.org/project/django-datatables-view/ for info on functions
class UserJson(CorereBaseDatatableView):
    max_display_length = 500

    def get_columns(self):
        return helper_user_columns(self.request.user)

    # If you need the old render_column code, look at commit aa36e9b87b8d8504728ff2365219beb917210eae or earlier
    def render_column(self, user, column):
        #these string matches aren't the most exact, but fine for now
        if column[0] == 'roles':
            return ', '.join(map(str, user.groups.filter(name__contains='Role')))
        if column[0] == 'assigned_manuscripts':
            return user.groups.filter(name__contains='Manuscript').exclude(name__endswith=c.GROUP_COMPLETED_SUFFIX).count()
        return super(UserJson, self).render_column(user, column[0])

    def get_initial_queryset(self):
        return(m.User.objects.all())
        # manuscript_id = self.kwargs['manuscript_id']
        # try:
        #     manuscript = m.Manuscript.objects.get(id=manuscript_id)
        # except ObjectDoesNotExist:
        #     raise Http404()
        # if(self.request.user.has_any_perm(c.PERM_MANU_VIEW_M, manuscript)):
        #     return(m.Submission.objects.filter(manuscript=manuscript_id).order_by('-version_id'))
        # else:
        #     raise Http404()    # return get_objects_for_user(self.request.user, c.PERM_MANU_VIEW_M, klass=m.Manuscript).order_by('-id')

    #Note: this isn't tied to the search bar in the datatable, that happens solely browserside
    # def filter_queryset(self, qs):
    #     # use parameters passed in GET request to filter (search) queryset
    #     search = self.request.GET.get('search[value]', None)
    #     if search:
    #         qs = qs.filter(Q(title__icontains=search)|Q(pub_id__icontains=search)|Q(doi__icontains=search))
    #     return qs

############ File Tables (based off the files_datatable app) ############

class ManuscriptFileJson(fdtv.FileBaseDatatableView):
    def get_initial_queryset(self):
        manuscript_id = self.kwargs['id']
        try:
            manuscript = m.Manuscript.objects.get(id=manuscript_id)
        except ObjectDoesNotExist:
            raise Http404()
        if(self.request.user.has_any_perm(c.PERM_MANU_VIEW_M, manuscript)):
            #print(m.GitFile.objects.values('path','name').filter(parent_manuscript=manuscript))
            print("wow")
            return m.GitFile.objects.filter(parent_manuscript=manuscript) 
        else:
            raise Http404()
