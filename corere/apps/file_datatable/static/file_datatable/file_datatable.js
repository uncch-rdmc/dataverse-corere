function create_file_table_config(table_path, readonly) {
    config = {
            ajax: table_path,
            lengthMenu: [[10, 25, 50, 100], [10, 25, 50, 100]],
            searching: true,
            processing: true,
            stateSave: true,
            paging: true,
            select: 'single',
            dom: 'Bftlp',
            // keys: true, //for keyboard
            columns:[
                {
                    data: 'buttons',
                    render: function(data,type,row,meta){
                        //TODO: Delete button needs to be a post with a csrf, see delete_and_remove or delete_and_refresh
                        //TODO: Unify how we are doing these two calls (after understanding generalizing better). One is relative, one isn't
                        encoded = encodeURIComponent(row[0]+row[1])
                        button =  '<button class="btn btn-secondary btn-sm" type="button" onclick="window.open(\'{{ file_download_url }}'+encoded+'\')"><span class="fas fa-file-download"></span></button>'
                        if(!readonly) {
                            button += '<button class="btn btn-secondary btn-sm" type="button" onclick="window.open(\'../deletefile/?file_path='+encoded+'\')"><span class="far fa-trash-alt"></span></button>'
                        }
                        return button;
                    }
                },
                {
                    data: 'path',
                    render: function(data,type,row,meta){
                        return row[0];
                    }
                },
                {
                    data: 'name',
                    render: function(data,type,row,meta){
                        return row[1];
                    }
                },
            ],
            columnDefs: [
                { "width": "33px", "targets": 0 }
              ],
            buttons: [
                        {
                            text: 'Refresh',
                            name: 'refresh',
                            action: function ( e, dt, node, config ) {
                                var table = $('#file_table').DataTable();
                                table.ajax.reload();
                            },
                        },
                        {
                            text: '<span class="fas fa-file-download"></span> Download All',
                            name: 'downloadall',
                            action: function ( e, dt, node, config ) {
                                window.open('../downloadall/');
                            },
                        },
                    ]
        }
    return config
}