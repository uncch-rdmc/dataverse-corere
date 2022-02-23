function create_file_table_config(table_path, readonly, is_submission, file_download_url) {
    top_buttons = [
        {
            text: '<span class="fas fa-file-download"></span> Download All',
            name: 'downloadall',
            action: function ( e, dt, node, config ) {
                slash_count = window.location.href.split("/").length - 1
                if(slash_count == 5)
                    window.open('downloadall/');
                else {
                    window.open('../downloadall/');
                }
                
            },
        },         
    ]
    if(!readonly && !is_submission) {
        top_buttons.push({
            text: '<span class="far fa-trash-alt"></span> Delete All',
            name: 'deleteall',
            action: function ( e, dt, node, config ) {
                if (confirm('This will delete all files for the submission. Is this ok?')) {
                    delete_all_and_refresh('..');
                }
            },
        },                    
        )
    }

    config = {
        ajax: table_path,
        lengthMenu: [[10, 25, 50, 100], [10, 25, 50, 100]],
        searching: true,
        processing: true,
        stateSave: true,
        paging: true,
        select: 'single',
        // dom: 'Bftlp',
        dom: 'Bfrtpl',
        // keys: true, //for keyboard
        columns:[
            {
                data: 'buttons',
                render: function(data,type,row,meta){
                    encoded = encodeURIComponent(row[0]+row[1])
                    button =  '<button class="btn btn-secondary btn-sm" type="button" onclick="window.open(\''+file_download_url+encoded+'\')"><span class="fas fa-file-download"></span></button>'
                    if(!readonly) {
                        button += '<button class="btn btn-secondary btn-sm" type="button" onclick="delete_and_refresh(\'../deletefile/?file_path='+encoded+'\''+')"><span class="far fa-trash-alt"></span></button>'
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
        buttons: top_buttons
    }
    return config
}