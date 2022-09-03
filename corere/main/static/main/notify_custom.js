//pulled from 1.7.0 
//modified to update badge and to return a better formatted list of notifications
//also modified to delete a notification on alert click and refetch

var notify_badge_class;
var notify_menu_class;
var notify_api_url;
var notify_fetch_count;
var notify_unread_url;
var notify_mark_all_unread_url;
var notify_refresh_period = 15000;
var consecutive_misfires = 0;
var registered_functions = [];

function fill_notification_badge(data) {
    var badges = document.getElementsByClassName(notify_badge_class);
    if (badges) {
        for(var i = 0; i < badges.length; i++){
            badges[i].innerHTML = data.unread_count;
        }
    }
    //Custom query to update CORE2 badges
    //this code also exists in the header to update when the page loads
    //TODO: Use notify_badge_class?
    $( "span.notification_count").filter(function() {
        return parseInt($(this).text()) > 0;
    }).show();
    $( "span.notification_count").filter(function() {
        return parseInt($(this).text()) == 0;
    }).hide();

    var pageTitle = $("title").text().split(/\(\d+\) /).pop() //We extract the existing unread count if there is one
    if(data.unread_count > 0){
        $("title").text("(" + data.unread_count + ") " + pageTitle);
    } else {
        $("title").text(pageTitle);
    }
}

function fill_notification_list(data) {
    var menus = document.getElementsByClassName(notify_menu_class);
    if (menus) {
        var messages = data.unread_list.map(function (item) {
            
            linkReplacePattern = /(\b(https?|ftp):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gim;
            var message = item.description.replace(linkReplacePattern, '<a href="$1">$1</a>');

            date = new Date(item.timestamp).toLocaleString('default', { hourCycle: 'h23', month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: 'numeric' })

            return '<div class="alert alert-info alert-dismissible fade show " role="alert">'
            +    '<span style="font-weight: 600;">' + date + "</span><br> " + message
            +    '<button type="button" class="btn-close" data-dismiss="alert" aria-label="Clear notification" onclick="'
            + `
              $.ajax({
                  url:'/inbox/notifications/mark-as-read/`+item.slug+`/',
                  type:'get' 
              }); 
              fetch_api_data();
              `
            +'">'
            +    '</button>'
            + '</div>'
        }).join('')

        for (var i = 0; i < menus.length; i++){
            menus[i].innerHTML = messages;
        }
    }
}

function register_notifier(func) {
    registered_functions.push(func);
}

function fetch_api_data() {
    if (registered_functions.length > 0) {
        //only fetch data if a function is setup
        var r = new XMLHttpRequest();
        r.addEventListener('readystatechange', function(event){
            if (this.readyState === 4){
                if (this.status === 200){
                    consecutive_misfires = 0;
                    var data = JSON.parse(r.responseText);
                    for(var i = 0; i < registered_functions.length; i++) {
                       registered_functions[i](data);
                    }
                }else{
                    consecutive_misfires++;
                }
            }
        })
        r.open("GET", notify_api_url+'?max='+notify_fetch_count, true);
        r.send();
    }
    if (consecutive_misfires < 10) {
        setTimeout(fetch_api_data,notify_refresh_period);
    } else {

    }
}

setTimeout(fetch_api_data, 1000);
