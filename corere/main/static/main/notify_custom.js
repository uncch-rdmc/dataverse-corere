//pulled from 1.6.0 
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
    //Custom query to update CoReRe badges
    //this code also exists in the header to update when the page loads
    //TODO: Use notify_badge_class?
    $( "span.notification_count").filter(function() {
        return parseInt($(this).text()) > 0;
    }).show();
    $( "span.notification_count").filter(function() {
        return parseInt($(this).text()) == 0;
    }).hide();

    //Custom update page title
    //if(data.unread_count > 0)
    //var pageTitle = $("title").text();
    if(data.unread_count > 0){
        $("title").text("(" + data.unread_count + ") Dataverse CORE2");
    } else {
        $("title").text("Dataverse CORE2");
    }
}

function fill_notification_list(data) {
    var menus = document.getElementsByClassName(notify_menu_class);
    if (menus) {
        var messages = data.unread_list.map(function (item) {
            
            var message = item.description;
            // var message = "";
            // if(typeof item.actor !== 'undefined'){
            //     message = item.actor;
            // }
            // if(typeof item.verb !== 'undefined'){
            //     message = message + " " + item.verb;
            // }
            // if(typeof item.target !== 'undefined'){
            //     message = message + " " + item.target;
            // }
            // if(typeof item.timestamp !== 'undefined'){
            //     message = message + " " + item.timestamp;
            // }
            return '<div class="alert alert-info alert-dismissible fade show " role="alert">'
            +    '<button type="button" class="fas fa-fw mr-3 align-self-center close" data-dismiss="alert" aria-label="Close" onclick="'
            + `
              $.ajax({
                  url:'/inbox/notifications/mark-as-read/`+item.slug+`/',
                  type:'get' 
              });
              fetch_api_data();
              `
            +'">'
            +        '<span aria-hidden="true">&times;</span>'
            +    '</button>'
            +    '<div>'+ message + '</div>'
            + '</div>'

            //finish '<li>' + message + '</li>';
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
                    registered_functions.forEach(function (func) { func(data); });
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
        // var badges = document.getElementsByClassName(notify_badge_class);
        // if (badges) {
        //     for (var i = 0; i < badges.length; i++){
        //         badges[i].innerHTML = "!";
        //         badges[i].title = "Connection lost!"
        //     }
        // }
    }
}

// //Custom corere
// function delete_and_fetch(slug) {
//     const userAction = async () => {
//         const response = await fetch('inbox/notifications/delete/'+slug+'/');
//         const myJson = await response.json(); //extract JSON from the http response
//         // do something with myJson
//       }
// }

setTimeout(fetch_api_data, 1000);
