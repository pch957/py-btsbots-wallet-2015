Date.prototype.format = function(format) {
   var date = {
     "M+": this.getMonth() + 1,
     "d+": this.getDate(),
     "h+": this.getHours(),
     "m+": this.getMinutes(),
     "s+": this.getSeconds(),
     "q+": Math.floor((this.getMonth() + 3) / 3),
     "S+": this.getMilliseconds()
   };
   if (/(y+)/i.test(format)) {
     format = format.replace(RegExp.$1, (this.getFullYear() + '').substr(4 - RegExp.$1.length));
   }
   for (var k in date) {
     if (new RegExp("(" + k + ")").test(format)) {
       format = format.replace(RegExp.$1, RegExp.$1.length == 1
       ? date[k] : ("00" + date[k]).substr(("" + date[k]).length));
     }
   }
   return format;
}

time_format = function (text) {
   time = new Date(text+"Z")
   //time = new Date(time.getTime() - time.getTimezoneOffset()*60000)
   time_str = time.format('MM-dd hh:mm:ss')
   return time_str;
}

get_socket = function (text) {
    // the socket.io documentation recommends sending an explicit package upon connection
    // this is specially important when using the global namespace
    namespace = ''; // change to an empty string to use the global namespace
    var socket = io.connect(window.location.protocol + document.domain + ':' + location.port + namespace);
    socket.on('connect', function() {
        console.log("connect");
        socket.emit('my event', {data: 'I\'m connected!'});
    });
    return socket
}

//<script type="text/javascript" src="https://pusher.btsbots.com/autobahn.min.js"></script>
get_pusher = function (text) {
    var pusher = new autobahn.Connection({
        url: 'wss://pusher.btsbots.com/ws',
        realm: 'realm1'
    });
    return pusher
}
