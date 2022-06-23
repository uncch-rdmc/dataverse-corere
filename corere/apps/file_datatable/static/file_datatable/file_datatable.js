function create_file_table_config(table_path, readonly, is_submission, file_url_base) {
    //buttons are hidden by default, to be managed by your page
    
    //TODO: This download all url logic doesn't work right for my case when I'm presenting the manuscript url in the submission. Maybe I should pass the urL?
    top_buttons = [
        {
            text: '<span class="fas fa-file-download"></span> Download All',
            name: 'downloadall',
            action: function ( e, dt, node, config ) {
                window.open(file_url_base+'downloadall/')
            },
            attr: {
                title: 'Download all manuscript and appendix files',
                'aria-label': 'Download all manuscript and appendix files'
            }
        },         
    ]
    if(!readonly && is_submission) {
        top_buttons.push({
            text: '<span class="far fa-trash-alt"></span> Delete All',
            name: 'deleteall',
            action: function ( e, dt, node, config ) {
                if (confirm('This will delete all files for the submission. Is this ok?')) {
                    delete_all_and_refresh(file_url_base);
                }
            },
            attr: {
                title: 'Delete all manuscript and appendix files',
                'aria-label': 'Delete all manuscript and appendix files'
            }
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
                    button =  '<button class="btn btn-secondary btn-sm" type="button" onclick="window.open(\''+file_url_base+'downloadfile/?file_path='+encoded+'\')" title="Download file" aria-label="Download file"><span class="fas fa-file-download"></span></button>'
                    if(!readonly) {
                        button += '<button class="btn btn-secondary btn-sm" type="button" onclick="delete_and_refresh(\''+file_url_base+'deletefile/?file_path='+encoded+'\''+')" title="Delete file" aria-label="Delete file"><span class="far fa-trash-alt"></span></button>'
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