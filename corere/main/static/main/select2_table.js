function generateResultTable(data) {
    var count = user_table_map.get(data.text)
  
    var result = $(
      '<div class="row">' +
      '<div class="col-md-6 col-xs-6">' + data.text + '</div>' +
      '<div class="col-md-6 col-xs-6">' + count + ' Assignments</div>' +
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