var title_text = document.querySelector("#homepage_title").innerHTML;
var msg_count = 1;
document.addEventListener('DOMContentLoaded', () => {    
    const channel_div_template = Handlebars.compile(document.querySelector('#channel_div').innerHTML);
    const list_template = Handlebars.compile(document.querySelector('#message_li').innerHTML);    
    var channelname;
    var username;
    const request = new XMLHttpRequest();
    request.open('GET', '/if_channel');
    request.send();        
    request.onload = () => {
        var resp = JSON.parse(request.responseText);
        channelname = resp.channel;
        username = resp.username;
        if (!channelname || !username) {
            document.querySelector("#chat_button").disabled = true;
            document.querySelector("#channel_error").innerHTML = "Select A Channel First";            
        }
        else {
            document.querySelector("#chat_button").disabled = false;
            document.querySelector("#channel_error").innerHTML = "";
        }            
    }
    
    // Connect to websocket
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    // When connected, configure buttons
    socket.on('connect', () => {

        document.querySelector("#chat_button").onclick = () => {
            let message = document.querySelector("#chat_message").value;
            if (message.length <= 0) {
                alert("Type a Message");
                return false;
            } else {
                socket.emit('submit chat', {'message': message, "channel": channelname, "username": username});
                document.querySelector("#chat_message").autofocus = true;
                document.querySelector("#chat_message").value = '';                
            }
        };        
    });
    
    socket.on('receive chat', data => {
        if (channelname === data.channel)
        {
            var chat_id = data.chat_id;
            var chatID = chat_id.toString();
            var currentuser;

            if (data.username === username) {
                currentuser = true;
            } else {
                currentuser = false;
                document.querySelector("#homepage_title").innerHTML = `${title_text} (${msg_count})`;
                msg_count = msg_count + 1;
            }

            let li = list_template({'username': data.username, 'time': data.time, 'chat_id': chatID, 'currentuser': currentuser, 'message': data.message});
            let mylist = document.querySelector("#chat_list").innerHTML;
            li += mylist;
            document.querySelector("#chat_list").innerHTML = li;        
        }
    });
    
    socket.on('connect', () => {
        document.querySelectorAll(".deletechat").forEach(link => {
            link.onclick = ()=> {
                let chatid = link.dataset.chat_id;
                socket.emit('delete chat', {'chat_id': chatid});
                return false;
            };
        });        
    });

    socket.on('connect', () => {
        document.querySelectorAll(".deletechannel").forEach(link => {
            link.onclick = ()=> {
                let chname = link.dataset.channelname;
                socket.emit('process channel deletion', {'channelname': chname});
            };
        });        
    });

    socket.on('block chat', data => {
        if (data.channelname === channelname) {
            document.querySelector("#chat_button").disabled = true;
            document.querySelector("#channel_error").innerHTML = "THIS CHANNEL IS BEING DELETED";
        }
    });

    socket.on('deleted chat', data => {
        if (data.channelname === channelname) {
            if (data.success) {
                const element = document.getElementById(data.chat_id);
                element.style.animationPlayState = 'running';
                element.addEventListener('animationend', () =>  {
                    element.remove();
                });
            } else {
                document.querySelector("#channel_error").innerHTML = "There was an error. Refresh the page."
            }
        }
    });

    socket.on('deleted channel', data => {
        if (data.channelname === channelname) {            
            document.getElementById(data.channelid).remove();
            location.reload();            
        } else {
            document.getElementById(data.channelid).remove();
        }
    });
    
    socket.on('channel created', data => {
        let current_channel = false;
        let current_user = false;
        if (data.channel === channelname) {
            current_channel = true;
        } 
        if (data.username === username) {
            current_user = true;
        }
        let div = channel_div_template({'channelname': data.channel, 'current_channel': current_channel, 'current_user': current_user, 'channelid': data.id});
        document.querySelector("#channel_list").innerHTML += div;
        if (document.querySelector("#nochannels_in_list").innerHTML) {
            document.querySelector("#nochannels_in_list").innerHTML = "";
        }
        
    });

});

window.onclick = ()=>{
    document.querySelector("#homepage_title").innerHTML = title_text;
    msg_count = 1;
};