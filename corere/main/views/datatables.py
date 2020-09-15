import logging
from django_datatables_view.base_datatable_view import BaseDatatableView
from corere.main import constants as c
from corere.main import models as m
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
logger = logging.getLogger(__name__)

#Shared across our various datatables
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
#MADTEST: subset of results here! (MISSING)
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
    # This defines the columns a user can view for a table.
    # TODO: Controll in a more centralized manner for security
    # NOTE: If any of the columns defined here are just numbers, it opens a security issue with restricting datatable info. See the comment in extract_datatables_column_data
    # MAD: This should be using guardian???
    columns = []
    # if(user.groups.filter(name=c.GROUP_ROLE_CURATOR).exists()):
    columns += ['id','pub_id','title','doi','open_data','_status','created_at','updated_at','authors','curators','verifiers','buttons']
    # if(user.groups.filter(name=c.GROUP_ROLE_VERIFIER).exists()):
    #     columns += ['id','pub_id','title','doi','open_data','authors']
    # if(user.groups.filter(name=c.GROUP_ROLE_AUTHOR).exists()):
    #     columns += ['id','pub_id','title','doi','open_data','authors']
    # if(user.groups.filter(name=c.GROUP_ROLE_EDITOR).exists()):
    #     columns += ['id','pub_id','title','doi','open_data','authors']
    return list(dict.fromkeys(columns)) #remove duplicates, keeps order in python 3.7 and up

# Customizing django-datatables-view defaults
# See https://pypi.org/project/django-datatables-view/ for info on functions
class ManuscriptJson(CorereBaseDatatableView):
    model = m.Manuscript
    max_display_length = 500

    def get_columns(self):
        return helper_manuscript_columns(self.request.user)

    def render_column(self, manuscript, column):
        if column == 'authors':
            return '{0}'.format([escape(user.username) for user in m.User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(manuscript.id))])
        elif column == 'curators':
            return '{0}'.format([escape(user.username) for user in m.User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id))])
        elif column == 'verifiers':
            return '{0}'.format([escape(user.username) for user in m.User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id))])
        elif column == 'buttons':
            user = self.request.user
            avail_buttons = []
            if(has_transition_perm(manuscript.edit_noop, user)):
                avail_buttons.append('editManuscript')
                avail_buttons.append('editManuscriptFiles')
            elif(has_transition_perm(manuscript.view_noop, user)):
                avail_buttons.append('viewManuscript')
                avail_buttons.append('viewManuscriptFiles')
            if(has_transition_perm(manuscript.begin, user)):
                avail_buttons.append('progressManuscript')
            #TODO: add launchNotebook once integration is better
            # MAD: Should we change these to be transitions?
            if(user.has_any_perm('add_authors_on_manuscript', manuscript)):
                avail_buttons.append('inviteassignauthor')
            if(user.has_any_perm('manage_editors_on_manuscript', manuscript)):
                avail_buttons.append('assigneditor')
            if(user.has_any_perm('manage_curators_on_manuscript', manuscript)):
                avail_buttons.append('assigncurator')
            if(user.has_any_perm('manage_verifiers_on_manuscript', manuscript)):
                avail_buttons.append('assignverifier')

            if(has_transition_perm(manuscript.add_submission_noop, user)):
                avail_buttons.append('createSubmission')
            return avail_buttons
        else:
            return super(ManuscriptJson, self).render_column(manuscript, column)

    def get_initial_queryset(self):
        return get_objects_for_user(self.request.user, "view_manuscript", klass=self.model)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter (search) queryset
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(title__icontains=search)|Q(pub_id__icontains=search)|Q(doi__icontains=search))
        return qs

def helper_submission_columns(user):
    # This defines the columns a user can view for a table.
    # NOTE: If any of the columns defined here are just numbers, it opens a security issue with restricting datatable info. See the comment in extract_datatables_column_data
    # MAD: This should be using guardian???
    columns = ['id','submission_status','curation_id','curation_status','verification_id','verification_status', 'buttons']
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
    model = m.Submission
    max_display_length = 500

    def get_columns(self):
        return helper_submission_columns(self.request.user)

    def render_column(self, submission, column):
        user = self.request.user
        if column == 'submission_status':
            if(has_transition_perm(submission.view_noop, user)):
                return submission._status
            else:
                return ''
        elif column == 'curation_id':
            try:
                return '{0}'.format(submission.submission_curation.id)
            except m.Submission.submission_curation.RelatedObjectDoesNotExist:
                return ''
        elif column == 'curation_status':
            try:
                if(has_transition_perm(submission.submission_curation.view_noop, user)):
                    return '{0}'.format(submission.submission_curation._status)
            except m.Submission.submission_curation.RelatedObjectDoesNotExist:
                pass
            return ''
        elif column == 'verification_id':
            try:
                return '{0}'.format(submission.submission_verification.id)
            except m.Submission.submission_verification.RelatedObjectDoesNotExist:
                return ''
        elif column == 'verification_status':
            try:
                if(has_transition_perm(submission.submission_verification.view_noop, user)):
                    return '{0}'.format(submission.submission_verification._status)
            except m.Submission.submission_verification.RelatedObjectDoesNotExist:
                pass
            return ''
        elif column == 'buttons': 
#Add edition buttons
            avail_buttons = []
            if(has_transition_perm(submission.edit_noop, user)):
                avail_buttons.append('editSubmission')
                avail_buttons.append('editSubmissionFiles')
            elif(has_transition_perm(submission.view_noop, user)):
                avail_buttons.append('viewSubmission')
                avail_buttons.append('viewSubmissionFiles')
            if(has_transition_perm(submission.submit, user)):
                avail_buttons.append('progressSubmission')

            if(has_transition_perm(submission.add_edition_noop, user)):
                avail_buttons.append('createEdition')
            try:
                if(has_transition_perm(submission.submission_edition.edit_noop, user)):
                    avail_buttons.append('editEdition')
                elif(has_transition_perm(submission.submission_edition.view_noop, user)):
                    avail_buttons.append('viewEdition')
                if(has_transition_perm(submission.review, user)): #TODO: same review check for edition and verification. Either make smarter or refactor the model
                    avail_buttons.append('progressEdition')
            except m.Submission.submission_edition.RelatedObjectDoesNotExist:
                pass

            if(has_transition_perm(submission.add_curation_noop, user)):
                avail_buttons.append('createCuration')
            try:
                if(has_transition_perm(submission.submission_curation.edit_noop, user)):
                    avail_buttons.append('editCuration')
                elif(has_transition_perm(submission.submission_curation.view_noop, user)):
                    avail_buttons.append('viewCuration')
                if(has_transition_perm(submission.review, user)): #TODO: same review check for curation and verification. Either make smarter or refactor the model
                    avail_buttons.append('progressCuration')
            except m.Submission.submission_curation.RelatedObjectDoesNotExist:
                pass

            if(has_transition_perm(submission.add_verification_noop, user)):
                avail_buttons.append('createVerification')
            try:
                if(has_transition_perm(submission.submission_verification.edit_noop, user)):
                    avail_buttons.append('editVerification')
                elif(has_transition_perm(submission.submission_verification.view_noop, user)):
                    avail_buttons.append('viewVerification')  
                if(has_transition_perm(submission.review, user)): #TODO: same review check for curation and verification. Either make smarter or refactor the model
                    avail_buttons.append('progressVerification')
            except m.Submission.submission_verification.RelatedObjectDoesNotExist:
                pass

            return avail_buttons
        else:
            return super(SubmissionJson, self).render_column(submission, column)

    def get_initial_queryset(self):
        manuscript_id = self.kwargs['manuscript_id']
        try:
            manuscript = m.Manuscript.objects.get(id=manuscript_id)
        except ObjectDoesNotExist:
            raise Http404()
        if(self.request.user.has_any_perm('view_manuscript', manuscript)):
            return(m.Submission.objects.filter(manuscript=manuscript_id))
        else:
            raise Http404()

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter (search) queryset
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(title__icontains=search)|Q(pub_id__icontains=search)|Q(doi__icontains=search))
        return qs

