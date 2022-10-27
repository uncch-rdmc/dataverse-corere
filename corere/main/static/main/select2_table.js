function generateResultTable(data) {
    if(data.text == "Searching…") {
      return ""
    }
    console.log(user_table_map.get(data.text));
    console.log(user_table_map.get(data.text).split("|",3))
    info = user_table_map.get(data.text).split("|",3);
  
    var result = $(
      '<div class="row">' +
      '<div class="col-md-6 col-xs-6">' + info[1] +' (' + info[0] + ')</div>' +
      '<div class="col-md-6 col-xs-6">' + info[2] + ' Assignments</div>' +
      '</div>'
    );

    return result;
}

$(function() {
    $('#id_users_to_add').select2({
      width: '100%',
      templateResult: generateResultTable
    });

  })