from django.shortcuts import render, redirect
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.utils.html import escape
from django.db.models import Q
from django.contrib.auth import logout
from django.contrib import messages
from .models import Manuscript, User

def index(request):
    if request.user.is_authenticated:
        return render(request, "main/index.html")
    else:
        return render(request, "main/login.html")

def logout_view(request):
    logout(request)
    messages.add_message(request, messages.INFO, 'You have succesfully logged out!')
    return redirect('/')

class ManuscriptJson(BaseDatatableView):
    # The model we're going to show
    model = Manuscript

    # define the columns that will be returned
    columns = ['pub_id','title','doi','open_data','note_text','status','created_at','updated_at','submissions','verifications','curations']

    # define column names that will be used in sorting
    # order is important and should be same as order of columns
    # displayed by datatables. For non sortable columns use empty
    # value like ''
    #order_columns = ['updated_at', 'user', 'state', '', '']

    # set max limit of records returned, this is used to protect our site if someone tries to attack our site
    # and make it return huge amount of data
    max_display_length = 500

    def render_column(self, row, column):
        # We want to render user as a custom column
        if column == 'user':
            # escape HTML for security reasons
            return escape('{0} {1}'.format(row.customer_firstname, row.customer_lastname))
        else:
            return super(ManuscriptJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(title__icontains=search)|Q(pub_id__icontains=search)|Q(note_text__icontains=search)|Q(doi__icontains=search))

        # # more advanced example using extra parameters
        # filter_customer = self.request.GET.get('customer', None)

        # if filter_customer:
        #     customer_parts = filter_customer.split(' ')
        #     qs_params = None
        #     for part in customer_parts:
        #         q = Q(customer_firstname__istartswith=part)|Q(customer_lastname__istartswith=part)
        #         qs_params = qs_params | q if qs_params else q
        #     qs = qs.filter(qs_params)
        return qs