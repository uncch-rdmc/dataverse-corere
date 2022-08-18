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
        autoWidth: false,
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
                    if(readonly) { return row[0]; }

                    //TODO: Stale, doing name first
                    return row[0] + '<span style="float:right;"><button class="btn btn-secondary btn-sm" type="button" onclick="edit_field(\''+row[0]+'\')" title="Edit file name" aria-label="Edit file name"><span class="fas fa-pencil-alt"></span></button></span>';

                }
            },
            {
                data: 'name',
                render: function(data,type,row,meta){
                    if(readonly) { return row[1]; }

                    return row[1] + '<span style="float:right;"><button class="btn btn-secondary btn-sm" type="button" onclick="show_edit_name_popup(\''+file_url_base+'\', \''+encodeURIComponent(row[0])+'\', \''+encodeURIComponent(row[1])+'\')" title="Edit file name" aria-label="Edit file name"><span class="fas fa-pencil-alt"></span></button></span>';
                }
            },
        ],
        columnDefs: [
            { "width": "3%", "targets": 0 },
            { "width": "20%", "targets": 1 },
            { "width": "40%", "targets": 2 },
            ],
        buttons: top_buttons
    }
    return config
}

function show_edit_name_popup(file_url_base, file_path, old_name){
    $('#file_name_old').val(decodeURIComponent(old_name));
    $('#file_path').val(file_path);
    $('#file_url_base').val(file_url_base);
    $('#exampleModalLong').modal('show');
}

function submit_edit_name_popup_and_reload(file_url_base){
    file_name_old = encodeURIComponent($('#file_name_old').val())
    file_name_new = $('#file_name_new').val()
    file_url_base = $('#file_url_base').val()
    file_path = $('#file_path').val()

    old_full_path = file_path + file_name_old
    new_full_path = file_path + file_name_new

    //TODO: Lets generate the url here
    rename_url = file_url_base+'renamefile/?old_path='+old_full_path+'&new_path='+new_full_path
    rename_and_refresh(rename_url)

    //TODO: Clear existing fields?

    console.log(file_path)
    console.log(file_name_old)
    console.log(file_name_new)
    $('#exampleModalLong').modal('hide');
}