#from django.shortcuts import render
from django_datatables_view.base_datatable_view import BaseDatatableView

# You need to override this and set your own "get_initial_queryset"
class FileBaseDatatableView(BaseDatatableView):
    max_display_length = 10000

    def get_columns(self):
        columns = [['download_button',''],['delete_button',''],['path','File Path'],['name','File Name'],['change_detection']]
        return columns

    def prepare_results(self, qs):
        data = []

        data.append(self.get_columns()) #adds headers to grab in js for dynamic support

        print(self._columns)
        print(qs)
        for item in qs:
            print(item)
            if self.is_data_list:
                data.append([self.render_column(item, column) for column in self._columns])
            else:
                row = {col_data['data']: self.render_column(item, col_data['data']) for col_data in self.columns_data}
                data.append(row)
        
        print("HEY")
        return data

    def render_column(self, file, column):
        #these string matches aren't the most exact, but fine for now
        # if column[0] == 'roles':
        #     return ', '.join(map(str, user.groups.filter(name__contains='Role')))
        # if column[0] == 'assigned_manuscripts':
        #     return user.groups.filter(name__contains='Manuscript').exclude(name__endswith=c.GROUP_COMPLETED_SUFFIX).count()
        return super(FileBaseDatatableView, self).render_column(file, column[0])