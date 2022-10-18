function constructTable(columns) {
    var columns_config = [];
    var button_index;

    for (var c in columns) {
        var column_settings = {name: columns[c][0], title: columns[c][1]}
        if(columns[c][0] === 'buttons') {
            column_settings.visible = false;
            button_index = c;
        } else if(columns[c][0] === 'id' || columns[c][0] === 'created_at' || columns[c][0] === 'authors' || columns[c][0] === 'editors' || columns[c][0] === 'curators' || columns[c][0] === 'verifiers') { //Sometimes this doesn't work right, see issue #26 "Fix Datatable Visibility Bug"
            column_settings.visible = false;
        // } else if(columns[c][0] === 'submission_timestamp' || columns[c][0] === 'edition_timestamp' || columns[c][0] === 'curation_timestamp' || columns[c][0] === 'verification_timestamp') {
        //     column_settings.visible = false;
        } else if(columns[c][0] === 'selected') {
            column_settings.orderable = false;
            column_settings.className = 'select-checkbox';
        }
        columns_config[c] = column_settings
    }
    return [columns_config, button_index];
} 

function construct_buttons() {
    buttons = [];

    if(Sub_Table_Params.landingView) {
        if(Sub_Table_Params.has_group_author) {
            buttons.push({
                    text: '<i class="fas fa-plus"></i> &nbsp;Create Submission',
                    name: 'createSubmission',
                    action: function ( e, dt, node, config ) {
                        window.location.href = "/manuscript/"+ Sub_Table_Params.manuscript_id +"/update/";
                    },
                    attr: {
                        title: 'Create a new submission of data/code for this manuscript',
                        'aria-label': 'Create a new submission of data/code for this manuscript'
                    },
                    enabled: Sub_Table_Params.createSubButton
                })
        }

        buttons.push(
            {
                text: 'Edit Notes',
                name: 'editSubmission',
                action: function ( e, dt, node, config ) {
                    window.location.href = "/submission/"+submission_id+"/review/";
                    
                },
                attr: {
                    title: 'Edit notes for this submission round',
                    'aria-label': 'Edit notes for this submission round'
                },
                init: function ( dt, node, config ) {
                    node.css("display", "none");
                },
                enabled: false
            },
            {
                text: 'Review',
                name: 'reviewSubmission',
                action: function ( e, dt, node, config ) {
                    window.location.href = "/submission/"+submission_id+"/review/";
                    
                },
                attr: {
                    title: 'Review the data/code/metadata for this submission round',
                    'aria-label': 'Review the data/code/metadata for this submission round'
                },
                init: function ( dt, node, config ) {
                    node.css("display", "none");
                },
                enabled: false
            },
            {
                text: 'Edit Files',
                name: 'editSubmissionFiles',
                action: function ( e, dt, node, config ) {
                    window.location.href = "/submission/"+submission_id+"/editfiles/";
                },
                attr: {
                    title: 'Edit the data/code submitted for review',
                    'aria-label': 'Edit the data/code submitted for review'
                },
                init: function ( dt, node, config ) {
                    node.css("display", "none");
                },
                enabled: false
            },
            {
                text: 'View',
                name: 'viewSubmission',
                action: function ( e, dt, node, config ) {
                    window.location.href = "/submission/"+submission_id+"/view/";
                },
                attr: {
                    title: 'View information related to this submission round',
                    'aria-label': 'View information related to this submission round'
                },
                init: function ( dt, node, config ) {
                        node.css("display", "none");
                    },
                enabled: false
            },
            {
                text: 'View Files',
                name: 'viewSubmissionFiles',
                action: function ( e, dt, node, config ) {
                    window.location.href = "/submission/"+submission_id+"/viewfiles/";
                },
                attr: {
                    title: 'View the data/code submitted for review',
                    'aria-label': 'View the data/code submitted for review'
                },
                init: function ( dt, node, config ) {
                        node.css("display", "none");
                    },
                enabled: false
            },
            {
                text: 'Launch Container',
                name: 'launchSubmissionContainer',
                action: function ( e, dt, node, config ) {
                    window.location.href = "/submission/"+submission_id+"/notebook/";
                },
                attr: {
                    title: 'Launch a virtual environment containing the data/code submitted for review',
                    'aria-label': 'Launch a virtual environment containing the data/code submitted for review'
                },
                init: function ( dt, node, config ) {
                        node.css("display", "none");
                    },
                enabled: false
            },
            {
                text: 'Download Container Files',
                name: 'downloadContainerFiles',
                action: function ( e, dt, node, config ) {
                    window.location.href = "/submission/"+submission_id+"/wtdownloadall/";
                },
                attr: {
                    title: 'Download the files contained in the virtual environment created for this round of review. Note that this data/code may be different than what is held the CORE2 system, due to user interactions in the virtual environment.',
                    'aria-label': 'Download the files contained in the virtual environment created for this round of review. Note that this data/code may be different than what is held the CORE2 system, due to user interactions in the virtual environment.'
                },
                init: function ( dt, node, config ) {
                        node.css("display", "none");
                    },
                enabled: false
            },
            {
                text: 'Send Report',
                name: 'sendReportForSubmission',
                action: function ( e, dt, node, config ) {
                    var headers = new Headers();
                    headers.append('X-CSRFToken', '{{ csrf_token }}');
                    fetch('/submission/'+submission_id+'/sendreport/', {
                        method: 'POST',
                        headers: headers, 
                        credentials: 'include'
                    }).then(response => {
                        if (response.redirected) {
                            window.location.href = response.url;
                        }
                    })
                },
                attr: {
                    title: 'Send current verification report for the manuscript to the editors',
                    'aria-label': 'Send current verification report for the manuscript to the editors'
                },
                init: function ( dt, node, config ) {
                    node.css("display", "none");
                },
                enabled: false
            },
            {
                text: 'Return Submission to Authors',
                name: 'returnSubmission',
                action: function ( e, dt, node, config ) {
                    var headers = new Headers();
                    headers.append('X-CSRFToken', '{{ csrf_token }}');
                    fetch('/submission/'+submission_id+'/finish/', {
                        method: 'POST',
                        headers: headers, 
                        credentials: 'include'
                    }).then(response => {
                        if (response.redirected) {
                            window.location.href = response.url;
                        }
                    })
                },
                attr: {
                    title: 'Return this manuscript record to the authors to resubmit their data/code',
                    'aria-label': 'Return this manuscript record to the authors to resubmit their data/code'
                },
                init: function ( dt, node, config ) {
                    node.css("display", "none");
                },
                enabled: false
            }
        );
    }
    
    return buttons;
}

function fixButtonGroupCurve() {
    //{% comment %} needs as we make buttons invisible, otherwise groups end up with non-rounded edges {% endcomment %}
    $('.my-1.btn-group').has('.btn:hidden').find('.btn').css('border-radius', 0);
    $('.my-1.btn-group').has('.btn:hidden').find('.btn:visible:first').css({
        'border-top-left-radius': '3px',
        'border-bottom-left-radius': '3px',
    });
    $('.my-1.btn-group').has('.btn:hidden').find('.btn:visible:last').css({
        'border-top-right-radius': '3px',
        'border-bottom-right-radius': '3px',
    });
}

function sub_table_callback(table) {
    dt_submission = table;
}

$(document).ready(function() {
    $.ajax({
        url: "/manuscript/"+ Sub_Table_Params.manuscript_id +"/submission_table/",
        cache: false,
        success: function (response) {
            var [columns_config, button_index] = constructTable(response.data[0]);
            var table = $('#submission_table').DataTable({
                searching: false,
                processing: true,
                stateSave: true,
                select: Sub_Table_Params.landingView ? 'single': false,
                columns: columns_config,
                ordering: false,
                dom: Sub_Table_Params.landingView ? 'Bfrt' : 'rt' ,
                data: response.data.slice(1),
                buttons: construct_buttons()
            })
            .on( 'select', function ( e, dt, type, indexes ) {
                submission_id = dt.rows( { selected: true } ).data()[0][1] //Implicit globals are not best practice
                submission_status = dt.rows( { selected: true } ).data()[0][3] //Implicit globals are not best practice
                avail_buttons = dt.rows( { selected: true } ).data()[0][button_index];
                for(var i in avail_buttons) {
                    dt.button(avail_buttons[i]+':name').enable(true);
                    dt.button(avail_buttons[i]+':name').nodes().css("display", "block");
                }
                if(submission_status == "New") {
                    dt.button('viewSubmissionFiles:name').enable(false);
                    dt.button('viewSubmissionFiles:name').nodes().css("display", "none");
                }
                fixButtonGroupCurve();

            } )
            .on( 'deselect', function ( e, dt, type, indexes ) {
                var count = dt.rows( { selected: true } ).count();
                if(count == 0) { //This is not dynamic because we can't ensure we know all the possible buttons by looking at a certain row
                    dt.button('editSubmission:name').enable(false);
                    dt.button('editSubmission:name').nodes().css("display", "none");
                    dt.button('editSubmissionFiles:name').enable(false);
                    dt.button('editSubmissionFiles:name').nodes().css("display", "none");
                    dt.button('viewSubmission:name').enable(false);
                    dt.button('viewSubmission:name').nodes().css("display", "none");
                    dt.button('viewSubmissionFiles:name').enable(false);
                    dt.button('viewSubmissionFiles:name').nodes().css("display", "none");
                    dt.button('progressSubmission:name').enable(false);
                            
                }
                fixButtonGroupCurve();
            } ) 
            .order.neutral().draw()
            .row(':eq(0)', { page: 'current' }).select();
            
            sub_table_callback(table)

            if(!Sub_Table_Params.landingView) {
                $('#submission_table tbody').on('dblclick', 'tr', function(e, dt, type, indexes) {
                    window.open("/submission/"+table.row( this ).data()[1]+"/review/", '_blank');
                }); 

                table.column(0).visible(false);
                table.row(0).remove().draw(false);
            }    

            if(Sub_Table_Params.has_group_editor || Sub_Table_Params.has_group_curator || Sub_Table_Params.has_group_verifier ) {
                if(Sub_Table_Params.landingView) {
                    document.getElementById("submission_table_wrapper").querySelector("div.dt-buttons").insertAdjacentHTML('beforeend',
                        `<input id="mine_toggle" type="checkbox" data-toggle="toggle" data-on="<i class='far fa-eye'></i> Timestamps Hidden" data-onstyle="secondary" 
                            data-off="<i class='far fa-eye'></i> Timestamps Shown" data-offstyle="secondary" data-height="38px" data-width="210px">`);
                    mine_toggle = $("#mine_toggle");
                    mine_toggle.change(function(event){
                        var column = table.column(4);
                        column.visible( ! column.visible() );
                        var column = table.column(7);
                        column.visible( ! column.visible() );
                        var column = table.column(9);
                        column.visible( ! column.visible() );
                        var column = table.column(11);
                        column.visible( ! column.visible() );
                    });
                    mine_toggle.bootstrapToggle() 
                } else {
                    var column = table.column(4);
                    column.visible( false );
                    var column = table.column(7);
                    column.visible( false );
                    var column = table.column(9);
                    column.visible( false );
                    var column = table.column(11);
                    column.visible( false );
                }

            }

            fixButtonGroupCurve();
        }
    })


});